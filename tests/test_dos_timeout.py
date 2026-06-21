import time
import pytest
from mobility_toolkit.bridge import run_with_timeout

def test_timeout_fast_execution():
    def fast_func(x, y):
        return x + y
    res = run_with_timeout(fast_func, args=(3, 5), timeout_seconds=1.0)
    assert res == 8

def test_timeout_dos_interruption():
    def hanging_func():
        while True:
            time.sleep(0.01)
    with pytest.raises(TimeoutError):
        run_with_timeout(hanging_func, timeout_seconds=0.1)

def test_timeout_exception_propagation():
    def error_func():
        raise ZeroDivisionError("division by zero")
    with pytest.raises(ZeroDivisionError):
        run_with_timeout(error_func, timeout_seconds=1.0)
