import os
import sys
import pytest
import sqlite3
import json

# Add project root and skills directories to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

skills_dir = os.path.join(PROJECT_ROOT, "KnowledgeBase", ".agents", "skills")
if skills_dir not in sys.path:
    sys.path.insert(0, skills_dir)

from mobility_toolkit.translate import translate_to_algebra
from mobility_toolkit.homology import compute_homology_and_mobility
from mobility_toolkit.fusion import analyze_fusion_interference
from mobility_toolkit.registry import query_vector_db, DB_PATH

@pytest.fixture(autouse=True)
def clean_db():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    yield
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

# ==============================================================================
# 1. Tests for translate_to_algebra
# ==============================================================================

def test_translate_to_algebra_basic():
    """Verify basic translation with positive and negative powers."""
    stabilizer_matrix = [
        ["1 - x^-1", "1 - y**-2", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    res = translate_to_algebra(stabilizer_matrix, qudit_dim=2)
    assert res["variables"] == ["x", "t", "y", "u"]
    assert "ZZ/2" in res["ring_definition"]
    assert "ideal(x*t - 1, y*u - 1)" in res["ring_definition"]
    
    # Transposed matrix definition checking
    assert res["matrix_definition"] == "{{1 - t, 0}, {1 - u^2, 0}, {0, 1 - y}, {0, 1 - x}}"

def test_translate_to_algebra_3d():
    """Verify 3D translation with z/w."""
    stabilizer_matrix = [
        ["1 - x", "1 - y", "1 - z**-3", "0"]
    ]
    res = translate_to_algebra(stabilizer_matrix, qudit_dim=3)
    assert res["variables"] == ["x", "t", "y", "u", "z", "w"]
    assert "ideal(x*t - 1, y*u - 1, z*w - 1)" in res["ring_definition"]
    assert res["matrix_definition"] == "{{1 - x}, {1 - y}, {1 - w^3}, {0}}"

def test_translate_to_algebra_validation():
    """Test error handling for invalid inputs."""
    with pytest.raises(ValueError):
        translate_to_algebra([], 2)
    with pytest.raises(ValueError):
        translate_to_algebra([["1 - x"], ["1 - y", "0"]], 2)
    with pytest.raises(ValueError):
        translate_to_algebra([["1 - a"]], 2)  # invalid variable
    with pytest.raises(ValueError):
        translate_to_algebra([["1 - x"]], 4)  # non-prime qudit_dim

# ==============================================================================
# 2. Tests for compute_homology_and_mobility
# ==============================================================================

def test_compute_homology_and_mobility_toric():
    """Verify Krull dimension is 0 for Toric Code point excitations (p_ext=0)."""
    stabilizer_matrix = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    res = compute_homology_and_mobility(stabilizer_matrix, qudit_dim=2, p_ext=0)
    assert res["krull_dimension"] == 0
    assert "cokernel" in res["ext_modules"][0]

def test_compute_homology_and_mobility_xcube():
    """Verify Krull dimension is 2 for X-Cube point excitations (p_ext=0)."""
    stabilizer_matrix = [
        ["1 - x", "1 - y", "1 - z", "0"],
        ["0", "1 - y", "1 - z", "1 - x"]
    ]
    res = compute_homology_and_mobility(stabilizer_matrix, qudit_dim=2, p_ext=0)
    assert res["krull_dimension"] == 2

# ==============================================================================
# 3. Tests for analyze_fusion_interference
# ==============================================================================

def test_analyze_fusion_interference_no_drop():
    """Verify that a shift which doesn't annihilate does not cause dimension drop."""
    # 2D lineon variety along y (annihilator dim is 1)
    stabilizer_matrix = [
        ["1 - x", "0*y"]
    ]
    # Shift along y direction (dx=0, dy=1), no drop
    shifts = [[0, 1]]
    res = analyze_fusion_interference(stabilizer_matrix, qudit_dim=2, shifts=shifts)
    assert res["annihilator_dimension"] == 1
    assert res["dimension_drop"] is False

def test_analyze_fusion_interference_with_drop():
    """Verify that a shift along the lineon axis causes dimension drop to -1."""
    # 2D lineon variety along y (annihilator dim is 1)
    stabilizer_matrix = [
        ["1 - x", "0*y"]
    ]
    # Shift along x direction (dx=1, dy=0), should cause drop
    shifts = [[1, 0]]
    res = analyze_fusion_interference(stabilizer_matrix, qudit_dim=2, shifts=shifts)
    assert res["annihilator_dimension"] == 1
    assert res["dimension_drop"] is True

# ==============================================================================
# 4. Tests for query_vector_db
# ==============================================================================

def test_query_vector_db_init_and_query():
    """Verify DB initialization, seeding, and querying."""
    # Run init
    res_init = query_vector_db("init")
    assert res_init["status"] == "success"
    
    # Query standard models
    res_query = query_vector_db("query", {"query": "SELECT * FROM models"})
    assert res_query["status"] == "success"
    models = res_query["results"]
    assert len(models) == 5
    
    names = [m["name"] for m in models]
    assert "Toric Code" in names
    assert "X-Cube Model" in names
    assert "WCF Code" in names
    assert "DCY Code" in names
    assert "Chamon's Cubic Code" in names
    
    # Verify WCF details
    wcf = next(m for m in models if m["name"] == "WCF Code")
    assert wcf["qudit_dim"] == 12
    assert wcf["gsd_val"] == 144
    assert wcf["l_x"] == 2
    assert wcf["l_y"] == 2
    assert wcf["is_topological"] == 1

def test_query_vector_db_sync():
    """Verify database sync behavior with a mock discovery file."""
    # Ensure database is initialized
    query_vector_db("init")
    
    # Create a mock discovery JSON file
    discoveries_dir = os.path.join(PROJECT_ROOT, "output", "discoveries")
    os.makedirs(discoveries_dir, exist_ok=True)
    mock_file = os.path.join(discoveries_dir, "test_discovery_model.json")
    
    mock_model = {
        "name": "Sync Test Model",
        "qudit_dim": 5,
        "spatial_dim": 3,
        "stabilizer_matrix": "[[\"1 - x\", \"1 - y\", \"1 - z\"]]",
        "d0": 2,
        "d1": 1,
        "is_topological": 0,
        "description": "Mock model for sync testing"
    }
    
    try:
        with open(mock_file, "w", encoding="utf-8") as f:
            json.dump(mock_model, f)
            
        # Run sync
        res_sync = query_vector_db("sync")
        assert res_sync["status"] == "success"
        
        # Query database to check if inserted
        res_query = query_vector_db("query", {"query": "SELECT * FROM models WHERE name = 'Sync Test Model'"})
        assert len(res_query["results"]) == 1
        synced = res_query["results"][0]
        assert synced["qudit_dim"] == 5
        assert synced["spatial_dim"] == 3
        assert synced["d0"] == 2
        assert synced["d1"] == 1
        assert synced["is_topological"] == 0
        
    finally:
        if os.path.exists(mock_file):
            os.remove(mock_file)
