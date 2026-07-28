import pytest

from mobility_toolkit.fusion import analyze_annihilator_fusion, solve_sset_fusion
from mobility_toolkit.utils import verify_modulus, verify_qudit_dim

def test_prime_qudit_dim_passes():
    for p in [2, 3, 5, 7, 11, 13]:
        verify_qudit_dim(p)

def test_non_prime_qudit_dim_fails_by_default():
    for np in [4, 6, 8, 9, 10, 12]:
        with pytest.raises(ValueError, match="must be prime"):
            verify_qudit_dim(np)

def test_composite_modulus_passes_general_validation():
    for np in [4, 6, 8, 9, 10, 12]:
        verify_modulus(np)

def test_invalid_qudit_dim_values():
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(1)
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(0)
    with pytest.raises(ValueError, match="must be >= 2"):
        verify_qudit_dim(-5)
    with pytest.raises(TypeError):
        verify_qudit_dim("2")
    with pytest.raises(TypeError):
        verify_qudit_dim(True)


def test_invalid_general_modulus_values():
    for value in [1, 0, -5]:
        with pytest.raises(ValueError, match="must be >= 2"):
            verify_modulus(value)
    for value in ["2", True]:
        with pytest.raises(TypeError):
            verify_modulus(value)


def test_sset_fusion_apis_reject_composite_coefficients_before_backend():
    with pytest.raises(ValueError, match="must be prime"):
        solve_sset_fusion("x + 1", "1", qudit_dim=4)
    with pytest.raises(ValueError, match="must be prime"):
        analyze_annihilator_fusion(["x + 1"], qudit_dim=4)
