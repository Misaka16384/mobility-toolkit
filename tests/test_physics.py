"""Layer-3 interpreter: classify_mobility. Pure Python, no Macaulay2 backend."""
import pytest

from mobility_toolkit.physics import classify_mobility


def test_krull_zero_is_topological():
    r = classify_mobility(0, spatial_dim=2)
    assert r["order"] == "topological"
    assert r["is_topological"] and not r["is_fracton"]
    assert r["mobility_class"] == "fully-mobile (anyon)"
    assert r["generic_mobility_dimension"] == 2


@pytest.mark.parametrize("krull,d,klass,gen_dim", [
    (1, 3, "planon", 2),
    (2, 3, "lineon", 1),
    (3, 3, "fracton (immobile)", 0),
    (5, 3, "fracton (immobile)", 0),   # over-restricted clamps to 0
])
def test_positive_krull_is_fracton(krull, d, klass, gen_dim):
    r = classify_mobility(krull, spatial_dim=d)
    assert r["order"] == "fracton"
    assert r["is_fracton"] and not r["is_topological"]
    assert r["mobility_class"] == klass
    assert r["generic_mobility_dimension"] == gen_dim


def test_negative_krull_is_trivial():
    r = classify_mobility(-1)
    assert r["order"] == "trivial"
    assert not r["is_topological"] and not r["is_fracton"]
    assert r["generic_mobility_dimension"] is None


def test_validation():
    with pytest.raises(TypeError):
        classify_mobility(True)            # bool is not an int here
    with pytest.raises(TypeError):
        classify_mobility(1.5)
    with pytest.raises(ValueError):
        classify_mobility(0, spatial_dim=0)


def test_matches_validated_models():
    """Mirrors docs/VALIDATION.md: toric (Krull 0) mobile; X-Cube (2) & Chamon (1) fracton."""
    assert classify_mobility(0, 2)["is_topological"] is True     # toric code
    assert classify_mobility(2, 3)["is_fracton"] is True         # X-Cube
    assert classify_mobility(1, 3)["is_fracton"] is True         # Chamon
