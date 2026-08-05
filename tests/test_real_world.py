from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.fusion import solve_sset_fusion
from mobility_toolkit.reference_models import TORIC_CODE_2D, XCUBE_EQ98

# ==============================================================================
# Tier 4: Real-World Application Scenarios (5 tests)
# ==============================================================================

def test_real_world_toric_code():
    """E2E verification of 2D Toric Code.
    
    Expectations: GSD = 4 on 2x2 torus, Q^0 Krull dimension = 0 (fully mobile charges).
    """
    stabilizer_matrix = TORIC_CODE_2D
    qudit_dim = 2
    
    # 1. Verify homological Krull dimension of Q^0 module
    hom_res = compute_ext_krull(stabilizer_matrix, qudit_dim=qudit_dim)
    assert hom_res["krull_dimension"] == 0
    
    # 2. Verify Ground State Degeneracy (GSD) on torus Lx=2, Ly=2
    grob_res = compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=qudit_dim)
    assert grob_res["gsd"] == 4

def test_real_world_xcube_model():
    """E2E verification of 3D X-Cube Model.
    
    Expectations: the full Eq. (98) presentation has dim Q^0 = 1.
    """
    # Stabilizer generators for X-cube model
    stabilizer_matrix = XCUBE_EQ98
    qudit_dim = 2
    
    hom_res = compute_ext_krull(stabilizer_matrix, qudit_dim=qudit_dim)
    assert hom_res["krull_dimension"] == 1

def test_real_world_zhang_ye_models():
    """E2E verification of Zhang & Ye models (a, b, c) from paper.
    
    Expectations:
    - Model (a) (f = 1 + y): beta_{y, 1} * beta_{y, 1} = alpha + beta_{y, 1}
    - Model (b) (f = (1+x)(1+y)): beta_{x, 1} * beta_{y, 1} = gamma
    - Model (c) (f = (1+x)(1+y^2)(1+y+y^2)):
        beta_{y, 2} * beta_{y, 3} = beta_{y, 6}
        beta_{y, 6} * beta_{y, 6} = alpha + beta_{y, 1} + beta_{y, 2} + beta_{y, 3} + beta_{y, 6}
    """
    # 1. Model (a)
    res_a = solve_sset_fusion("1 + y", "beta_{y, 1} * beta_{y, 1}")
    assert "alpha" in res_a["fusion_rules"]
    assert "beta_{y, 1}" in res_a["fusion_rules"]
    
    # If testing a single excitation polynomial g, pass g = 1 to get characteristic polynomial 1+y and mobility class beta_{y,1}
    res_a_single = solve_sset_fusion("1 + y", "1")
    assert res_a_single["characteristic_polynomial"] == "1 + y"
    assert res_a_single["mobility_class"] == "beta_{y, 1}"
    
    # 2. Model (b)
    res_b = solve_sset_fusion("(1 + x) * (1 + y)", "beta_{x, 1} * beta_{y, 1}")
    assert "gamma" in res_b["fusion_rules"]
    
    # 3. Model (c)
    poly_c = "(1 + x) * (1 + y^2) * (1 + y + y^2)"
    res_c_lcm = solve_sset_fusion(poly_c, "beta_{y, 2} * beta_{y, 3}")
    assert "beta_{y, 6}" in res_c_lcm["fusion_rules"]
    
    res_c_channels = solve_sset_fusion(poly_c, "beta_{y, 6} * beta_{y, 6}")
    expected_channels = {"alpha", "beta_{y, 1}", "beta_{y, 2}", "beta_{y, 3}", "beta_{y, 6}"}
    assert set(res_c_channels["fusion_rules"]) == expected_channels

def test_real_world_wcf_model():
    """E2E verification of WCF model.
    
    Expectations: For N=12, a=5, periodicities l_x = l_y = 2.
    GSD matches Equation (33) of He & Song.
    """
    stabilizer_matrix = [
        ["t - 5", "u - 5", "0", "0"],
        ["0", "0", "y - 5", "5 - x"]
    ]
    Lx, Ly, qudit_dim = 12, 12, 12
    
    res = compute_gsd_and_periodicity(stabilizer_matrix, Lx=Lx, Ly=Ly, qudit_dim=qudit_dim)
    
    # Check periodicities l_x = l_y = 2
    assert res["periodicities"]["l_x"] == 2
    assert res["periodicities"]["l_y"] == 2
    
    # Check GSD matches Equation (33) - expecting 144
    assert res["gsd"] == 144

def test_real_world_dcy_model():
    """E2E verification of DCY model.
    
    Expectations: For N=12, a=10, periodicities l_x = 3, l_y = 3.
    GSD matches analytical computation of He & Song.
    """
    stabilizer_matrix = [
        ["t^2 - 11*t + 10", "u^2 - 11*u + 10", "0", "0"],
        ["0", "0", "y^2 - 11*y + 10", "-x^2 + 11*x - 10"]
    ]
    Lx, Ly, qudit_dim = 12, 12, 12
    
    res = compute_gsd_and_periodicity(stabilizer_matrix, Lx=Lx, Ly=Ly, qudit_dim=qudit_dim)
    
    # Check periodicities
    assert res["periodicities"]["l_x"] == 3
    assert res["periodicities"]["l_y"] == 3
    
    # Check GSD
    assert res["gsd"] == 104976


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
