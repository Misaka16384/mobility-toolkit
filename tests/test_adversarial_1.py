import pytest
from mobility_toolkit.fusion import solve_sset_fusion
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.grobner import compute_gsd_and_periodicity

# ==============================================================================
# 1. HOCA Solver: High-Degree Irreducible Polynomial Hang (Denial of Service)
# ==============================================================================

def test_hoca_high_degree_hang(monkeypatch):
    """Verifies that the HOCA solver does not call get_divisors with extremely large
    numbers (which causes an infinite loop/hang).
    
    We pass a degree-89 irreducible polynomial. Unprotected code will call
    get_divisors(2^89 - 1). We mock get_divisors to raise a RuntimeError if n is huge,
    which will fail the test and expose the hang vulnerability.
    """
    import mobility_toolkit.fusion as hoca
    
    called_with = []
    
    def mock_get_divisors(n):
        called_with.append(n)
        if n > 10000000:
            raise RuntimeError(f"VULNERABILITY_EXPOSED: get_divisors called with extremely large n ({n}), which would cause a Denial of Service hang.")
        return [1]
        
    monkeypatch.setattr(hoca, "get_divisors", mock_get_divisors)
    
    with pytest.raises(ValueError):
        # f = x^89 + x^38 + 1 is irreducible over FF(2)
        solve_sset_fusion("x^89 + x^38 + 1", "1")


# ==============================================================================
# 2. Macaulay2 Script Injections
# ==============================================================================

def test_homological_script_injection():
    """Verifies that the homological solver blocks script injection in the stabilizer matrix.
    
    Adversarial input injects code to execute arbitrary prints.
    A robust solver must validate input strings and raise a ValueError.
    """
    injected_matrix = [["x}}); print \"INJECTION_SUCCESSFUL\"; M = matrix(R, {{x"]]
    with pytest.raises(ValueError):
        compute_ext_krull(injected_matrix, qudit_dim=2)


def test_grobner_script_injection():
    """Verifies that the Gröbner solver blocks script injection in the stabilizer matrix.
    
    Adversarial input injects code into ideal definitions.
    A robust solver must validate input strings and raise a ValueError.
    """
    injected_matrix = [["x) ; print \"INJECTION_SUCCESSFUL\" ; I = ideal(x"]]
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity(injected_matrix, Lx=2, Ly=2, qudit_dim=2)


# ==============================================================================
# 3. Variable Validation Boundaries (Homological & Gröbner)
# ==============================================================================

def test_grobner_invalid_variables():
    """Verifies that the Gröbner solver validates input variables.
    
    The polynomial ring in M2 is hardcoded as S = ZZ[u, t, y, x]. 
    Using 'z' or other variables should be validated and raise a ValueError upfront 
    instead of crashing the M2 bridge with a RuntimeError.
    """
    stabilizer_matrix = [["z - 1", "0"], ["0", "0"]]
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=2)


def test_homological_multi_char_variables():
    """Verifies that the homological solver validates against multi-character variables.
    
    Multi-character variables like 'xx' violate the assumption of variables
    and cause undefined symbols in Macaulay2. The solver should raise a ValueError.
    """
    stabilizer_matrix = [["xx - 1", "0"], ["0", "0"]]
    with pytest.raises(ValueError):
        compute_ext_krull(stabilizer_matrix, qudit_dim=2)


def test_homological_uppercase_variables():
    """Verifies that the homological solver validates against uppercase variables.
    
    The solver only scans for '[a-z]' for ring variables. An uppercase variable like 'X'
    will be omitted from ring definitions but included in the matrix, crashing M2.
    It should raise a ValueError.
    """
    stabilizer_matrix = [["X - 1", "0"], ["0", "0"]]
    with pytest.raises(ValueError):
        compute_ext_krull(stabilizer_matrix, qudit_dim=2)


# ==============================================================================
# 4. HOCA Non-Separable Polynomials
# ==============================================================================

def test_hoca_non_separable_polynomial():
    """Verifies that the HOCA solver raises a NotImplementedError for non-separable 
    multivariate polynomials over FF(2), since SymPy factorization has finite field limitations.
    """
    # x^2 + y^2 + x*y + 1 is non-separable
    with pytest.raises(NotImplementedError):
        solve_sset_fusion("x^2 + y^2 + x*y + 1", "beta_{x, 1}")
