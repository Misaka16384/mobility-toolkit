import pytest
from mobility_toolkit.utils import verify_qudit_dim

def test_prime_qudit_dim_passes():
    for p in [2, 3, 5, 7, 11, 13]:
        verify_qudit_dim(p)

def test_non_prime_qudit_dim_fails_by_default():
    for np in [4, 6, 8, 9, 10, 12]:
        with pytest.raises(ValueError, match="must be prime"):
            verify_qudit_dim(np)

def test_non_prime_qudit_dim_passes_with_bypass():
    for np in [4, 6, 8, 9, 10, 12]:
        verify_qudit_dim(np, prime_bypass=True)

def test_invalid_qudit_dim_values():
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(1)
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(0)
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(-5)
    with pytest.raises(TypeError):
        verify_qudit_dim("2")
