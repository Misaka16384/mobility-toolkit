"""Regression tests for the Ruba--Yang charge-module definition."""

import re

import pytest

from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.translate import translate_stabilizers


M2_AVAILABLE = describe_m2_backend()["available"]


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def test_translation_exposes_barred_coker_presentation():
    translated = translate_stabilizers(
        [["x - 2", "0"]],
        qudit_dim=5,
        spatial_dim=1,
    )

    assert _compact(translated["matrix_definition"]) == "{{x-2},{0}}"
    assert _compact(translated["antipode_matrix_definition"]) == "{{t-2},{0}}"
    assert translated["stabilizer_validation"]["pauli_rank"] == 2
    assert translated["stabilizer_validation"]["qudits_per_cell"] == 1


def test_explicit_spatial_dim_builds_inactive_axes_into_ring():
    translated = translate_stabilizers(
        [["x - 1", "0"]],
        qudit_dim=5,
        spatial_dim=3,
    )

    assert translated["spatial_dim"] == 3
    assert translated["variables"] == ["x", "t", "y", "u", "z", "w"]
    assert "y*u - 1" in translated["ring_definition"]
    assert "z*w - 1" in translated["ring_definition"]


def test_legacy_input_in_dimension_above_three_returns_fully_unified_ring():
    translated = translate_stabilizers(
        [["x - 1", "0"]],
        qudit_dim=5,
        spatial_dim=4,
    )
    assert translated["variables"] == [
        "x1", "t1", "x2", "t2", "x3", "t3", "x4", "t4"
    ]
    assert "x1*t1 - 1" in translated["ring_definition"]
    assert translated["variable_pairs"][-1] == ["x4", "t4"]


def test_noncommuting_generators_are_rejected():
    with pytest.raises(ValueError, match=r"sigma\^dagger lambda sigma"):
        translate_stabilizers(
            [["1", "0"], ["0", "1"]],
            qudit_dim=5,
            spatial_dim=1,
        )


def test_odd_pauli_rank_is_rejected():
    with pytest.raises(ValueError, match="Pauli rank must be even"):
        translate_stabilizers([["x - 1"]], qudit_dim=5)


def test_valid_qudit_toric_presentation_is_accepted():
    # sigma columns are (x-1, y-1, 0, 0)^T and
    # (0, 0, 1-bar(y), bar(x)-1)^T.
    toric = [
        ["x - 1", "y - 1", "0", "0"],
        ["0", "0", "1 - y^-1", "x^-1 - 1"],
    ]
    translated = translate_stabilizers(toric, qudit_dim=5, spatial_dim=2)
    assert translated["stabilizer_validation"]["enabled"] is True
    assert translated["stabilizer_validation"]["generator_count"] == 2


def test_validation_can_be_explicitly_disabled_for_arbitrary_presentations():
    translated = translate_stabilizers(
        [["1", "0"], ["0", "1"]],
        qudit_dim=5,
        validate_stabilizer=False,
    )
    assert translated["stabilizer_validation"]["enabled"] is False


def test_composite_homology_fails_before_backend_even_with_bypass():
    translated = translate_stabilizers(
        [["x - 1", "0"]],
        qudit_dim=4,
        prime_bypass=True,
    )
    assert "ZZ/4" in translated["ring_definition"]

    with pytest.raises(NotImplementedError, match="uniform prime field"):
        compute_ext_krull(
            [["x - 1", "0"]],
            qudit_dim=4,
            prime_bypass=True,
        )


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_qbar_antipode_changes_f5_annihilator_direction():
    result = compute_ext_krull(
        [["x - 2", "0"]],
        qudit_dim=5,
        spatial_dim=1,
    )
    generators = {_compact(item) for item in result["annihilator_generators"]}

    # bar(x-2)=t-2, and the Laurent relation then gives x=3 in F_5.
    assert generators & {"t-2", "t+3", "3+t"}
    assert generators & {"x-3", "x+2", "2+x"}
    assert "x-2" not in generators
    assert result["definition"] == "Q^p = Ext_R^{p+1}(bar(P/L), R)"
    assert result["theorem_metadata"]["antipode_applied"] is True


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_spatial_dim_is_used_by_ext_ring_not_only_by_classifier():
    result = compute_ext_krull(
        [["x - 1", "0"]],
        qudit_dim=5,
        p_ext=0,
        spatial_dim=3,
    )
    assert result["krull_dimension"] == 2
    assert result["spatial_dim"] == 3
    bound = result["theorem_metadata"]["checks"]["prop25_universal_dimension_bound"]
    assert bound == {"statement": "dim(Q^p) <= D - 1 - p", "bound": 2, "passed": True}
    assert result["invariant_consistency"] is True


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_prop25_p_at_least_d_is_reported_and_zero():
    result = compute_ext_krull(
        [["x - 1", "0"]],
        qudit_dim=5,
        p_ext=1,
        spatial_dim=1,
    )
    assert result["krull_dimension"] == -1
    check = result["theorem_metadata"]["checks"]["prop25_vanishing"]
    assert check["applicable"] is True
    assert check["passed"] is True


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_saturated_prop25_bound_is_checked_only_when_declared():
    nonsaturated = [["x - 1", "0"]]
    with pytest.raises(RuntimeError, match="Proposition 25"):
        compute_ext_krull(
            nonsaturated,
            qudit_dim=5,
            p_ext=0,
            spatial_dim=1,
            saturated=True,
        )
