from dataclasses import replace

import pytest

from mobility_toolkit.boundary.enumeration import symbolic3d as symbolic
from mobility_toolkit.boundary.enumeration.symbolic3d import (
    Symbolic3DBudget,
    Symbolic3DDecision,
    Symbolic3DEnumeration,
    Symbolic3DEquivalence,
    Symbolic3DPhaseStatus,
    Symbolic3DSearchRequest,
    Symbolic3DSourceLock,
    enumerate_symbolic3d_candidates,
    toric3d_primary_symbolic_crosscheck,
    verify_symbolic3d_enumeration,
    xcube_symbolic_orientation_crosscheck,
)
from mobility_toolkit.boundary_halfspace.boundary_module import (
    TangentLaurentPolynomial,
    TangentLaurentTerm,
)
from mobility_toolkit.boundary_halfspace.geometry import PrimitiveNormal
from mobility_toolkit.boundary_halfspace.quasi_symplectic import (
    FreeBoundaryPairingPresentation,
)
from mobility_toolkit.boundary_halfspace.toric3d import (
    toric3d_z2_z_nonnegative_primary_benchmark,
)
from mobility_toolkit.core import Exactness


NORMAL = PrimitiveNormal.from_integer((0, 0, 1))


def _poly(modulus, terms=()):
    return TangentLaurentPolynomial(
        modulus,
        2,
        tuple(
            TangentLaurentTerm(coefficient, exponents)
            for coefficient, exponents in terms
        ),
    )


def _constant_symplectic(modulus):
    zero = _poly(modulus)
    one = _poly(modulus, ((1, (0, 0)),))
    minus_one = _poly(modulus, (((-1) % modulus, (0, 0)),))
    return FreeBoundaryPairingPresentation(
        coefficient_modulus=modulus,
        tangent_rank=2,
        pairing_matrix=((zero, one), (minus_one, zero)),
        generator_labels=("e", "m"),
    )


def _request(presentation, **kwargs):
    return Symbolic3DSearchRequest(
        presentation=presentation,
        boundary_normal=NORMAL,
        exponent_bounds=kwargs.pop("exponent_bounds", ((0, 0), (0, 0))),
        max_generators=kwargs.pop("max_generators", 2),
        **kwargs,
    )


def test_odd_prime_constant_symplectic_search_is_bounded_complete():
    result = enumerate_symbolic3d_candidates(_request(_constant_symplectic(3)))

    assert result.exactness is Exactness.BOUNDED_EXACT
    enumeration = result.value
    certificate = enumeration.certificate
    assert certificate.bounded_complete
    assert certificate.seed_presentations_scanned == 5
    assert certificate.isotropic_seed_presentations == 4
    assert len(enumeration.candidates) == 4
    assert verify_symbolic3d_enumeration(enumeration)
    assert all(
        candidate.phase_status
        is Symbolic3DPhaseStatus.CANONICAL_ODD_PRIME_LIFT
        and candidate.phase_lift_available_by_canonical_odd_prime_convention
        and not candidate.phase_assignment_machine_verified
        and candidate.phase_assignment_witness_status == "not_computed"
        and not candidate.thermodynamic_gapped_boundary_claimed
        for candidate in enumeration.candidates
    )
    assert all(
        entry.is_zero
        for candidate in enumeration.candidates
        for row in candidate.pairing_matrix
        for entry in row
    )


def test_even_prime_pairing_is_exact_but_phase_refinement_is_unsupported():
    result = enumerate_symbolic3d_candidates(_request(_constant_symplectic(2)))

    assert result.exactness is Exactness.BOUNDED_EXACT
    assert len(result.value.candidates) == 3
    assert all(
        candidate.phase_status
        is Symbolic3DPhaseStatus.EVEN_PRIME_REFINEMENT_REQUIRED
        and not candidate.phase_lift_available_by_canonical_odd_prime_convention
        and not candidate.phase_assignment_machine_verified
        for candidate in result.value.candidates
    )
    assert ("phase_assignment_machine_verified", False) in result.verification
    assert any("quadratic refinement" in diagnostic for diagnostic in result.diagnostics)


def test_common_translation_equivalence_is_an_explicit_exact_subset():
    zero = _poly(2)
    presentation = FreeBoundaryPairingPresentation(
        coefficient_modulus=2,
        tangent_rank=2,
        pairing_matrix=((zero,),),
        generator_labels=("a",),
    )
    raw = enumerate_symbolic3d_candidates(
        _request(
            presentation,
            exponent_bounds=((0, 1), (0, 0)),
            max_generators=1,
        )
    )
    translated = enumerate_symbolic3d_candidates(
        _request(
            presentation,
            exponent_bounds=((0, 1), (0, 0)),
            max_generators=1,
            equivalence=Symbolic3DEquivalence.TRANSLATION,
        )
    )

    assert raw.exactness is Exactness.BOUNDED_EXACT
    assert translated.exactness is Exactness.BOUNDED_EXACT
    assert len(raw.value.candidates) == 3
    assert len(translated.value.candidates) == 2
    assert translated.value.certificate.isotropic_seed_presentations == 3
    assert translated.value.certificate.equivalence_representatives == 2
    assert "common tangent monomial" in (
        translated.value.certificate.implemented_equivalence
    )


def test_budget_exhaustion_is_experimental_and_replayable():
    result = enumerate_symbolic3d_candidates(
        _request(_constant_symplectic(3)),
        Symbolic3DBudget(max_seed_presentations=2, max_output_candidates=10),
    )

    assert result.exactness is Exactness.EXPERIMENTAL
    assert not result.value.certificate.rref_seed_domain_complete
    assert not result.value.certificate.bounded_complete
    assert result.value.checkpoint is not None
    assert result.value.checkpoint.structurally_verified
    assert verify_symbolic3d_enumeration(result.value)


def test_resumed_pages_concatenate_to_the_one_shot_candidate_order():
    request = _request(_constant_symplectic(3))
    one_shot = enumerate_symbolic3d_candidates(request)
    budget = Symbolic3DBudget(
        max_seed_presentations=1,
        max_output_candidates=1,
    )
    checkpoint = None
    page_hashes = []
    pages = []
    while True:
        page = enumerate_symbolic3d_candidates(
            request,
            budget,
            checkpoint=checkpoint,
        )
        pages.append(page)
        page_hashes.extend(
            candidate.candidate_hash for candidate in page.value.candidates
        )
        checkpoint = page.value.checkpoint
        if checkpoint is None:
            break

    assert len(pages) > 1
    assert all(
        page.exactness is Exactness.EXPERIMENTAL for page in pages[:-1]
    )
    assert pages[-1].exactness is Exactness.BOUNDED_EXACT
    assert tuple(page_hashes) == tuple(
        candidate.candidate_hash
        for candidate in one_shot.value.candidates
    )
    assert (
        pages[-1].value.certificate.transcript
        == one_shot.value.certificate.transcript
    )
    assert (
        pages[-1].value.certificate.transcript_hash
        == one_shot.value.certificate.transcript_hash
    )
    assert (
        pages[-1].value.certificate.output_hashes
        == one_shot.value.certificate.output_hashes
    )
    assert all(verify_symbolic3d_enumeration(page.value) for page in pages)


def test_resealed_checkpoint_decision_tamper_is_rejected_semantically():
    request = _request(_constant_symplectic(3))
    first = enumerate_symbolic3d_candidates(
        request,
        Symbolic3DBudget(
            max_seed_presentations=1,
            max_output_candidates=1,
        ),
    )
    checkpoint = first.value.checkpoint
    assert checkpoint is not None
    tampered_entry = replace(
        checkpoint.transcript[0],
        decision=Symbolic3DDecision.NON_ISOTROPIC,
        equivalence_key="",
    )
    resealed = symbolic._seal_checkpoint(
        checkpoint.request_hash,
        (tampered_entry,),
        (),
        (),
    )
    assert resealed.structurally_verified

    with pytest.raises(ValueError, match="semantic replay"):
        enumerate_symbolic3d_candidates(
            request,
            Symbolic3DBudget(
                max_seed_presentations=1,
                max_output_candidates=1,
            ),
            checkpoint=resealed,
        )


def test_semantic_replay_rejects_a_resealed_decision_tamper():
    result = enumerate_symbolic3d_candidates(_request(_constant_symplectic(3)))
    enumeration = result.value
    transcript = list(enumeration.certificate.transcript)
    transcript[0] = replace(transcript[0], pairing_hash="0" * 64)
    bad_certificate = replace(
        enumeration.certificate,
        transcript=tuple(transcript),
        transcript_hash=symbolic._transcript_hash(transcript),
    )
    assert bad_certificate.structurally_verified
    bad_enumeration = Symbolic3DEnumeration(
        enumeration.request,
        enumeration.candidates,
        bad_certificate,
    )

    assert not verify_symbolic3d_enumeration(bad_enumeration)


def test_nonprime_and_non_three_dimensional_domains_are_rejected():
    zero4 = _poly(4)
    composite = FreeBoundaryPairingPresentation(
        coefficient_modulus=4,
        tangent_rank=2,
        pairing_matrix=((zero4,),),
    )
    with pytest.raises(NotImplementedError, match="prime coefficient field"):
        _request(composite, max_generators=1)

    with pytest.raises(ValueError, match="three-dimensional normal"):
        Symbolic3DSearchRequest(
            presentation=_constant_symplectic(3),
            boundary_normal=PrimitiveNormal.from_integer((0, 1)),
            exponent_bounds=((0, 0), (0, 0)),
            max_generators=1,
        )


def test_primary_only_source_lock_cannot_enter_the_e3_search():
    lock = Symbolic3DSourceLock(
        model_id="toric3d",
        boundary_normal=NORMAL,
        source_id="primary-benchmark",
        source_scope="projected primary only",
        source_verified=True,
        full_boundary_module_supplied=False,
    )
    with pytest.raises(ValueError, match="full boundary module"):
        _request(_constant_symplectic(2), source_lock=lock)


def test_toric3d_primary_pairing_has_expected_bounded_isotropic_sectors():
    benchmark = toric3d_z2_z_nonnegative_primary_benchmark().value
    presentation = FreeBoundaryPairingPresentation(
        coefficient_modulus=2,
        tangent_rank=2,
        pairing_matrix=benchmark.quasi_symplectic_pairing,
        generator_labels=benchmark.generator_labels,
        source_scope="source-locked toric3d projected primary crosscheck only",
    )
    result = enumerate_symbolic3d_candidates(_request(presentation))
    bases = {candidate.coefficient_basis for candidate in result.value.candidates}
    label_index = {
        label: index for index, label in enumerate(benchmark.generator_labels)
    }
    electric_seed = tuple(
        1 if index == label_index["e_X"] else 0 for index in range(3)
    )
    magnetic_seeds = tuple(
        tuple(
            1 if index == label_index[label] else 0 for index in range(3)
        )
        for label in ("e_Zx", "e_Zy")
    )
    magnetic_basis = symbolic._rref(magnetic_seeds, 2)

    # Constant coefficients in the source-frozen primary basis.  These checks
    # reproduce the two known isotropic sectors without calling them completed
    # boundary Hamiltonians.
    assert (electric_seed,) in bases
    assert magnetic_basis in bases
    assert all(
        candidate.local_completion_status == "unsupported"
        for candidate in result.value.candidates
    )

    preflight = toric3d_primary_symbolic_crosscheck()
    assert preflight.exactness is Exactness.UNSUPPORTED
    assert preflight.value.source_verified
    assert not preflight.value.free_full_boundary_module_available
    assert not preflight.value.symbolic_search_supported
    assert "primary" in preflight.value.reason


def test_xcube_orientation_crosschecks_preserve_directional_difference():
    axial = xcube_symbolic_orientation_crosscheck(
        PrimitiveNormal.from_integer((0, 0, 1))
    )
    diagonal = xcube_symbolic_orientation_crosscheck(
        PrimitiveNormal.from_integer((1, 1, 1))
    )
    unregistered = xcube_symbolic_orientation_crosscheck(
        PrimitiveNormal.from_integer((1, 0, 1))
    )

    assert axial.exactness is Exactness.UNSUPPORTED
    assert diagonal.exactness is Exactness.UNSUPPORTED
    assert axial.value.source_verified and diagonal.value.source_verified
    assert axial.value.orientation_behavior == "not_surjective"
    assert diagonal.value.orientation_behavior == "isomorphism"
    assert not axial.value.symbolic_search_supported
    assert not diagonal.value.symbolic_search_supported
    assert unregistered.value.orientation_behavior == "unregistered"
    assert not unregistered.value.source_verified
