import pytest
from mobility_toolkit.translate import normalize_laurent_poly
from mobility_toolkit.fusion import check_ideal_principal, analyze_annihilator_fusion, solve_sset_fusion
from mobility_toolkit.homology import compute_ext_krull

def test_normalize_laurent_poly():
    """Verify normalize_laurent_poly clears denominators and normalizes Laurent polynomials."""
    # Test 2D legacy variables
    assert normalize_laurent_poly("x^2*u - y + 1") == "x^2 - y^2 + y" # u is y^-1
    assert normalize_laurent_poly("x*t - 1") == "1 - 1" or normalize_laurent_poly("x*t - 1") == "0"
    # Test unified variables
    assert normalize_laurent_poly("x1^2*t2 - x2 + 1") == "x1^2 - x2^2 + x2"
    # Test 3D unified variables
    assert normalize_laurent_poly("x1*t3 + x2^2*t1") == "x1^2 + x2^2*x3"

def test_check_ideal_principal():
    """Verify check_ideal_principal detects principal ideals and extracts their generators."""
    # Check principal ideal
    ring_def = "R = ZZ/2[x1, t1, x2, t2] / ideal(x1*t1 - 1, x2*t2 - 1)"
    is_p, gen = check_ideal_principal(ring_def, ["x1 + x2 + 1"])
    assert is_p is True
    assert gen == "x1 + x2 + 1"
    
    # Check non-principal ideal
    is_p2, gen2 = check_ideal_principal(ring_def, ["x1 - 1", "x2 - 1"])
    assert is_p2 is False
    assert gen2 is None

def test_analyze_annihilator_fusion():
    """Verify L2 -> L3 annihilator fusion computes SSET rules directly from generators."""
    # Model A: generators = ["y + 1"] -> lineon beta_{y, 1}
    res = analyze_annihilator_fusion(
        generators=["y + 1"],
        qudit_dim=2,
        variables=["x", "y"]
    )
    assert res["is_principal"] is True
    assert res["normalized_generator"] == "y + 1"
    assert "beta_" in res["mobility_class"]
    assert res["fusion_rules"] == [res["mobility_class"]]

def test_l1_l3_automatic_merge():
    """Verify compute_ext_krull automatically checks and computes SSET properties if principal."""
    # 2D Toric Code (non-principal annihilator, should NOT have sset_properties)
    toric_code = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    res_toric = compute_ext_krull(toric_code, qudit_dim=2)
    assert "sset_properties" not in res_toric
    
    # Model A (principal annihilator, should have sset_properties)
    # Model A decoration polynomial f = 1 + y. In 2D, stabilizer is:
    # Plaquette term is 1 - y, coupling is 1 - y.
    model_a = [
        ["1 - y", "0"],
        ["0", "1 - y"]
    ]
    res_model_a = compute_ext_krull(model_a, qudit_dim=2)
    assert "sset_properties" in res_model_a
    assert res_model_a["sset_properties"]["is_principal"] is True
    assert "beta_" in res_model_a["sset_properties"]["mobility_class"]
