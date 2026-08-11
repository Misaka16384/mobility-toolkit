import pytest
from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.fusion import solve_sset_fusion
from mobility_toolkit.reference_models import TORIC_CODE_2D

from mobility_toolkit.engine import describe_m2_backend

M2_AVAILABLE = bool(describe_m2_backend()["available"])

# ==============================================================================
# Tier 3: Cross-Feature Interactions (5 tests)
# ==============================================================================

def test_cross_bridge_and_homological():
    """Checks that the homological solver successfully interfaces with the WSL-M2 bridge.
    
    Under the hood, compute_ext_krull calls run_m2_script.
    """
    stabilizer_matrix = [["1 - x", "1 - y"]]
    # This should trigger compute_ext_krull which uses WSL-M2 bridge.
    result = compute_ext_krull(
        stabilizer_matrix, qudit_dim=2, validate_stabilizer=False
    )
    assert "krull_dimension" in result

def test_cross_bridge_and_grobner():
    """Checks that the Grobner solver successfully interfaces with the WSL-M2 bridge.
    
    Under the hood, compute_gsd_and_periodicity calls run_m2_script.
    """
    stabilizer_matrix = [["1 - x", "1 - y"]]
    result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=2)
    assert "gsd" in result

def test_cross_grobner_and_homological():
    """Compares the results of Grobner and Homological solvers on the Toric Code.
    
    If Krull dimension is 0 (fully mobile), periodicities should be trivial or well-behaved,
    and GSD on a Lx x Ly torus must be qudit_dim^(2 * gcd(Lx, Ly)) etc.
    """
    stabilizer_matrix = TORIC_CODE_2D
    qudit_dim = 2
    
    hom_result = compute_ext_krull(stabilizer_matrix, qudit_dim=qudit_dim)
    grob_result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=2, Ly=2, qudit_dim=qudit_dim)
    
    # Asserting consistency
    if hom_result["krull_dimension"] == 0:
        assert grob_result["gsd"] == qudit_dim ** 2

def test_cross_hoca_and_grobner():
    """Compares HOCA (pure Python) with Grobner solver (via M2) for an SSET model.
    
    For a 1D model (e.g. f = 1 + y), the LFSR period from HOCA should match
    the periodicity computed via Grobner basis.
    """
    poly_f = "1 + y"
    poly_g = "1"
    
    hoca_result = solve_sset_fusion(poly_f, poly_g)
    
    # We can model the SSET as a stabilizer matrix for compute_gsd_and_periodicity
    # to find the periodicity directly.
    stabilizer_matrix = [["1 - y"]]
    grob_result = compute_gsd_and_periodicity(stabilizer_matrix, Lx=1, Ly=6, qudit_dim=2)
    
    assert hoca_result["lfsr_period"] == grob_result["periodicities"]["l_y"]

@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_cross_full_pipeline():
    """Executes the full pipeline of bridge execution, SSET fusion, homological Ext, and Grobner GSD."""
    # 1. Test Bridge
    exit_code, stdout, stderr = run_m2_script("2 + 2")
    assert exit_code == 0
    
    # 2. Test HOCA
    hoca_res = solve_sset_fusion("1 + y", "1")
    assert hoca_res["characteristic_polynomial"] == "1 + y"
    
    # 3. Test Homological
    hom_res = compute_ext_krull(TORIC_CODE_2D, qudit_dim=2)
    assert hom_res["krull_dimension"] >= 0
    
    # 4. Test Grobner
    grob_res = compute_gsd_and_periodicity(TORIC_CODE_2D, Lx=2, Ly=2, qudit_dim=2)
    assert grob_res["gsd"] >= 0
