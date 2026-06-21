import pytest
from mobility_toolkit.bridge import validate_input_string

def test_regex_sanitization_safe_inputs():
    safe_strings = [
        "1 - x",
        "t^2 - 11*t + 10",
        "R = ZZ/2[x, y]",
        "ideal(x*t - 1)",
        "{{1 - t, 0}, {0, 1 - x}}",
        "a + b - c * d / e ^ f"
    ]
    for s in safe_strings:
        validate_input_string(s)

def test_regex_sanitization_unsafe_inputs():
    unsafe_strings = [
        "2 + 2; rm -rf /",
        "2 + 2 & echo 'hacked'",
        "cat /etc/passwd | mail",
        "$(whoami)",
        "`id`",
        "echo test > file.txt",
        "cat < input.txt"
    ]
    for s in unsafe_strings:
        with pytest.raises(ValueError):
            validate_input_string(s)

def test_regex_sanitization_type_error():
    with pytest.raises(TypeError):
        validate_input_string(None)
    with pytest.raises(TypeError):
        validate_input_string(123)
