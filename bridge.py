import re
import threading
from typing import Tuple, Any, Callable

def validate_input_string(text: str) -> None:
    """Validates that a string does not contain potential command injection vectors or unsafe characters.
    Only allows letters, numbers, basic math operators, spaces, parentheses, brackets, braces, commas, newlines, colons, underscores.
    """
    if not isinstance(text, str):
        raise TypeError("Input must be a string")
    # Whitelist pattern of allowed characters
    pattern = r"^[a-zA-Z0-9\s\+\-\*\/\^\%\=\(\)\[\]\{\}\,\.\:_\?\!]*$"
    if not re.match(pattern, text):
        raise ValueError("Potential command injection or unsafe characters detected in input.")

def run_with_timeout(func: Callable[..., Any], args: Tuple[Any, ...] = (), kwargs: Any = None, timeout_seconds: float = 30.0) -> Any:
    """Executes a function in a separate thread and raises TimeoutError if it takes too long.
    Protects against Denial of Service (DOS) from long running computations.
    """
    if kwargs is None:
        kwargs = {}
    result = []
    exception = []

    def worker() -> None:
        try:
            res = func(*args, **kwargs)
            result.append(res)
        except Exception as e:
            exception.append(e)

    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"Function execution timed out after {timeout_seconds} seconds.")
    if exception:
        raise exception[0]
    return result[0] if result else None

from mobility_toolkit.engine import run_macaulay2 as engine_run_macaulay2

def run_m2_script(script_content: str, timeout_seconds: float = 60.0, *args: Any, **kwargs: Any) -> Tuple[int, str, str]:
    if not script_content or not script_content.strip():
        return 0, "", ""
    import uuid
    from mobility_toolkit import utils
    temp_file_name = f"m2_script_{uuid.uuid4().hex}_dump.m2"
    utils.save_troubleshooting_dump(temp_file_name, script_content)
    res = engine_run_macaulay2(script_content, timeout_seconds=timeout_seconds)
    utils.log_m2_execution(script_content, res["exit_code"], res["stdout"], res["stderr"])
    return res["exit_code"], res["stdout"], res["stderr"]

def run_macaulay2(script: str, timeout: int = 30, *args: Any, **kwargs: Any) -> Any:
    return engine_run_macaulay2(script, timeout_seconds=float(timeout))

