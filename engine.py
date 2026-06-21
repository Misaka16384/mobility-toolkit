import subprocess
from typing import Dict

def run_macaulay2(script_content: str, timeout_seconds: float = 30.0) -> Dict[str, any]:
    """Executes a Macaulay2 script via WSL Ubuntu.

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

    # 2. Execute Macaulay2 script via WSL Ubuntu
    # Command: wsl -d Ubuntu timeout --kill-after=5 <timeout_seconds> M2 --no-readline -q
    # We convert timeout_seconds to string.
    cmd = [
        "wsl",
        "-d",
        "Ubuntu",
        "timeout",
        "--kill-after=5",
        str(timeout_seconds),
        "M2",
        "--no-readline",
        "-q"
    ]

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

        # Check if the WSL timeout command triggered a timeout (returns 124)
        if exit_code == 124:
            timeout_triggered = True

    except subprocess.TimeoutExpired:
        timeout_triggered = True
        exit_code = 124
        stdout_raw = b""
        # Format the timeout seconds for the error message
        timeout_str = str(int(timeout_seconds)) if timeout_seconds.is_integer() else str(timeout_seconds)
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
