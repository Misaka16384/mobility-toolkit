from collections import Counter

import pytest

pytest.importorskip("flint")

from mobility_toolkit.defects import (
    DEFAULT_FRACTON_CLASSIFICATION_SCOPE,
    PrimitiveRationalDirection,
    StratifiedTubeRecord,
    xcube_cheshire_candidates,
)
from mobility_toolkit.defects.cheshire_classification import EvidenceStatus
from mobility_toolkit.finite import FlintIntegerBackend


def test_xcube_support_search_is_58_per_axis_but_never_a_complete_classification():
    catalog = xcube_cheshire_candidates(axis="all")

    assert len(catalog.candidates) == 174
    assert Counter(item.axis for item in catalog.candidates) == {
        "x": 58,
        "y": 58,
        "z": 58,
    }
    assert catalog.support_search_complete
    assert not catalog.classification_complete
    assert {
        item.evidence_tier.value for item in catalog.candidates
    } == {"support_candidate"}
    assert all(item.missing_obligations for item in catalog.candidates)
    assert all(item.planon_dressing_retained for item in catalog.candidates)


def test_xcube_equivalence_counts_keep_the_default_choice_visible():
    summary = xcube_cheshire_candidates(axis="z").equivalence_summary

    assert summary.raw_fixed_axis_count == 58
    assert summary.orientation_reversal_orbit_count == 58
    assert summary.all_axes_raw_count == 174
    assert summary.cubic_symmetry_orbit_count == 41
    assert summary.planon_generated_support_count == 15
    assert summary.all_constituents_planon_mobile_support_count == 4
    assert summary.all_constituents_line_mobile_support_count == 34
    assert summary.mixed_constituent_mobility_support_count == 20
    assert summary.nonzero_intrinsic_lineon_projection_count == 43
    assert summary.algebraic_planon_quotient_nontrivial_count == 1
    assert summary.foliated_planon_dressing_quotient_count is None
    assert summary.foliated_quotient_status.value == "unsupported"
    assert "retained planon dressing" in summary.default_equivalence_relation


def test_conditional_cochain_counts_are_explicitly_not_species_counts():
    catalog = xcube_cheshire_candidates(axis="z")
    diagnostics = {
        item.count: item for item in catalog.conditional_diagnostics
    }

    assert set(diagnostics) == {134, 4590}
    assert all(
        item.evidence_status.value == "conditional"
        and "not an X-cube Cheshire species count"
        == item.forbidden_interpretation
        for item in diagnostics.values()
    )


def test_optional_finite_reference_upgrades_only_ell_z_to_static_candidate():
    catalog = xcube_cheshire_candidates(
        axis="z",
        include_finite_static_reference=True,
        finite_reference_line_length=1,
        backend=FlintIntegerBackend(),
    )
    counts = Counter(item.evidence_tier.value for item in catalog.candidates)

    assert counts == {"support_candidate": 57, "static_cheshire_candidate": 1}
    assert not catalog.classification_complete
    assert catalog.finite_static_reference is not None


def test_finite_reference_does_not_silently_upgrade_reverse_orientation():
    with pytest.raises(ValueError, match=r"source-locked to the \+z orientation"):
        xcube_cheshire_candidates(
            axis="z",
            orientation="-",
            include_finite_static_reference=True,
            finite_reference_line_length=1,
            backend=FlintIntegerBackend(),
        )


def test_general_fracton_geometry_ir_accepts_arbitrary_primitive_direction():
    direction = PrimitiveRationalDirection((1, -2, 3))
    tube = StratifiedTubeRecord(
        tube_id="slanted-line",
        direction=direction,
        bulk_cell_ids=("c0", "c1"),
        boundary_strata_cell_ids=(("skin", ("f0", "f1")),),
        endpoint_ids=("left", "right"),
        junction_ids=("j0",),
        geometry_evidence_status=EvidenceStatus.BOUNDED_EXACT,
        missing_physical_obligations=(
            "supply mobility-enriched multiplication and junction data",
        ),
    )

    assert direction.reversed.components == (-1, 2, -3)
    assert tube.direction == direction
    assert DEFAULT_FRACTON_CLASSIFICATION_SCOPE.finite_depth_equivalence
    assert DEFAULT_FRACTON_CLASSIFICATION_SCOPE.retain_planon_dressing
    assert not DEFAULT_FRACTON_CLASSIFICATION_SCOPE.foliated_equivalence


def test_general_fracton_geometry_ir_rejects_nonprimitive_direction():
    with pytest.raises(ValueError, match="primitive"):
        PrimitiveRationalDirection((2, 0, 4))
