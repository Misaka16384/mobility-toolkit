from mobility_toolkit.translate import normalize_laurent_poly
from mobility_toolkit.fusion import check_ideal_principal, analyze_annihilator_fusion
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.reference_models import TORIC_CODE_2D

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

def test_homology_does_not_auto_attach_unrelated_sset_analysis():
    """The Ruba--Yang Ext path stays separate from the independent SSET API."""
    res_toric = compute_ext_krull(TORIC_CODE_2D, qudit_dim=2)
    assert "sset_properties" not in res_toric
