import pytest
from mobility_toolkit.translate import translate_stabilizers
from mobility_toolkit.fusion import parse_poly_str
from mobility_toolkit.grobner import compute_gsd_and_periodicity

# ==============================================================================
# 1. Extremes in Dynamic Ring Promotion (R1)
# ==============================================================================

def test_extreme_ring_promotion_10():
    """Test dynamic ring promotion with dimension 10 explicitly specified."""
    res = translate_stabilizers(
        [["x - 1", "y - 1"]], qudit_dim=2, spatial_dim=10,
        validate_stabilizer=False,
    )
    assert len(res["variables"]) == 20  # x1..x10, t1..t10
    assert "x10" in res["variables"]
    assert "t10" in res["variables"]
    assert "x10*t10 - 1" in res["ring_definition"]

def test_extreme_ring_promotion_15_implicit():
    """Test dynamic ring promotion to dimension 15 based on unified variable index in input."""
    res = translate_stabilizers([["x15 + 1", "0"]], qudit_dim=2)
    assert len(res["variables"]) == 30  # x1..x15, t1..t15
    assert "x15" in res["variables"]
    assert "t15" in res["variables"]
    assert "x15*t15 - 1" in res["ring_definition"]

def test_compute_gsd_and_periodicity_dimension_10():
    """Test compute_gsd_and_periodicity with a 10-dimensional torus to verify scalability."""
    stabilizer = [["x1 - 1", "x2 - 1"]]
    res = compute_gsd_and_periodicity(stabilizer, qudit_dim=2, L=[2]*10)
    assert res["gsd"] == 2 ** 512
    # All 10 periodicities should be populated
    for i in range(1, 11):
        assert f"l_{i}" in res["periodicities"]
    # Check values: x1 and x2 are active and constrained to period 1
    assert res["periodicities"]["l_x"] == 1
    assert res["periodicities"]["l_y"] == 1
    # Check other inactive dimensions are infinite (0)
    for i in range(3, 11):
        assert res["periodicities"][f"l_{i}"] == 0

# ==============================================================================
# 2. Complex Z2Polynomial Parsing (R2)
# ==============================================================================

def test_complex_parsing_nested_parentheses():
    """Test parsing of heavily nested parentheses expressions."""
    # ((x + y) * (x + 1)) * (y + 1)
    # = (x^2 + x + x*y + y) * (y + 1)
    # = x^2*y + x^2 + x*y + x + x*y^2 + x*y + y^2 + y
    # = x^2*y + x^2 + x + x*y^2 + y^2 + y  (since 2*x*y = 0 mod 2)
    terms = parse_poly_str("((x + y) * (x + 1)) * (y + 1)")
    expected = {(2, 1), (2, 0), (1, 0), (1, 2), (0, 2), (0, 1)}
    assert terms == expected

def test_complex_parsing_subtraction():
    """Test parsing of subtraction and double negation under mod 2 logic."""
    terms_1 = parse_poly_str("x - (y - x)")
    # x - y + x = 2*x - y = y mod 2
    assert terms_1 == {(0, 1)}

    terms_2 = parse_poly_str("-(-x - -y)")
    # -(-x - -y) = x + y mod 2
    assert terms_2 == {(1, 0), (0, 1)}

def test_complex_parsing_power_interactions():
    """Test complex power combinations and distribution properties."""
    # (x + y)^3 = (x + y)^2 * (x + y) = (x^2 + y^2) * (x + y) = x^3 + x^2*y + x*y^2 + y^3 mod 2
    terms_pow = parse_poly_str("(x + y)^3")
    assert terms_pow == {(3, 0), (2, 1), (1, 2), (0, 3)}

    # (x^2 - y^2)^2 = (x^2 + y^2)^2 = x^4 + y^4 mod 2
    terms_pow2 = parse_poly_str("(x^2 - y^2)^2")
    assert terms_pow2 == {(4, 0), (0, 4)}

def test_complex_parsing_mixture():
    """Test complex expressions combining addition, subtraction, powers, and multiplication."""
    # (x + 1)^4 - y^2 * (x - 1)
    # (x + 1)^4 = x^4 + 1 mod 2
    # y^2 * (x - 1) = x*y^2 - y^2 mod 2
    # Result: x^4 + 1 + x*y^2 + y^2 mod 2
    terms = parse_poly_str("(x + 1)^4 - y^2 * (x - 1)")
    expected = {(4, 0), (0, 0), (1, 2), (0, 2)}
    assert terms == expected

def test_complex_parsing_validation_failures():
    """Test that invalid variables or malformed syntax raise ValueError."""
    # Only single-character variables 'x' and 'y' are allowed in parse_poly_str
    with pytest.raises(ValueError):
        parse_poly_str("x + z")
    
    with pytest.raises(ValueError):
        parse_poly_str("x1 + y")

    # Empty parentheses
    with pytest.raises(ValueError):
        parse_poly_str("()")

    # Unmatched parentheses
    with pytest.raises(ValueError):
        parse_poly_str("(x + y")

# ==============================================================================
# 3. Large/Infinite Periodicities & Degenerate Case GSD (R3 & R4)
# ==============================================================================

def test_degenerate_infinite_periodicity():
    """Verify that a degenerate stabilizer yields infinite fusion rules and infinite periodicity (l=0)."""
    # stabilizer with active variable x1 but no constraint on x1
    stabilizer = [["x1*t1 - 1"]]
    res = compute_gsd_and_periodicity(stabilizer, qudit_dim=2, L=[2, 2])
    
    # x1 is active and unconstrained, so its periodicity is infinite (0)
    assert res["periodicities"]["l_x"] == 0
    # x2 is inactive, so it has infinite periodicity (0)
    assert res["periodicities"]["l_y"] == 0
    
    # Since x1 is not constrained, the original quotient ring is infinite
    assert res["fusion_rules"] == "infinite"
    
    # However on torus L=[2,2], the torus relation x1^2 - 1 is added, making GSD finite
    # S / IGSD has size 2^4 = 16 (basis 1, x1, x2, x1*x2 in ZZ/2), so GSD = 16^2 = 256
    assert res["gsd"] == 256

def test_large_periodicities():
    """Verify that large periodicity constraints are computed correctly without Macaulay2 crashes or timeouts."""
    # Ideal constraints periodicity of x1 to be 256
    # GSD quotient size is 2**(256*256), GSD is 2**131072
    stabilizer_256 = [["x1^256 - 1"]]
    res_256 = compute_gsd_and_periodicity(stabilizer_256, qudit_dim=2, L=[256, 256])
    assert res_256["periodicities"]["l_x"] == 256
    assert res_256["periodicities"]["l_y"] == 0
    assert res_256["gsd"] == 2 ** 131072
    
    # Ideal constraints periodicity of x1 to be 512
    # GSD quotient size is 2**(512*512), GSD is 2**524288
    stabilizer_512 = [["x1^512 - 1"]]
    res_512 = compute_gsd_and_periodicity(stabilizer_512, qudit_dim=2, L=[512, 512])
    assert res_512["periodicities"]["l_x"] == 512
    assert res_512["periodicities"]["l_y"] == 0
    assert res_512["gsd"] == 2 ** 524288
