import pytest
import subprocess
from unittest.mock import MagicMock
from mobility_toolkit.engine import run_macaulay2

def test_engine_basic_arithmetic():
    """Runs a script doing basic arithmetic using run_macaulay2."""
    res = run_macaulay2("2 + 2")
    assert res["exit_code"] == 0
    assert "4" in res["stdout"]
    assert res["timeout"] is False

def test_engine_input_sanitization():
    """Checks that null bytes are removed and line endings normalized."""
    # We can pass text containing null bytes and check if it runs without error.
    res = run_macaulay2("2 + 2\x00\r\n")
    assert res["exit_code"] == 0
    assert "4" in res["stdout"]

def test_engine_output_sanitization():
    """Checks output sanitization for Matrix class names and wsl: lines."""
    # We can mock subprocess.run to return a stdout with 'Matrix' and a stderr with 'wsl: warning'
    import subprocess
    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        # Return mock process output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"i1 : Matrix\n"
        mock_result.stderr = b"wsl: some warning\nsome other message\n"
        return mock_result
    # Since we aren't using pytest monkeypatch directly in args for this helper test,
    # we can just temporarily replace subprocess.run and restore it.
    try:
        subprocess.run = mock_run
        res = run_macaulay2("Matrix")
        assert res["exit_code"] == 0
        assert "matrix" in res["stdout"]
        assert "Matrix" not in res["stdout"]
        assert "wsl:" not in res["stderr"]
        assert "some other message" in res["stderr"]
    finally:
        subprocess.run = original_run

def test_engine_execution_error_heuristics():
    """Checks that interactive execution error heuristics force exit_code to 1."""
    # Test stdout contains 'error:'
    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"error: syntax error at or near +\n"
        mock_result.stderr = b""
        return mock_result

    try:
        subprocess.run = mock_run
        res = run_macaulay2("error script")
        assert res["exit_code"] == 1
    finally:
        subprocess.run = original_run

def test_engine_timeout_handling():
    """Checks that subprocess.TimeoutExpired returns timeout=True and exit_code=124."""
    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=30.0)

    try:
        subprocess.run = mock_run
        res = run_macaulay2("timeout script", timeout_seconds=30.0)
        assert res["exit_code"] == 124
        assert res["timeout"] is True
        assert "timed out after 30 seconds" in res["stderr"]
    finally:
        subprocess.run = original_run

def test_engine_file_not_found_handling():
    """Checks that FileNotFoundError returns exit_code=127 and descriptive stderr."""
    original_run = subprocess.run

    def mock_run(*args, **kwargs):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'wsl'")

    try:
        subprocess.run = mock_run
        res = run_macaulay2("missing wsl script")
        assert res["exit_code"] == 127
        assert "No such file or directory" in res["stderr"]
        assert res["timeout"] is False
    finally:
        subprocess.run = original_run
