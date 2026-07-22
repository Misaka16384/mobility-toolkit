"""Theorem-safe Layer-3 interpretation; pure Python, no M2 backend."""
import pytest

from mobility_toolkit.physics import classify_mobility


def test_q0_krull_zero_proves_full_mobility_but_not_topological_order():
    result = classify_mobility(0, spatial_dim=2)

    assert result["theorem_status"] == "proven"
    assert result["mobility_conclusion"] == "all_local_point_charges_fully_mobile"
    assert result["mobility_class"] == "fully-mobile-local-point-charges"
    assert result["topological_order"] is None
    assert result["order"] is None
    assert result["is_topological"] is None
    assert result["is_fracton"] is None
    assert result["generic_mobility_dimension"] is None
    assert result["evidence"]["reference"] == "Ruba--Yang, Corollary 37"


def test_topological_order_label_requires_explicit_extra_assumptions():
    incomplete = classify_mobility(
        0,
        spatial_dim=2,
        assumptions={"lagrangian": True, "saturated": True},
    )
    assert incomplete["topological_order"] is None

    qualified = classify_mobility(
        0,
        spatial_dim=2,
        assumptions={"lagrangian": True, "saturated": True, "no_ssb": True},
    )
    assert qualified["topological_order"] is True
    assert qualified["order"] == "topological"
    assert qualified["is_topological"] is True


@pytest.mark.parametrize("krull_dim", [1, 2, 3, 5])
def test_positive_q0_dimension_only_proves_not_all_charges_are_fully_mobile(krull_dim):
    result = classify_mobility(krull_dim, spatial_dim=3)

    assert result["theorem_status"] == "proven"
    assert result["mobility_conclusion"] == "not_all_local_point_charges_fully_mobile"
    assert result["mobility_class"] == "not-fully-mobile-as-a-whole"
    assert result["generic_mobility_dimension"] is None
    assert result["is_fracton"] is None
    assert result["topological_order"] is None
    assert all(
        label not in result["note"].lower()
        for label in ("is a planon", "is a lineon", "is a fracton")
    )


def test_zero_charge_module_does_not_make_the_code_trivial():
    result = classify_mobility(-1)

    assert result["charge_module_status"] == "zero"
    assert result["mobility_conclusion"] == "no_charge_in_this_degree"
    assert result["theorem_status"] == "not_applicable"
    assert result["order"] is None
    assert result["topological_order"] is None
    assert "whole stabilizer code is trivial" in result["evidence"]["statement"]


@pytest.mark.parametrize("krull_dim", [0, 1, 2])
def test_higher_charge_degree_mobility_is_reported_as_conjectural(krull_dim):
    result = classify_mobility(krull_dim, spatial_dim=3, charge_degree=1)

    assert result["charge_degree"] == 1
    assert result["theorem_status"] == "conjectural"
    assert result["mobility_conclusion"] == "undetermined_for_higher_charge_degree"
    assert result["mobility_class"] == "undetermined"
    assert result["generic_mobility_dimension"] is None


def test_p_ext_alias_and_conflict_detection():
    result = classify_mobility(0, p_ext=2)
    assert result["charge_degree"] == 2
    assert result["theorem_status"] == "conjectural"

    with pytest.raises(ValueError, match="disagree"):
        classify_mobility(0, charge_degree=1, p_ext=2)


def test_validation():
    with pytest.raises(TypeError):
        classify_mobility(True)
    with pytest.raises(TypeError):
        classify_mobility(1.5)
    with pytest.raises(ValueError):
        classify_mobility(0, spatial_dim=0)
    with pytest.raises(ValueError):
        classify_mobility(0, charge_degree=-1)
    with pytest.raises(TypeError):
        classify_mobility(0, assumptions=[])
    with pytest.raises(TypeError):
        classify_mobility(0, assumptions={"lagrangian": "yes"})
