import pytest
from mobility_toolkit.grobner import compute_gsd_and_periodicity

# ==============================================================================
# Tier 1: Feature Coverage (5 tests)
# ==============================================================================

def test_bb_codes_gsd_toric():
    """Verifies GSD = 4 for Toric code on a 2x2 torus."""
    # Toric code stabilizer matrix representation
    stabilizer_matrix = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=2)
    
    assert "gsd" in result
    assert "periodicities" in result
    assert result["gsd"] == 4

def test_bb_codes_wcf_periodicity():
    """WCF with N=12, a=5, verifies l_x = l_y = 2."""
    stabilizer_matrix = [
        ["t - 5", "u - 5", "0", "0"],
        ["0", "0", "y - 5", "5 - x"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=12, Ly=12, qudit_dim=12)
    
    assert "periodicities" in result
    assert result["periodicities"]["l_x"] == 2
    assert result["periodicities"]["l_y"] == 2

def test_bb_codes_wcf_gsd():
    """WCF with N=12, a=5 and sizes Lx=12, Ly=12, verifies GSD matches analytical formula."""
    stabilizer_matrix = [
        ["t - 5", "u - 5", "0", "0"],
        ["0", "0", "y - 5", "5 - x"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=12, Ly=12, qudit_dim=12)
    
    assert "gsd" in result
    assert result["gsd"] == 144

def test_bb_codes_dcy_periodicity():
    """DCY with N=12, a=10, verifies l_x = 3, l_y = 3."""
    stabilizer_matrix = [
        ["t^2 - 11*t + 10", "u^2 - 11*u + 10", "0", "0"],
        ["0", "0", "y^2 - 11*y + 10", "-x^2 + 11*x - 10"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=12, Ly=12, qudit_dim=12)
    
    assert "periodicities" in result
    assert result["periodicities"]["l_x"] == 3
    assert result["periodicities"]["l_y"] == 3

def test_bb_codes_dcy_gsd():
    """DCY with N=12, a=10 and sizes Lx=12, Ly=12, verifies GSD matches analytical formula."""
    stabilizer_matrix = [
        ["t^2 - 11*t + 10", "u^2 - 11*u + 10", "0", "0"],
        ["0", "0", "y^2 - 11*y + 10", "-x^2 + 11*x - 10"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=12, Ly=12, qudit_dim=12)
    
    assert "gsd" in result
    assert result["gsd"] == 104976


# ==============================================================================
# Tier 2: Boundary & Corner Cases (5 tests)
# ==============================================================================

def test_bb_codes_invalid_matrix():
    """Trivial or empty stabilizer matrix, checks error handling (ValueError)."""
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity([], Lx=2, Ly=2, qudit_dim=2)

def test_bb_codes_negative_Lx_Ly():
    """Negative or zero torus dimensions, checks validation (ValueError)."""
    stabilizer_matrix = [["1 - x", "1 - y"]]
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity(stabilizer_matrix, Lx=-1, Ly=2, qudit_dim=2)
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=0, qudit_dim=2)

def test_bb_codes_qudit_dim_one():
    """Qudit dimension N=1, checks validation (ValueError for invalid qudit dimension)."""
    stabilizer_matrix = [["1 - x", "1 - y"]]
    with pytest.raises(ValueError):
        compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=1)

def test_bb_codes_huge_torus():
    """Checks that a very large torus size is handled (either runs or raises OverflowError/ValueError)."""
    stabilizer_matrix = [["1 - x", "1 - y"]]
    # A huge torus Lx, Ly might raise ValueError if validation prevents it or handle it
    with pytest.raises((ValueError, OverflowError)):
        compute_gsd_and_periodicity(stabilizer_matrix, Lx=1000000, Ly=1000000, qudit_dim=2)

def test_bb_codes_non_coprime():
    """Checks that the code handles N and a sharing factors (e.g. N=12, a=6)."""
    stabilizer_matrix = [
        ["x^6 - 1", "y - 1"],
        ["0", "x - 1"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=12, Ly=12, qudit_dim=12)
    assert "gsd" in result
    assert "periodicities" in result


def test_bb_codes_general_periodicity_and_gsd():
    """Table I General BB code (N=12, f=4x^3+y^2+y, g=6y^5+x^2+x)."""
    stabilizer_matrix = [
        ["4*t^3 + u^2 + u", "6*u^5 + t^2 + t", "0", "0"],
        ["0", "0", "6*y^5 + x^2 + x", "-4*x^3 - y^2 - y"]
    ]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=18, Ly=18, qudit_dim=12)
    assert result["periodicities"]["l_x"] == 1
    assert result["periodicities"]["l_y"] == 2
    assert result["gsd"] == 16
