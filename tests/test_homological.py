import pytest
from mobility_toolkit.homology import compute_ext_krull

# ==============================================================================
# Tier 1: Feature Coverage (5 tests)
# ==============================================================================

def test_homological_toric_ext():
    """Toric code, verifies Ext modules and Krull dimension for electric charge (dimension = 0, fully mobile)."""
    # 2D Toric code stabilizer matrix representation
    stabilizer_matrix = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=2)
    
    assert "krull_dimension" in result
    assert "ext_modules" in result
    # Electric charge has Krull dimension 0 (fully mobile)
    assert result["krull_dimension"] == 0

def test_homological_xcube_ext():
    """X-Cube model, verifies Ext modules and Krull dimension (dimension = 2, fractons)."""
    # X-Cube has 3D excitation properties
    stabilizer_matrix = [
        ["1 - x", "1 - y", "1 - z", "0"],
        ["0", "1 - y", "1 - z", "1 - x"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=2)
    
    assert "krull_dimension" in result
    # Fractons in X-cube have Krull dimension 2
    assert result["krull_dimension"] == 2

def test_homological_krull_trivial():
    """Verifies Krull dimension for trivial modules (should be -1 or 0 depending on convention)."""
    stabilizer_matrix = [
        ["1", "0"],
        ["0", "1"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=2)
    assert "krull_dimension" in result
    assert result["krull_dimension"] in (-1, 0)

def test_homological_ext_format():
    """Checks Ext solver output dictionary structure and type matching."""
    stabilizer_matrix = [
        ["1 - x", "1 - y"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=3)
    assert isinstance(result, dict)
    assert "krull_dimension" in result
    assert "ext_modules" in result
    assert isinstance(result["ext_modules"], list)

def test_homological_qudit_toric():
    """Toric code generalised to qudits (e.g., N=3), verifies Krull dimension of Ext modules."""
    stabilizer_matrix = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=3)
    assert "krull_dimension" in result
    assert result["krull_dimension"] == 0


# ==============================================================================
# Tier 2: Boundary & Corner Cases (5 tests)
# ==============================================================================

def test_homological_invalid_stabilizer():
    """Checks error handling for improperly formatted stabilizer matrices (e.g. non-string elements)."""
    with pytest.raises(ValueError):
        compute_ext_krull([[1, 2], [3, 4]], qudit_dim=2)

def test_homological_large_qudit_dim():
    """Qudit dimension N extremely large, checks validation or overflow handling."""
    stabilizer_matrix = [["1 - x", "1 - y"]]
    with pytest.raises((ValueError, OverflowError)):
        compute_ext_krull(stabilizer_matrix, qudit_dim=99999999)

def test_homological_empty_matrix():
    """Verifies behavior of Ext module solver for empty stabilizer matrix."""
    with pytest.raises(ValueError):
        compute_ext_krull([], qudit_dim=2)

def test_homological_high_dimensional_space():
    """Excitations in higher-dimensional space (e.g. 4D: x, y, z, w), checks dimensions."""
    stabilizer_matrix = [
        ["1 - x", "1 - y", "1 - z", "1 - w"]
    ]
    result = compute_ext_krull(stabilizer_matrix, qudit_dim=2)
    assert "krull_dimension" in result
    assert result["krull_dimension"] >= 0

def test_homological_non_prime_qudit():
    """Ext module calculation with composite qudit dimension (e.g. N=6), checks prime factorization or error."""
    stabilizer_matrix = [
        ["1 - x", "1 - y"]
    ]
    # If the system only supports prime dimension qudits for homological invariants, it may raise ValueError
    with pytest.raises(ValueError):
        compute_ext_krull(stabilizer_matrix, qudit_dim=6)
