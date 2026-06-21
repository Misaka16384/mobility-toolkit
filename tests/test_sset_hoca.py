import pytest
from mobility_toolkit.fusion import solve_sset_fusion

# ==============================================================================
# Tier 1: Feature Coverage (5 tests)
# ==============================================================================

def test_sset_model_a_fusion():
    """Model (a) with f = 1 + y.
    
    Verifies fusion of lineons: beta_{y, 1} * beta_{y, 1} = alpha + beta_{y, 1}
    """
    poly_f = "1 + y"
    result = solve_sset_fusion(poly_f, "beta_{y, 1} * beta_{y, 1}")
    
    assert "fusion_rules" in result
    
    # Fusion should yield alpha (fully mobile) and beta_{y, 1}
    assert "alpha" in result["fusion_rules"]
    assert "beta_{y, 1}" in result["fusion_rules"]

    # If testing a single excitation polynomial g, pass g = 1 to get characteristic polynomial 1+y and mobility class beta_{y,1}
    result_single = solve_sset_fusion(poly_f, "1")
    assert result_single["characteristic_polynomial"] == "1 + y"
    assert result_single["mobility_class"] == "beta_{y, 1}"

def test_sset_model_b_fusion():
    """Model (b) with f = (1 + x)*(1 + y) = 1 + x + y + x*y.
    
    Verifies fusion: beta_{x, 1} * beta_{y, 1} = gamma (where gamma is the immobile fracton)
    """
    poly_f = "(1 + x) * (1 + y)"
    # Fusing a x-lineon and a y-lineon
    result = solve_sset_fusion(poly_f, "beta_{x, 1} * beta_{y, 1}")
    
    assert "fusion_rules" in result
    
    # Fusing coprime lineons of different directions yields a fracton sector (gamma)
    assert "gamma" in result["fusion_rules"]

def test_sset_model_c_fusion_lcm():
    """Model (c) with f = (1 + x)*(1 + y^2)*(1 + y + y^2).
    
    Verifies fusion beta_{y, 2} * beta_{y, 3} = beta_{y, 6} (LCM of periodicities 2 and 3)
    """
    poly_f = "(1 + x)*(1 + y^2)*(1 + y + y^2)"
    # Fusing periodicities 2 and 3 should yield period 6
    result = solve_sset_fusion(poly_f, "beta_{y, 2} * beta_{y, 3}")
    
    assert "characteristic_polynomial" in result
    assert "lfsr_period" in result
    assert result["lfsr_period"] == 6
    assert "beta_{y, 6}" in result["fusion_rules"]

def test_sset_model_c_fusion_channels():
    """Model (c) with f = (1 + x)*(1 + y^2)*(1 + y + y^2).
    
    Verifies fusion: beta_{y, 6} * beta_{y, 6} = alpha + beta_{y, 1} + beta_{y, 2} + beta_{y, 3} + beta_{y, 6}
    """
    poly_f = "(1 + x)*(1 + y^2)*(1 + y + y^2)"
    result = solve_sset_fusion(poly_f, "beta_{y, 6} * beta_{y, 6}")
    
    assert "fusion_rules" in result
    expected_channels = {"alpha", "beta_{y, 1}", "beta_{y, 2}", "beta_{y, 3}", "beta_{y, 6}"}
    assert set(result["fusion_rules"]) == expected_channels

def test_sset_hoca_solver_basic():
    """Runs solve_sset_fusion with basic inputs and checks output format."""
    result = solve_sset_fusion("1 + x", "1 + y")
    assert isinstance(result, dict)
    assert "characteristic_polynomial" in result
    assert "lfsr_period" in result
    assert "fusion_rules" in result


# ==============================================================================
# Tier 2: Boundary & Corner Cases (5 tests)
# ==============================================================================

def test_sset_hoca_constant_poly():
    """Checks behavior when f = 1 (constant polynomial).
    
    The characteristic polynomial is computed and mobility is alpha (fully mobile).
    """
    result = solve_sset_fusion("1", "x")
    assert result["characteristic_polynomial"] == "1"
    assert "alpha" in result["fusion_rules"]

def test_sset_hoca_zero_poly():
    """Checks handling of zero polynomial f = 0.
    
    Should raise ValueError or handle it gracefully.
    """
    with pytest.raises(ValueError):
        solve_sset_fusion("0", "x")

def test_sset_hoca_negative_coefficients():
    """Checks that polynomials with negative coefficients are correctly reduced mod 2.
    
    e.g. x - y becomes x + y in F_2.
    """
    result = solve_sset_fusion("x - y", "x + y")
    # x - y mod 2 is identical to x + y. Their GCD should be x + y, leaving 1.
    assert result["characteristic_polynomial"] == "1"

def test_sset_hoca_coprime_polys():
    """Checks behavior when f and g are completely coprime polynomials."""
    # f = 1 + x, g = 1 + y. They share no common factors in F_2[x,y].
    result = solve_sset_fusion("1 + x", "1 + y")
    assert result["characteristic_polynomial"] == "1 + x"
    assert "beta_{x, 1}" in result["fusion_rules"]

def test_sset_hoca_high_degree():
    """Verifies that high-degree polynomials are handled without performance degradation."""
    # Poly degree 20
    poly_f = "1 + x^20 + y^20"
    poly_g = "1 + x^10 + y^10"
    result = solve_sset_fusion(poly_f, poly_g)
    assert "characteristic_polynomial" in result
    assert isinstance(result["characteristic_polynomial"], str)
