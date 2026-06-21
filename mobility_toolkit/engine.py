import os
import shlex
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Macaulay2 backend resolution
# ---------------------------------------------------------------------------
# The engine shells out to a Macaulay2 binary. How that binary is reached
# differs per platform, so the invocation is resolved at call time from the
# environment and the host OS. Resolution order:
#
#   1. MOBILITY_M2_CMD       -- explicit full command (script still on stdin),
#                               e.g. "wsl -d Debian M2 --no-readline -q".
#   2. MOBILITY_M2_DOCKER_IMAGE -- run M2 inside `docker run --rm -i <image>`.
#   3. native `M2` on PATH   -- Linux/macOS, or Windows with a native install.
#   4. WSL on Windows        -- `wsl [-d <distro>] ... M2`, distro from
#                               MOBILITY_M2_WSL_DISTRO (default "Ubuntu").
#
# In every case a Python-side subprocess timeout is the hard safety net; the
# GNU coreutils `timeout` wrapper is added on top only where it is available
# (it kills M2 itself, not just the launcher process).

_IS_WINDOWS = os.name == "nt"

_M2_FLAGS = ["M2", "--no-readline", "-q"]


def _fmt_timeout(timeout_seconds: float) -> str:
    return str(int(timeout_seconds)) if float(timeout_seconds).is_integer() else str(timeout_seconds)


def _coreutils_timeout_prefix(timeout_seconds: float, available: bool) -> List[str]:
    if not available:
        return []
    return ["timeout", "--kill-after=5", _fmt_timeout(timeout_seconds)]


def resolve_m2_command(timeout_seconds: float = 30.0) -> Optional[List[str]]:
    """Resolve the argv used to launch Macaulay2 reading a script from stdin.

    Returns ``None`` when no Macaulay2 backend can be located, so callers can
    emit an actionable error instead of an opaque FileNotFoundError.
    """
    # 1. Explicit override -- the user owns the full command.
    override = os.environ.get("MOBILITY_M2_CMD")
    if override:
        # posix=False on Windows so backslash paths survive splitting.
        return shlex.split(override, posix=not _IS_WINDOWS)

    # 2. Docker (opt-in; there is no official M2 image, so it must be named).
    image = os.environ.get("MOBILITY_M2_DOCKER_IMAGE")
    if image:
        prefix = _coreutils_timeout_prefix(timeout_seconds, available=True)
        return ["docker", "run", "--rm", "-i", image] + prefix + _M2_FLAGS

    # 3. Native M2 on PATH (Linux/macOS, or a native Windows install).
    if shutil.which("M2"):
        prefix = _coreutils_timeout_prefix(timeout_seconds, available=bool(shutil.which("timeout")))
        return prefix + _M2_FLAGS

    # 4. WSL on Windows.
    if _IS_WINDOWS and shutil.which("wsl"):
        distro = os.environ.get("MOBILITY_M2_WSL_DISTRO", "Ubuntu")
        wsl_base = ["wsl"]
        if distro:
            wsl_base += ["-d", distro]
        prefix = _coreutils_timeout_prefix(timeout_seconds, available=True)
        return wsl_base + prefix + _M2_FLAGS

    return None


def describe_m2_backend() -> Dict[str, object]:
    """Diagnostic summary of how Macaulay2 will be invoked (for `doctor`/UX)."""
    override = os.environ.get("MOBILITY_M2_CMD")
    image = os.environ.get("MOBILITY_M2_DOCKER_IMAGE")
    cmd = resolve_m2_command()
    if override:
        strategy = "env override (MOBILITY_M2_CMD)"
    elif image:
        strategy = f"docker image '{image}'"
    elif shutil.which("M2"):
        strategy = "native M2 on PATH"
    elif _IS_WINDOWS and shutil.which("wsl"):
        strategy = f"WSL distro '{os.environ.get('MOBILITY_M2_WSL_DISTRO', 'Ubuntu')}'"
    else:
        strategy = "none (Macaulay2 not found)"
    return {
        "platform": sys.platform,
        "strategy": strategy,
        "command": cmd,
        "available": cmd is not None,
    }


def _no_backend_message() -> str:
    return (
        "Macaulay2 backend not found. Install Macaulay2 and ensure `M2` is on PATH, "
        "or set MOBILITY_M2_CMD (e.g. 'wsl -d Ubuntu M2 --no-readline -q'), "
        "or MOBILITY_M2_DOCKER_IMAGE for a Docker-based backend. "
        "See https://macaulay2.com for installation."
    )


def run_macaulay2(script_content: str, timeout_seconds: float = 30.0) -> Dict[str, any]:
    """Executes a Macaulay2 script via the resolved backend (native/WSL/docker).

    Args:
        script_content (str): The Macaulay2 script to execute.
        timeout_seconds (float): Timeout in seconds for the execution.

    Returns:
        Dict[str, any]: {
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "timeout": bool
        }
    """
    # 1. Input sanitization: removes null bytes, normalizes line endings to \n
    if script_content is None:
        script_content = ""
    sanitized_input = script_content.replace('\x00', '')
    sanitized_input = sanitized_input.replace('\r\n', '\n').replace('\r', '\n')

    # Prepare default outputs
    exit_code = 0
    stdout_raw = b""
    stderr_raw = b""
    timeout_triggered = False

    # 2. Resolve the backend command for this platform/environment.
    cmd = resolve_m2_command(timeout_seconds)
    if cmd is None:
        return {
            "exit_code": 127,
            "stdout": "",
            "stderr": _no_backend_message(),
            "timeout": False,
        }

    try:
        # Dual-layer timeout: Python-side timeout set to timeout_seconds + 5.0
        python_timeout = timeout_seconds + 5.0
        result = subprocess.run(
            cmd,
            input=sanitized_input.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=python_timeout
        )
        exit_code = result.returncode
        stdout_raw = result.stdout
        stderr_raw = result.stderr

        # Check if the coreutils `timeout` command triggered a timeout (returns 124)
        if exit_code == 124:
            timeout_triggered = True

    except subprocess.TimeoutExpired:
        timeout_triggered = True
        exit_code = 124
        stdout_raw = b""
        # Format the timeout seconds for the error message
        timeout_str = str(int(timeout_seconds)) if float(timeout_seconds).is_integer() else str(timeout_seconds)
        stderr_raw = f"Macaulay2 process timed out after {timeout_str} seconds.".encode('utf-8')

    except (FileNotFoundError, OSError) as e:
        exit_code = 127
        stdout_raw = b""
        stderr_raw = f"Macaulay2 execution failed: {str(e)}".encode('utf-8')

    # 3. Output sanitization
    # Decode and remove null bytes
    stdout_str = stdout_raw.decode('utf-8', errors='replace').replace('\x00', '')
    stderr_str = stderr_raw.decode('utf-8', errors='replace').replace('\x00', '')

    # Normalizes line endings
    stdout_str = stdout_str.replace('\r\n', '\n').replace('\r', '\n')
    stderr_str = stderr_str.replace('\r\n', '\n').replace('\r', '\n')

    # Standardizes class name casing (replace Matrix with matrix)
    stdout_str = stdout_str.replace('Matrix', 'matrix')
    stderr_str = stderr_str.replace('Matrix', 'matrix')

    # Filters out any lines starting with wsl: (case-insensitive) from stderr
    stderr_lines = stderr_str.split('\n')
    filtered_stderr_lines = [
        line for line in stderr_lines
        if not (line.lower().startswith('wsl:') or line.strip().lower().startswith('wsl:'))
    ]
    stderr_str = '\n'.join(filtered_stderr_lines)

    # 4. Interactive execution error heuristics
    # If interactive execution error heuristics apply (e.g. "error" in stderr.lower()
    # or "error:" in stdout.lower() or "syntax error" in stdout.lower()), force exit_code to 1.
    # Note: we do not override timeout/file not found exit codes if they were already set.
    if exit_code not in (124, 127):
        if "error" in stderr_str.lower() or "error:" in stdout_str.lower() or "syntax error" in stdout_str.lower():
            exit_code = 1

    return {
        "exit_code": exit_code,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "timeout": timeout_triggered
    }
