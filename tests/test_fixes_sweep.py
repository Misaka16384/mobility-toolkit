import pytest
from mobility_toolkit.translate import translate_stabilizers, map_variables_to_unified
from mobility_toolkit.fusion import parse_poly_str, solve_sset_fusion
from mobility_toolkit.grobner import compute_gsd_and_periodicity

# ==============================================================================
# R1: Unified Variable Naming & Dynamic Ring Promotion Tests
# ==============================================================================

def test_unified_variable_translation():
    """Verify legacy and unified variables are mapped and ring dimension is promoted correctly."""
    # Input has legacy variable 'x' and unified variable 'x4' and negative power 'x1^-2'
    stabilizer = [
        ["x^-2 + x4", "y - 1"],
        ["0", "x1^-2 + t4"]
    ]
    res = translate_stabilizers(stabilizer, qudit_dim=2)
    # x^-2 maps to t1^2 (since x is x1, power -2 maps to t1^2)
    # x1^-2 maps to t1^2
    # x4 and t4 exist, so spatial_dim is promoted to max(4, 0, 1) = 4
    # The ring should contain variables up to x4, t4
    assert "x4" in res["variables"]
    assert "t4" in res["variables"]
    assert "x1*t1 - 1" in res["ring_definition"]
    assert "x4*t4 - 1" in res["ring_definition"]

# ==============================================================================
# R2: Pure Python Z2Polynomial Parser Tests
# ==============================================================================

def test_z2_polynomial_parser_subtraction_parentheses():
    """Verify recursive descent parser handles subtraction, power, and parentheses in Z2 polynomials."""
    # Test subtraction (same as addition mod 2)
    terms_sub = parse_poly_str("x - y")
    assert terms_sub == {(1, 0), (0, 1)}
    
    # Test parentheses and multiplication
    terms_paren = parse_poly_str("(1 + x) * (1 + y)")
    # (1 + x)*(1 + y) = 1 + x + y + x*y
    assert terms_paren == {(0, 0), (1, 0), (0, 1), (1, 1)}
    
    # Test power
    terms_pow = parse_poly_str("(x + y)^2")
    # (x+y)^2 = x^2 + 2*x*y + y^2 = x^2 + y^2 mod 2
    assert terms_pow == {(2, 0), (0, 2)}

# ==============================================================================
# R3 & R4: 3D Torus GSD & Elimination-Ideal Periodicity Tests
# ==============================================================================

def test_grobner_3d_torus_gsd_and_periodicity():
    """Verify GSD and periodicities on a 3D torus work correctly and yield expected results."""
    # 3D Toric code style stabilizer (with x1, x2, x3 spatial components)
    stabilizer_3d = [
        ["1 - x1", "1 - x2", "0", "0"],
        ["0", "0", "1 - x2", "1 - x3"]
    ]
    # Torus sizes: L = [2, 2, 2], qudit_dim = 2
    res = compute_gsd_and_periodicity(stabilizer_3d, qudit_dim=2, L=[2, 2, 2])
    
    assert "gsd" in res
    assert "periodicities" in res
    # Should contain 3D periodicities
    assert "l_1" in res["periodicities"]
    assert "l_2" in res["periodicities"]
    assert "l_3" in res["periodicities"]
    
    # Let's check GSD and periodicities for 2D Toric code style (periodicity = 1)
    stabilizer_2d = [
        ["1 - x1", "1 - x2", "0", "0"],
        ["0", "0", "1 - x2", "1 - x1"]
    ]
    res_2d = compute_gsd_and_periodicity(stabilizer_2d, qudit_dim=2, L=[2, 2])
    assert res_2d["periodicities"]["l_x"] == 1
    assert res_2d["periodicities"]["l_y"] == 1
    
    # Let's check GSD and periodicities for WCF code style too (periodicity = 2)
    stabilizer_wcf = [
        ["t - 5", "u - 5", "0", "0"],
        ["0", "0", "y - 5", "5 - x"]
    ]
    res_wcf = compute_gsd_and_periodicity(stabilizer_wcf, qudit_dim=12, L=[12, 12])
    assert res_wcf["periodicities"]["l_x"] == 2
    assert res_wcf["periodicities"]["l_y"] == 2

def test_mcp_compute_grobner_tool():
    """Verify the compute_grobner FastMCP tool accepts the L list parameter correctly."""
    try:
        from mobility_toolkit.mcp_server import compute_grobner
    except (ImportError, SystemExit):
        pytest.skip("FastMCP is not installed in this environment.")
        return
        
    stabilizer = [
        ["1 - x1", "1 - x2"]
    ]
    res = compute_grobner(stabilizer, qudit_dim=2, L=[2, 3])
    assert res["periodicities"]["l_x"] == 2
    assert res["periodicities"]["l_y"] == 3


def test_inactive_torus_dimension_gsd():
    """Verify that inactive torus dimensions are not collapsed and yield correct GSD.
    For a 2D toric code on a 3D torus where the 3rd dimension is inactive, the GSD
    should be GSD(2D toric code)^L_z = 4^2 = 16 (for L_z=2)."""
    stabilizer_2d = [
        ["1 - x1", "1 - x2", "0", "0"],
        ["0", "0", "1 - x2", "1 - x1"]
    ]
    # Torus size 2 in the inactive z-direction (x3)
    res = compute_gsd_and_periodicity(stabilizer_2d, qudit_dim=2, L=[2, 2, 2])
    assert res["gsd"] == 16
    assert res["periodicities"]["l_3"] == 0  # Infinite periodicity since x3 is inactive

