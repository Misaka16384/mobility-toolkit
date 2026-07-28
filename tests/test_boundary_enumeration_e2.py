from dataclasses import replace

import pytest

pytest.importorskip("flint")

import mobility_toolkit.boundary.enumeration.bounded_periodic as e2_module
from mobility_toolkit.boundary import (
    E2TangentAction,
    E2SiteCoordinate,
    E2Termination,
    EnumerationBudget,
    analyze_finite_boundary_algebra,
    bind_bounded_periodic_algebra,
    bounded_periodic_search_extent,
    enumerate_e2_bounded_periodic,
    enumerate_e1_subgroups,
    paired_boundary_presentation,
    support_window_from_sites,
)
from mobility_toolkit.boundary_halfspace import (
    AncillaBound,
    BoundedPeriodicSearchDomain,
    GeneratorSupportBound,
    OrientedHalfSpace,
    PrimitiveNormal,
)
from mobility_toolkit.core import Exactness, PauliModule, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import (
    FiniteGroupHomomorphism,
    FlintIntegerBackend,
    analyze_finite_stabilizer,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _domain(
    *,
    period=1,
    ancilla_sites=0,
    candidate_families=("translation_compatible_submodules",),
    coefficient_domain="finite_fga:uniform_z2",
    max_sites_per_term=2,
    tangent_radius=1,
):
    allowed_orders = (2,) if ancilla_sites else ()
    return BoundedPeriodicSearchDomain(
        half_space=OrientedHalfSpace(PrimitiveNormal((0, 1))),
        unit_cell_period=(period,),
        support_bound=GeneratorSupportBound(
            tangent_radii=(tangent_radius,),
            max_inward_depth=0,
            max_sites_per_term=max_sites_per_term,
        ),
        completion_depth=0,
        ancilla_bound=AncillaBound(
            max_sites_per_unit_cell=ancilla_sites,
            allowed_local_orders=allowed_orders,
        ),
        coefficient_domain=coefficient_domain,
        candidate_families=candidate_families,
    )


def _algebra_for_domain(domain, backend, dimensions=(2, 2)):
    site_ids = tuple(chr(ord("a") + index) for index in range(len(dimensions)))
    module = PauliModule.from_dimensions(dimensions, site_ids)
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(
        analysis,
        site_ids,
        backend,
        "bounded-periodic-window",
        bounded_periodic_search_extent(domain),
    )
    return analyze_finite_boundary_algebra(analysis, window, backend)


def _swap_qubits_action(algebra, backend):
    paired = paired_boundary_presentation(algebra, backend)
    swap = SparseIntMatrix.from_rows(
        (
            (0, 0, 1, 0),
            (0, 0, 0, 1),
            (1, 0, 0, 0),
            (0, 1, 0, 0),
        )
    )
    return E2TangentAction(
        "tangent-step",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, swap, backend
        ),
    )


def _identity_action(algebra, backend):
    paired = paired_boundary_presentation(algebra, backend)
    identity = SparseIntMatrix.identity(paired.group.presentation_rank)
    return E2TangentAction(
        "tangent-step",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, identity, backend
        ),
    )


def _site_coordinates(algebra):
    return tuple(
        E2SiteCoordinate(site_id, (index,), 0)
        for index, site_id in enumerate(algebra.window.site_ids)
    )


def _span_mod_prime(generators, prime):
    values = {tuple(0 for _ in generators[0])} if generators else {()}
    if not generators:
        return values
    values = {tuple(0 for _ in generators[0])}
    for generator in generators:
        values = {
            tuple(
                (left[index] + coefficient * generator[index]) % prime
                for index in range(len(generator))
            )
            for left in values
            for coefficient in range(prime)
        }
    return values


def test_z2_toric_shadow_has_electric_and_magnetic_periodic_lagrangians(backend):
    """The two sites are adjacent tangent translates of one toric edge species."""

    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    action = _swap_qubits_action(algebra, backend)
    page = enumerate_e2_bounded_periodic(
        algebra, domain, (action,), backend, _site_coordinates(algebra)
    )

    assert page.checkpoint is None
    assert page.certificate.termination is E2Termination.EXHAUSTED
    assert page.certificate.exactness is Exactness.BOUNDED_EXACT
    assert page.certificate.bounded_complete
    assert page.certificate.e1_certificate is not None
    assert page.certificate.e1_certificate.certified_complete
    assert (
        page.certificate.processed_e1_candidates
        == page.certificate.e1_certificate.isotropic_subgroups
    )

    lagrangians = tuple(
        candidate
        for candidate in page.candidates
        if candidate.e1_candidate.self_orthogonal_lagrangian
    )
    spans = {
        frozenset(_span_mod_prime(candidate.e1_candidate.generator_vectors, 2))
        for candidate in lagrangians
    }
    electric = frozenset(
        ((0, 0, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (1, 0, 1, 0))
    )
    magnetic = frozenset(
        ((0, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1), (0, 1, 0, 1))
    )
    assert electric in spans
    assert magnetic in spans
    assert len(lagrangians) >= 2
    assert all(candidate.fundamental_period == (1,) for candidate in page.candidates)
    # E1 contains raw finite-window isotropic subgroups; E2 keeps only those
    # compatible with the declared tangent translation.
    assert (
        page.certificate.processed_e1_candidates
        > page.certificate.accepted_candidates
    )


def test_period_two_includes_smaller_fundamental_periods(backend):
    domain = _domain(period=2)
    algebra = _algebra_for_domain(domain, backend)
    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (_swap_qubits_action(algebra, backend),),
        backend,
        _site_coordinates(algebra),
    )
    assert page.certificate.bounded_complete
    assert {candidate.fundamental_period for candidate in page.candidates} <= {
        (1,),
        (2,),
    }
    assert (1,) in {
        candidate.fundamental_period for candidate in page.candidates
    }


def test_resource_limited_resume_matches_one_shot(backend):
    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    actions = (_swap_qubits_action(algebra, backend),)
    full = enumerate_e2_bounded_periodic(
        algebra, domain, actions, backend, _site_coordinates(algebra)
    )
    expected = tuple(
        canonical_hash("test-e2-output", candidate)
        for candidate in full.candidates
    )

    budget = EnumerationBudget(max_work_units=7, max_results=2)
    checkpoint = None
    resumed = []
    pages = 0
    while True:
        page = enumerate_e2_bounded_periodic(
            algebra,
            domain,
            actions,
            backend,
            _site_coordinates(algebra),
            budget,
            checkpoint,
        )
        assert page.certificate.page_work_units <= budget.max_work_units
        resumed.extend(page.candidates)
        pages += 1
        if page.checkpoint is None:
            break
        assert page.certificate.exactness is Exactness.EXPERIMENTAL
        checkpoint = page.checkpoint
        assert pages < 1_000

    assert pages > 1
    assert page.certificate.bounded_complete
    assert tuple(
        canonical_hash("test-e2-output", candidate)
        for candidate in resumed
    ) == expected
    assert page.certificate.total_work_units >= sum(
        1 for _ in resumed
    )


def test_checkpoint_and_input_tampering_are_rejected(backend):
    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    swap = _swap_qubits_action(algebra, backend)
    partial = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (swap,),
        backend,
        _site_coordinates(algebra),
        EnumerationBudget(max_work_units=1, max_results=1),
    )
    assert partial.checkpoint is not None
    forged = replace(
        partial.checkpoint,
        total_work_units=partial.checkpoint.total_work_units + 1,
    )
    with pytest.raises(ValueError, match="state hash"):
        enumerate_e2_bounded_periodic(
            algebra,
            domain,
            (swap,),
            backend,
            _site_coordinates(algebra),
            checkpoint=forged,
        )

    different_domain = _domain(period=2)
    different_algebra = _algebra_for_domain(different_domain, backend)
    with pytest.raises(ValueError, match="different search domain|different algebra"):
        enumerate_e2_bounded_periodic(
            different_algebra,
            different_domain,
            (_swap_qubits_action(different_algebra, backend),),
            backend,
            _site_coordinates(different_algebra),
            checkpoint=partial.checkpoint,
        )

    with pytest.raises(ValueError, match="different algebra realization"):
        enumerate_e2_bounded_periodic(
            algebra,
            domain,
            (_identity_action(algebra, backend),),
            backend,
            _site_coordinates(algebra),
            checkpoint=partial.checkpoint,
        )


def test_resealed_semantic_decision_tampering_is_rejected(backend):
    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    actions = (_swap_qubits_action(algebra, backend),)
    partial = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        actions,
        backend,
        _site_coordinates(algebra),
        EnumerationBudget(max_results=1),
    )
    assert partial.checkpoint is not None
    assert partial.checkpoint.candidate_transcript

    original = partial.checkpoint.candidate_transcript[0]
    forged_decision = replace(
        original,
        accepted=not original.accepted,
    )
    forged_transcript = (
        forged_decision,
    ) + partial.checkpoint.candidate_transcript[1:]
    forged_candidate_hash = e2_module._replay_candidate_transcript(
        partial.checkpoint.domain_hash,
        partial.checkpoint.realization_hash,
        forged_transcript,
    )
    forged_output_prefix = tuple(
        entry
        for entry in partial.checkpoint.accepted_output_prefix
        if entry[0]
        != canonical_hash(
            "e2-input-e1-candidate-v1", original.e1_candidate
        )
    )
    forged_output_hash = e2_module._replay_output(
        partial.checkpoint.domain_hash,
        partial.checkpoint.realization_hash,
        forged_output_prefix,
    )
    forged = e2_module._seal_checkpoint(replace(
        partial.checkpoint,
        candidate_transcript=forged_transcript,
        candidate_transcript_hash=forged_candidate_hash,
        accepted_output_prefix=forged_output_prefix,
        output_transcript_hash=forged_output_hash,
        checkpoint_hash="",
    ))
    with pytest.raises(ValueError, match="semantically invalid"):
        enumerate_e2_bounded_periodic(
            algebra,
            domain,
            actions,
            backend,
            _site_coordinates(algebra),
            checkpoint=forged,
        )


def test_resealed_pending_candidate_tampering_breaks_e1_output_replay(backend):
    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    actions = (_swap_qubits_action(algebra, backend),)
    e1 = enumerate_e1_subgroups(algebra, backend)
    partial = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        actions,
        backend,
        _site_coordinates(algebra),
        EnumerationBudget(
            max_work_units=e1.certificate.page_work_units,
            max_results=1_000,
        ),
    )
    assert partial.checkpoint is not None
    assert len(partial.checkpoint.pending_e1_candidates) > 1
    pending = partial.checkpoint.pending_e1_candidates
    forged_pending = (pending[1],) + pending[1:]
    forged = e2_module._seal_checkpoint(replace(
        partial.checkpoint,
        pending_e1_candidates=forged_pending,
        checkpoint_hash="",
    ))
    with pytest.raises(ValueError, match="E1 output transcript"):
        enumerate_e2_bounded_periodic(
            algebra,
            domain,
            actions,
            backend,
            _site_coordinates(algebra),
            checkpoint=forged,
        )


def test_support_bound_rejects_a_subgroup_with_only_two_site_generators(backend):
    domain = _domain(max_sites_per_term=1)
    algebra = _algebra_for_domain(domain, backend)
    action = _swap_qubits_action(algebra, backend)
    e1 = enumerate_e1_subgroups(algebra, backend)
    two_site_x = next(
        candidate
        for candidate in e1.candidates
        if _span_mod_prime(candidate.generator_vectors, 2)
        == {(0, 0, 0, 0), (1, 0, 1, 0)}
    )

    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (action,),
        backend,
        _site_coordinates(algebra),
    )
    assert page.certificate.bounded_complete
    assert all(
        candidate.e1_candidate.element_indices != two_site_x.element_indices
        for candidate in page.candidates
    )
    assert page.certificate.realization.support_image_hashes
    assert page.certificate.realization.support_coverage_hash


def test_period_two_translation_orbit_of_one_local_seed_generates_candidate(
    backend,
):
    domain = _domain(
        period=2,
        max_sites_per_term=1,
        tangent_radius=0,
    )
    algebra = _algebra_for_domain(domain, backend)
    action = _swap_qubits_action(algebra, backend)
    electric_span = {
        (0, 0, 0, 0),
        (1, 0, 0, 0),
        (0, 0, 1, 0),
        (1, 0, 1, 0),
    }
    e1 = enumerate_e1_subgroups(algebra, backend)
    electric = next(
        candidate
        for candidate in e1.candidates
        if _span_mod_prime(candidate.generator_vectors, 2) == electric_span
    )

    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (action,),
        backend,
        _site_coordinates(algebra),
    )
    accepted = tuple(
        candidate.e1_candidate.element_indices
        for candidate in page.candidates
    )
    assert electric.element_indices in accepted
    assert tuple(
        sites
        for sites, _ in page.certificate.realization.support_image_hashes
    ) == ((), ("a",))
    assert len(
        page.certificate.realization.translated_support_image_hashes
    ) == 3


def test_genuine_fundamental_period_two_is_not_forced_to_be_t_invariant(
    backend,
):
    domain = _domain(
        period=2,
        coefficient_domain="finite_fga:uniform_z3",
        max_sites_per_term=1,
        tangent_radius=0,
    )
    algebra = _algebra_for_domain(domain, backend, dimensions=(3,))
    paired = paired_boundary_presentation(algebra, backend)
    fourier = SparseIntMatrix.from_rows(((0, -1), (1, 0)))
    action = E2TangentAction(
        "order-four-fourier",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, fourier, backend
        ),
    )
    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (action,),
        backend,
        _site_coordinates(algebra),
    )
    x_line = next(
        candidate
        for candidate in page.candidates
        if candidate.e1_candidate.self_orthogonal_lagrangian
        and _span_mod_prime(
            candidate.e1_candidate.generator_vectors, 3
        )
        == {(0, 0), (1, 0), (2, 0)}
    )
    assert x_line.fundamental_period == (2,)
    # T sends the X line to the distinct Z line, while T^2 acts by -1 and
    # therefore fixes the subgroup.  The microscopic action itself has order 4.
    assert fourier.to_rows() == ((0, -1), (1, 0))
    assert len(
        page.certificate.realization.translated_support_image_hashes
    ) == 2


def test_non_pairing_preserving_automorphism_is_rejected(backend):
    domain = _domain()
    algebra = _algebra_for_domain(domain, backend)
    paired = paired_boundary_presentation(algebra, backend)
    bad_permutation = SparseIntMatrix.from_rows(
        (
            (0, 0, 1, 0),
            (0, 1, 0, 0),
            (1, 0, 0, 0),
            (0, 0, 0, 1),
        )
    )
    action = E2TangentAction(
        "bad-step",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, bad_permutation, backend
        ),
    )
    with pytest.raises(ValueError, match="does not preserve the pairing"):
        bind_bounded_periodic_algebra(
            algebra,
            domain,
            (action,),
            backend,
            _site_coordinates(algebra),
        )


def test_ancillas_and_completion_family_are_not_overclaimed(backend):
    ancilla_domain = _domain(ancilla_sites=1)
    ancilla_algebra = _algebra_for_domain(ancilla_domain, backend)
    ancilla_page = enumerate_e2_bounded_periodic(
        ancilla_algebra,
        ancilla_domain,
        (_swap_qubits_action(ancilla_algebra, backend),),
        backend,
        _site_coordinates(ancilla_algebra),
    )
    assert ancilla_page.certificate.termination is E2Termination.UNSUPPORTED
    assert ancilla_page.certificate.exactness is Exactness.UNSUPPORTED
    assert not ancilla_page.candidates
    assert ancilla_page.checkpoint is None
    assert "ancilla enumeration is not implemented" in " ".join(
        ancilla_page.certificate.unsupported_reasons
    )

    completion_domain = _domain(
        candidate_families=(
            "translation_compatible_submodules",
            "local_hamiltonian_completions",
        )
    )
    completion_algebra = _algebra_for_domain(completion_domain, backend)
    completion_page = enumerate_e2_bounded_periodic(
        completion_algebra,
        completion_domain,
        (_swap_qubits_action(completion_algebra, backend),),
        backend,
        _site_coordinates(completion_algebra),
    )
    assert completion_page.certificate.exactness is Exactness.UNSUPPORTED
    assert "local_hamiltonian_completions" in " ".join(
        completion_page.certificate.unsupported_reasons
    )


def test_nonsymmetric_qutrit_action_uses_e1_generator_vectors_not_product_order(
    backend,
):
    domain = _domain(
        coefficient_domain="finite_fga:uniform_z3"
    )
    # The declared support permits two sites but a one-site realization is
    # still an exact precompiled algebra for this algebraic ordering oracle.
    algebra = _algebra_for_domain(domain, backend, dimensions=(3,))
    paired = paired_boundary_presentation(algebra, backend)
    shear = SparseIntMatrix.from_rows(((1, 1), (0, 1)))
    action = E2TangentAction(
        "qutrit-shear",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, shear, backend
        ),
    )
    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (action,),
        backend,
        _site_coordinates(algebra),
    )
    lagrangians = tuple(
        candidate
        for candidate in page.candidates
        if candidate.e1_candidate.self_orthogonal_lagrangian
    )
    assert len(lagrangians) == 1
    span = _span_mod_prime(
        lagrangians[0].e1_candidate.generator_vectors, 3
    )
    assert span == {(0, 0), (1, 0), (2, 0)}
