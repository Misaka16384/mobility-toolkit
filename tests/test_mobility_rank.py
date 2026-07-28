from mobility_toolkit.mobility import compute_translation_lattice


def test_preferred_translation_lattice_api():
    result = compute_translation_lattice(["x*y - 1"], 5, ["x", "y"])
    assert result["mobility_dimension"] == 1
    assert result["translation_lattice_basis"] in ([[1, 1]], [[-1, -1]])

def test_two_independent_binomials_give_rank_two_translation_lattice():
    result = compute_translation_lattice(["x - 1", "y - 1"], qudit_dim=2)
    assert result["mobility_dimension"] == 2
    assert result["variables"] == ["x", "y"]

def test_xy_translation_lattice_in_declared_three_dimensional_ring():
    result = compute_translation_lattice(["x - 1", "y - 1"], qudit_dim=2, all_vars=["x", "y", "z"])
    assert result["mobility_dimension"] == 2
    assert result["variables"] == ["x", "y", "z"]
    # Kernel basis should span the xy plane (e.g. [1,0,0] and [0,1,0])
    basis = result["kernel_basis"]
    assert len(basis) == 2
    # Ensure z-component is 0 in all basis vectors
    for vec in basis:
        assert vec[2] == 0

def test_z_translation_lattice_in_declared_three_dimensional_ring():
    result = compute_translation_lattice(["z - 1"], qudit_dim=2, all_vars=["x", "y", "z"])
    assert result["mobility_dimension"] == 1
    assert result["variables"] == ["x", "y", "z"]
    # Kernel basis should span the z axis (e.g. [0,0,1])
    basis = result["kernel_basis"]
    assert len(basis) == 1
    assert basis[0] == [0, 0, 1]

def test_non_binomial_haah_generators_are_inconclusive():
    """The binomial algorithm must not invent an answer for a Type-II ideal."""
    result = compute_translation_lattice(["1 + x + y + z", "1 + x*y + y*z + z*x"], qudit_dim=2)
    assert result["status"] == "inconclusive"
    assert result["conclusive"] is False
    assert result["mobility_dimension"] is None
    assert result["variables"] == ["x", "y", "z"]
    assert result["kernel_basis"] is None

def test_three_independent_binomials_give_rank_three_translation_lattice():
    result = compute_translation_lattice(["x - 1", "y - 1", "z - 1"], qudit_dim=2)
    assert result["mobility_dimension"] == 3
    assert result["variables"] == ["x", "y", "z"]
    assert len(result["kernel_basis"]) == 3


def test_diagonal_translation_lattice_counterexample():
    """Ann(q)=(xy-1) permits only diagonal translations, not two axes."""
    result = compute_translation_lattice(["x*y - 1"], qudit_dim=5, all_vars=["x", "y"])
    assert result["status"] == "success"
    assert result["mobility_dimension"] == 1
    assert result["translation_lattice_basis"] in ([[1, 1]], [[-1, -1]])


def test_inverse_variables_are_same_spatial_axes():
    result = compute_translation_lattice(
        ["t*u - 1"], qudit_dim=5, all_vars=["x", "t", "y", "u"]
    )
    assert result["variables"] == ["x", "y"]
    assert result["laurent_relations"] == ["x*t - 1", "y*u - 1"]
    assert result["mobility_dimension"] == 1
    assert result["translation_lattice_basis"] in ([[1, 1]], [[-1, -1]])


def test_inverse_relation_reduces_to_zero():
    result = compute_translation_lattice(
        ["x*t - 1", "x - 1"], qudit_dim=3, all_vars=["x", "t"]
    )
    assert result["mobility_dimension"] == 1
    assert result["translation_lattice_basis"] in ([[1]], [[-1]])


def test_unified_inverse_variable_is_negative_same_axis():
    result = compute_translation_lattice(
        ["x1*t2 - 1"], 3, all_vars=["x1", "t1", "x2", "t2"]
    )
    assert result["variables"] == ["x1", "x2"]
    assert result["mobility_dimension"] == 1
    assert result["translation_lattice_basis"] in ([[1, -1]], [[-1, 1]])


def test_nontrivial_scalar_gives_finite_index_translation_lattice():
    result = compute_translation_lattice(["x - 2"], qudit_dim=5, all_vars=["x"])
    assert result["mobility_dimension"] == 1
    # 2 has multiplicative order four in F_5, hence x^4 acts trivially.
    assert result["translation_lattice_basis"] in ([[4]], [[-4]])


def test_inconsistent_binomial_character_is_unit_ideal():
    result = compute_translation_lattice(["x - 1", "x - 2"], qudit_dim=5)
    assert result["status"] == "trivial"
    assert result["conclusive"] is True
    assert result["mobility_dimension"] is None
    assert "unit ideal" in result["reason"]


def test_cache_key_includes_spatial_ring():
    import mobility_toolkit.mobility as mobility

    mobility._RESULT_CACHE.clear()
    plane = compute_translation_lattice(["x - 1"], 2, all_vars=["x", "y"])
    space = compute_translation_lattice(["x - 1"], 2, all_vars=["x", "y", "z"])
    assert plane["variables"] == ["x", "y"]
    assert space["variables"] == ["x", "y", "z"]
    assert len(mobility._RESULT_CACHE) == 2
