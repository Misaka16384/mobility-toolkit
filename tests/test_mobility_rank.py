import pytest
from mobility_toolkit.mobility import compute_true_mobility_dimension

def test_mobility_rank_toric():
    """Toric code anyons should have mobility dimension 2."""
    result = compute_true_mobility_dimension(["x - 1", "y - 1"], qudit_dim=2)
    assert result["mobility_dimension"] == 2
    assert result["variables"] == ["x", "y"]

def test_mobility_rank_planon_3d():
    """Planon in 3D (mobile in x and y, but not z) should have mobility dimension 2."""
    result = compute_true_mobility_dimension(["x - 1", "y - 1"], qudit_dim=2, all_vars=["x", "y", "z"])
    assert result["mobility_dimension"] == 2
    assert result["variables"] == ["x", "y", "z"]
    # Kernel basis should span the xy plane (e.g. [1,0,0] and [0,1,0])
    basis = result["kernel_basis"]
    assert len(basis) == 2
    # Ensure z-component is 0 in all basis vectors
    for vec in basis:
        assert vec[2] == 0

def test_mobility_rank_lineon_3d():
    """Lineon in 3D (mobile in z, but not x and y) should have mobility dimension 1."""
    result = compute_true_mobility_dimension(["z - 1"], qudit_dim=2, all_vars=["x", "y", "z"])
    assert result["mobility_dimension"] == 1
    assert result["variables"] == ["x", "y", "z"]
    # Kernel basis should span the z axis (e.g. [0,0,1])
    basis = result["kernel_basis"]
    assert len(basis) == 1
    assert basis[0] == [0, 0, 1]

def test_mobility_rank_haah_fracton():
    """Haah's code point charge should have true mobility dimension 0 (Type II fracton)."""
    result = compute_true_mobility_dimension(["1 + x + y + z", "1 + x*y + y*z + z*x"], qudit_dim=2)
    assert result["mobility_dimension"] == 0
    assert result["variables"] == ["x", "y", "z"]
    assert len(result["kernel_basis"]) == 0

def test_mobility_rank_3d_toric():
    """3D Toric code point charges and loops should have mobility dimension 3."""
    result = compute_true_mobility_dimension(["x - 1", "y - 1", "z - 1"], qudit_dim=2)
    assert result["mobility_dimension"] == 3
    assert result["variables"] == ["x", "y", "z"]
    assert len(result["kernel_basis"]) == 3

