import os
import pytest
import sqlite3
import json
from mobility_toolkit.registry import ModelRegistry, DB_PATH
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.mobility import compute_true_mobility_dimension
from mobility_toolkit.search import search_koszul_models

@pytest.fixture(autouse=True)
def clean_db():
    # Make sure we start with a clean cache database
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass
    # Initialize registry
    registry = ModelRegistry()
    yield registry
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

def test_annihilator_caching(clean_db):
    registry = clean_db
    stabilizer_matrix = [["1 - x", "1 - y"]]
    qudit_dim = 2
    p_ext = 0

    # Ensure cache is initially empty
    assert registry.get_cached_annihilator(stabilizer_matrix, qudit_dim, p_ext) is None

    # Cache some mock results
    registry.cache_annihilator(
        stabilizer_matrix=stabilizer_matrix,
        qudit_dim=qudit_dim,
        p_ext=p_ext,
        krull_dimension=10,
        ext_modules=["mock_ext_module"],
        annihilator_generators=["gen1", "gen2"]
    )

    # Retrieve from cache
    cached = registry.get_cached_annihilator(stabilizer_matrix, qudit_dim, p_ext)
    assert cached is not None
    assert cached["krull_dimension"] == 10
    assert cached["ext_modules"] == ["mock_ext_module"]
    assert cached["annihilator_generators"] == ["gen1", "gen2"]

    # Verify compute_ext_krull respects the cache (fake value check)
    res = compute_ext_krull(stabilizer_matrix, qudit_dim, p_ext)
    assert res["krull_dimension"] == 10
    assert res["ext_modules"] == ["mock_ext_module"]
    assert res["annihilator_generators"] == ["gen1", "gen2"]

def test_properties_caching(clean_db):
    registry = clean_db
    generators = ["x - 1", "y - 1"]
    qudit_dim = 2

    # Ensure cache is initially empty
    assert registry.get_cached_properties(generators, qudit_dim) is None

    # Cache some mock properties
    registry.cache_properties(
        generators=generators,
        qudit_dim=qudit_dim,
        mobility_dimension=5,
        valuation_matrix=[[1, 2], [3, 4]],
        kernel_basis=[[0, 1]]
    )

    # Retrieve from cache
    cached = registry.get_cached_properties(generators, qudit_dim)
    assert cached is not None
    assert cached["mobility_dimension"] == 5
    assert cached["valuation_matrix"] == [[1, 2], [3, 4]]
    assert cached["kernel_basis"] == [[0, 1]]

    # Verify compute_true_mobility_dimension respects the cache (fake value check)
    res = compute_true_mobility_dimension(generators, qudit_dim)
    assert res["mobility_dimension"] == 5
    assert res["valuation_matrix"] == [[1, 2], [3, 4]]
    assert res["kernel_basis"] == [[0, 1]]
    assert res["variables"] == ["x", "y"]

def test_search_koszul_models(clean_db):
    # Try searching for a model with target_dim = 0
    res = search_koszul_models(qudit_dim=2, target_dim=0, max_trials=10)
    assert "status" in res
    if res["status"] == "success":
        assert res["krull_dimension"] == 0
        assert len(res["stabilizer_matrix"]) == 4
        assert len(res["stabilizer_matrix"][0]) == 6
    else:
        assert res["status"] == "failure"
        assert "message" in res

    # Try searching for an impossible target dimension to guarantee failure
    res_fail = search_koszul_models(qudit_dim=2, target_dim=999, max_trials=2)
    assert res_fail["status"] == "failure"
    assert res_fail["message"] == "No model found"
