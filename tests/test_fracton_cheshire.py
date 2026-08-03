from dataclasses import replace

import pytest

pytest.importorskip("flint")

from mobility_toolkit.boundary_halfspace import PrimitiveNormal
from mobility_toolkit.core import Exactness, canonical_json
from mobility_toolkit.defects.fracton_cheshire import (
    analyze_xcube_fracton_line_reference,
    xcube_axial_line_reference_request,
)
from mobility_toolkit.finite import FlintIntegerBackend


@pytest.fixture(scope="module")
def reference_result():
    request = xcube_axial_line_reference_request(1)
    return analyze_xcube_fracton_line_reference(request, FlintIntegerBackend())


def test_axial_reference_is_explicit_finite_and_experimental(reference_result):
    assert reference_result.exactness is Exactness.EXPERIMENTAL
    assert reference_result.certificate.verified
    assert ("thermodynamic_claim", False) in reference_result.verification
    assert reference_result.value.request.periodic_axes == (0, 1)
    assert reference_result.value.request.shape == (2, 2, 6)
    assert any(
        "no uniform thermodynamic spectral gap" in warning
        for warning in reference_result.warnings
    )


def test_local_lineon_completion_absorbs_nontrivial_bulk_probe(reference_result):
    value = reference_result.value
    assert value.probe_operator.phase == 0
    assert value.probe_operator.scalar_obstruction == 0
    assert len(value.bulk_syndrome) == 2
    assert value.defect_syndrome == ()
    assert value.certificate.removal_covers_bulk_syndrome
    assert value.certificate.modification_locality_verified
    assert value.certificate.removed_lineon_sector_only
    assert value.certificate.added_condensation_present
    assert value.certificate.added_condensation_commutes
    assert len(value.condensation_operators) == 1


def test_condensate_chain_has_no_accidental_local_zero_mode(reference_result):
    algebra = reference_result.value.local_algebra
    assert algebra.verified
    assert algebra.invariant_factors == ()
    assert algebra.pairing_rank == 0
    assert algebra.radical_invariant_factors == ()


def test_hidden_charge_is_global_independent_and_recovers_bulk_rank(
    reference_result,
):
    value = reference_result.value
    certificate = value.certificate

    assert certificate.rank_deficit_relative_to_bulk == 1
    assert certificate.hidden_charge_commutes
    assert certificate.hidden_charge_independent
    assert certificate.hidden_charge_restores_bulk_rank
    assert len(value.hidden_charge_operator.terms) == 6


def test_finite_translation_scan_records_orientation_sensitive_constraints(
    reference_result,
):
    constraints = reference_result.value.translation_constraints
    assert any(item.terminates_on_supplied_defect for item in constraints)
    assert any(
        item.bulk_excitation_nontrivial
        and not item.terminates_on_supplied_defect
        for item in constraints
    )
    assert reference_result.value.terminating_shifts


def test_scaling_sample_is_finite_rank_data_not_asymptotics(reference_result):
    sample = reference_result.value.scaling_sample
    assert sample.line_length_lattice_steps == 1
    assert sample.qubit_count == 72
    assert sample.bulk_codespace_dimension == 524288
    assert sample.defect_codespace_dimension == 1048576
    assert sample.removed_instance_count == 2
    assert sample.added_operator_count == 1


def test_slanted_orientation_is_structured_unsupported():
    request = replace(
        xcube_axial_line_reference_request(1),
        normal=PrimitiveNormal((1, 1, 1)),
    )
    result = analyze_xcube_fracton_line_reference(
        request, FlintIntegerBackend()
    )
    assert result.exactness is Exactness.UNSUPPORTED
    assert result.value is None
    assert ("requested_normal", (1, 1, 1)) in result.verification


def test_certificate_detects_probe_and_syndrome_tampering(reference_result):
    certificate = reference_result.certificate
    assert not replace(certificate, probe_hash="tampered").verified
    assert not replace(certificate, bulk_syndrome=()).verified
    assert not replace(certificate, hidden_charge_hash="tampered").verified


def test_serialization_keeps_nonclaim_scope(reference_result):
    payload = canonical_json(reference_result)
    assert '"exactness":"experimental"' in payload
    assert '"thermodynamic_claim",false' in payload
    assert "ordinary 2D anyon Lagrangian-subgroup criterion is not applied" in payload
    assert "q2 z-lineon is created/hopped by X(edge_x) along z" in payload
