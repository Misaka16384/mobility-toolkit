import os
import sys

# Add project root and skills directories to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

skills_dir = os.path.join(PROJECT_ROOT, "KnowledgeBase", ".agents", "skills")
if skills_dir not in sys.path:
    sys.path.insert(0, skills_dir)

from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.fusion import analyze_fusion_interference
from mobility_toolkit.reference_models import TORIC_CODE_2D

def test_toric_code_point_like_excitations():
    """Test 1: 2D Toric Code point-like excitations.
    
    Verify that point-like excitations (0-excitations) have krull_dimension == 0.
    """
    stabilizer_matrix = TORIC_CODE_2D
    qudit_dim = 2
    
    res = compute_ext_krull(stabilizer_matrix, qudit_dim=qudit_dim)
    assert res["krull_dimension"] == 0

def test_bivariate_bicycle_code_periodicity():
    """Test 2: Bivariate-Bicycle Code Periodicity.
    
    Verify Z12 ring ideal generators for periodicity. Check WCF and DCY models.
    """
    # WCF model
    wcf_matrix = [
        ["t - 5", "u - 5", "0", "0"],
        ["0", "0", "y - 5", "5 - x"]
    ]
    wcf_res = compute_gsd_and_periodicity(wcf_matrix, Lx=12, Ly=12, qudit_dim=12)
    assert wcf_res["periodicities"]["l_x"] == 2
    assert wcf_res["periodicities"]["l_y"] == 2

    # DCY model
    dcy_matrix = [
        ["t^2 - 11*t + 10", "u^2 - 11*u + 10", "0", "0"],
        ["0", "0", "y^2 - 11*y + 10", "-x^2 + 11*x - 10"]
    ]
    dcy_res = compute_gsd_and_periodicity(dcy_matrix, Lx=12, Ly=12, qudit_dim=12)
    assert dcy_res["periodicities"]["l_x"] == 3
    assert dcy_res["periodicities"]["l_y"] == 3

def test_high_dimensional_collapse():
    """Test 3: High-Dimensional Collapse.
    
    Verify that fusion of two lineons with a relative shift results in a dimension collapse.
    """
    # Stabilizer matrix of a lineon along the x-axis under qudit_dim = 2.
    # Note: 0*x is included to activate the x coordinate to make it a lineon variety
    # of dimension 1, rather than 0.
    stabilizer_matrix = [["1 - y", "1 - z", "0*x", "0"]]
    shifts = [[0, 1, 0]]
    
    res = analyze_fusion_interference(stabilizer_matrix, qudit_dim=2, shifts=shifts)
    assert res["annihilator_dimension"] == 1
    assert res["dimension_drop"] is True
