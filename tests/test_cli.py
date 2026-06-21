import pytest
import json
from unittest.mock import patch
from mobility_toolkit.__main__ import main

def test_cli_homology():
    test_args = [
        "__main__.py",
        "homology",
        "--stabilizer",
        '[["1 - x", "1 - y"]]',
        "--qudit-dim",
        "2",
        "--prime-bypass"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "krull_dimension" in result

def test_cli_mobility():
    test_args = [
        "__main__.py",
        "mobility",
        "--generators",
        '["x - 1", "y - 1"]',
        "--qudit-dim",
        "2"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "mobility_dimension" in result

def test_cli_grobner():
    test_args = [
        "__main__.py",
        "grobner",
        "--stabilizer",
        '[["x - 1", "y - 1"]]',
        "--Lx", "2",
        "--Ly", "2",
        "--qudit-dim",
        "2"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "gsd" in result

def test_cli_fusion_interference():
    test_args = [
        "__main__.py",
        "fusion-interference",
        "--stabilizer",
        '[["1 - x", "1 - y"]]',
        "--qudit-dim",
        "2",
        "--shifts",
        '[[1, 0], [0, 1]]'
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "annihilator_dimension" in result

def test_cli_sset_fusion():
    test_args = [
        "__main__.py",
        "sset-fusion",
        "--poly-f",
        "1 + x + y",
        "--poly-g",
        "1 + x"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "characteristic_polynomial" in result

def test_cli_search():
    test_args = [
        "__main__.py",
        "search",
        "--qudit-dim",
        "2",
        "--target-dim",
        "0",
        "--max-trials",
        "5"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert "status" in result

def test_cli_db():
    test_args = [
        "__main__.py",
        "db",
        "init"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert result["status"] == "success"

def test_cli_error_missing_arg():
    test_args = [
        "__main__.py",
        "homology",
        "--qudit-dim",
        "2"
    ]
    with patch("sys.argv", test_args), patch("sys.stdout") as mock_stdout:
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
        output_str = "".join([call.args[0] for call in mock_stdout.write.call_args_list])
        result = json.loads(output_str)
        assert result["status"] == "error"
