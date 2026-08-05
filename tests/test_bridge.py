from mobility_toolkit.bridge import run_m2_script

# ==============================================================================
# Tier 1: Feature Coverage (5 tests)
# ==============================================================================

def test_bridge_simple_arithmetic():
    """Runs a script doing basic arithmetic and checks if it computes correctly."""
    script = "2 + 2"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert "4" in stdout

def test_bridge_ring_definition():
    """Runs a script defining a polynomial ring in M2."""
    script = "R = ZZ/2[x, y]; x^2 + y"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert "x" in stdout

def test_bridge_ideal_generators():
    """Runs a script generating an ideal and finding its minimal generators."""
    script = "R = ZZ/2[x, y]; I = ideal(x^2, x*y); generators gb I"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert "matrix" in stdout.lower()

def test_bridge_multiline_script():
    """Runs a multiline script to define objects step-by-step and inspect results."""
    script = (
        "R = ZZ/2[x, y, z]\n"
        "I = ideal(x + y, y + z)\n"
        "dim I\n"
    )
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert "1" in stdout

def test_bridge_exit_code_zero():
    """Runs a simple correct command and asserts that the exit code is exactly 0."""
    script = "print \"Hello from M2\""
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert "Hello" in stdout


# ==============================================================================
# Tier 2: Boundary & Corner Cases (5 tests)
# ==============================================================================

def test_bridge_syntax_error():
    """Runs an invalid M2 script with syntax errors and asserts failure (non-zero exit or stderr content)."""
    script = "R = ZZ/2[x, y]; x +"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code != 0 or "error" in stderr.lower()

def test_bridge_nonexistent_vars():
    """Runs a script referencing undefined variables, checks error output handling."""
    script = "unknown_variable + 1"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code != 0 or "undefined" in stderr.lower() or "not defined" in stderr.lower()

def test_bridge_empty_script():
    """Runs an empty script and checks that it exits gracefully without errors."""
    script = ""
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert stdout == ""

def test_bridge_large_output():
    """Runs a script that generates a very large stdout payload and checks that the bridge does not hang."""
    script = "apply(1000, i -> print i)"
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0
    assert len(stdout) > 1000

def test_bridge_unicode_characters():
    """Runs a script containing special/unicode characters to ensure shell encoding works properly."""
    script = "print \"测试 unicode\""
    exit_code, stdout, stderr = run_m2_script(script)
    assert exit_code == 0


def test_bridge_timeout(monkeypatch):
    """Mocks subprocess.run to raise subprocess.TimeoutExpired and verifies handling."""
    import subprocess

    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=60)

    monkeypatch.setattr(subprocess, "run", mock_run)

    exit_code, stdout, stderr = run_m2_script("2 + 2")
    assert exit_code == 124
    assert stdout == ""
    assert "Macaulay2 process timed out after 60 seconds." in stderr


def test_bridge_file_not_found_error(monkeypatch):
    """Mocks subprocess.run to raise FileNotFoundError and verifies handling."""
    import subprocess

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'wsl'")

    monkeypatch.setattr(subprocess, "run", mock_run)

    exit_code, stdout, stderr = run_m2_script("2 + 2")
    assert exit_code == 127
    assert stdout == ""
    assert "Macaulay2 execution failed:" in stderr
    assert "No such file or directory" in stderr


