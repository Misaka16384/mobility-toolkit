from dataclasses import replace

import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    FiniteMetricGroup,
    fold_metric_groups,
    test_condensation as check_condensation,
    zd_toric_metric_model,
)
from mobility_toolkit.completion2d import (
    LocalBoundaryCompletionRequest,
    unsupported_automatic_anyon_extraction,
    verify_local_boundary_completion,
    zd_toric_cut_completion_benchmark,
)
from mobility_toolkit.core import Exactness, SparseIntMatrix, StabilizerCodeSpec
from mobility_toolkit.finite import FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


@pytest.mark.parametrize(
    "modulus,boundary_kind,anyon",
    (
        (2, "rough", (1, 0)),
        (2, "smooth", (0, 1)),
        (3, "rough", (1, 0)),
        (3, "smooth", (0, 1)),
        (4, "rough", (1, 0)),
        (4, "smooth", (0, 1)),
    ),
)
def test_zd_toric_cut_completion_closes_metric_to_local_pipeline(
    modulus, boundary_kind, anyon, backend
):
    benchmark = zd_toric_cut_completion_benchmark(
        modulus, boundary_kind, backend
    )
    result = verify_local_boundary_completion(benchmark.request, backend)
    assert result.exactness is Exactness.BOUNDED_EXACT
    assert result.certificate_level.value == "full"
    assert result.value.anyon_fusion_invariant_factors == (modulus, modulus)
    assert result.value.condensate_invariant_factors == (modulus,)
    assert result.value.codespace_dimension == 1
    assert result.value.boundary_logical_invariant_factors == ()
    certificate = result.value.certificate
    assert certificate.condensate.lagrangian
    assert certificate.phase_aware_completion_verified
    assert certificate.fusion_lift_verified
    assert certificate.local_support_verified
    assert certificate.termination_verified
    assert len(certificate.termination_witnesses) == 1
    termination = certificate.termination_witnesses[0]
    assert termination.anyon_representative == anyon
    assert termination.actual_excitation_term_ids == (
        termination.declared_remote_excitation_term_ids
    )
    assert termination.actual_excitation_term_ids[0].startswith("bulk:")
    assert all(
        witness.within_declared_domain
        for witness in certificate.locality_witnesses
    )
    assert "thermodynamic spectral gap" in result.theorem_scope


def test_completion_rejects_resealed_wrong_remote_syndrome(backend):
    benchmark = zd_toric_cut_completion_benchmark(2, "rough", backend)
    lift = benchmark.request.string_lifts[0]
    wrong = replace(lift, remote_excitation_term_ids=("bulk:not-a-real-term",))
    request = replace(benchmark.request, string_lifts=(wrong,))
    with pytest.raises(ValueError, match="must name bulk"):
        verify_local_boundary_completion(request, backend)


def test_completion_rejects_short_string_outside_declared_bound(backend):
    benchmark = zd_toric_cut_completion_benchmark(2, "smooth", backend)
    domain = replace(
        benchmark.request.locality_domain,
        max_completion_depth=0,
    )
    request = replace(benchmark.request, locality_domain=domain)
    with pytest.raises(ValueError, match="exceeds the declared locality"):
        verify_local_boundary_completion(request, backend)


def test_completion_rejects_scalar_incompatible_fusion_lift(backend):
    benchmark = zd_toric_cut_completion_benchmark(4, "rough", backend)
    lift = benchmark.request.string_lifts[0]
    phased = replace(lift, operator=lift.operator.with_phase(1))
    request = replace(benchmark.request, string_lifts=(phased,))
    with pytest.raises(ValueError, match="incompatible scalar phase"):
        verify_local_boundary_completion(request, backend)


def test_folded_z4_diagonal_is_lagrangian_with_reversed_second_form(backend):
    toric = zd_toric_metric_model(4, backend).metric
    folded = fold_metric_groups(toric, toric, backend)
    diagonal_generators = SparseIntMatrix(
        4,
        2,
        (
            (0, 0, 1),
            (1, 1, 1),
            (2, 0, 1),
            (3, 1, 1),
        ),
    )
    diagonal = folded.metric.group.subgroup(diagonal_generators, backend)
    certificate = check_condensation(folded.metric, diagonal, backend)
    assert folded.second_form_reversed
    assert certificate.lagrangian
    assert diagonal.invariant_factors(backend) == (4, 4)


def test_arbitrary_stabilizer_extraction_is_structured_unsupported(backend):
    benchmark = zd_toric_cut_completion_benchmark(2, "rough", backend)
    code = StabilizerCodeSpec(
        benchmark.request.pauli_module,
        tuple(item.operator for item in benchmark.request.bulk_terms),
    )
    result = unsupported_automatic_anyon_extraction(code)
    assert result.exactness is Exactness.UNSUPPORTED
    assert result.value is None
    assert "explicitly supplied" in result.theorem_scope
    assert result.diagnostics


def test_completion_request_rejects_non_lagrangian_semion_lift(backend):
    benchmark = zd_toric_cut_completion_benchmark(2, "rough", backend)
    group = benchmark.request.metric.group
    semion_metric = FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((2, 0), (0, 2))),
        (1, 3),
        backend,
    )
    request = LocalBoundaryCompletionRequest(
        metric=semion_metric,
        pauli_module=benchmark.request.pauli_module,
        bulk_terms=benchmark.request.bulk_terms,
        boundary_terms=benchmark.request.boundary_terms,
        string_lifts=benchmark.request.string_lifts,
        locality_domain=benchmark.request.locality_domain,
        source_scope="negative test: semion is not a bosonic Lagrangian generator",
    )
    with pytest.raises(ValueError, match="Lagrangian condensate"):
        verify_local_boundary_completion(request, backend)
