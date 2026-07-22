import itertools

import pytest

pytest.importorskip("flint")

from mobility_toolkit.boundary import (
    EnumerationBudget,
    PhaseLiftContext,
    analyze_finite_boundary_algebra,
    enumerate_e1_subgroups,
    enumerate_phase_lifts,
    paired_boundary_presentation,
    reduce_e1_orbits,
    support_window_from_sites,
)
from mobility_toolkit.core import Exactness, PauliModule, PresentedModule, SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FlintIntegerBackend,
    analyze_finite_stabilizer,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _qubit_algebra(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(analysis, ("q",), backend, "qubit-window")
    return analyze_finite_boundary_algebra(analysis, window, backend)


def _brute_subgroups_z2_squared():
    elements = tuple(itertools.product(range(2), repeat=2))

    def add(left, right):
        return tuple((a + b) % 2 for a, b in zip(left, right))

    subgroups = set()
    for mask in range(1 << len(elements)):
        subset = frozenset(
            element for index, element in enumerate(elements) if mask & (1 << index)
        )
        if (0, 0) not in subset:
            continue
        if all(add(left, right) in subset for left in subset for right in subset):
            subgroups.add(subset)
    isotropic = {
        subgroup
        for subgroup in subgroups
        if all((left[1] * right[0] - left[0] * right[1]) % 2 == 0
               for left in subgroup for right in subgroup)
    }
    return subgroups, isotropic


def test_e1_exhaustion_matches_independent_bruteforce_subgroups(backend):
    algebra = _qubit_algebra(backend)
    page = enumerate_e1_subgroups(algebra, backend)
    brute_subgroups, brute_isotropic = _brute_subgroups_z2_squared()
    assert page.checkpoint is None
    assert page.certificate.certified_complete
    assert page.certificate.exactness is Exactness.CERTIFIED_EXACT
    assert page.certificate.distinct_subgroups == len(brute_subgroups) == 5
    assert len(page.candidates) == len(brute_isotropic) == 4
    lagrangians = tuple(item for item in page.candidates if item.self_orthogonal_lagrangian)
    assert len(lagrangians) == 3
    assert all(item.maximal_isotropic and item.order == 2 for item in lagrangians)
    assert page.domain.finite_window_id == "qubit-window"
    assert page.domain.equivalence_relation == "raw_subgroups"


def test_e1_resume_and_result_paging_reaches_same_certificate(backend):
    algebra = _qubit_algebra(backend)
    budget = EnumerationBudget(max_work_units=2, max_results=1)
    checkpoint = None
    candidates = []
    iterations = 0
    while True:
        page = enumerate_e1_subgroups(algebra, backend, budget, checkpoint)
        candidates.extend(page.candidates)
        iterations += 1
        if page.checkpoint is None:
            break
        checkpoint = page.checkpoint
        assert page.certificate.exactness is Exactness.EXPERIMENTAL
        assert iterations < 100
    assert iterations > 1
    assert page.certificate.certified_complete
    assert len(candidates) == 4
    assert len({candidate.element_indices for candidate in candidates}) == 4


def test_phase_lift_completion_is_exhaustive_and_resumable(backend):
    algebra = _qubit_algebra(backend)
    subgroup_page = enumerate_e1_subgroups(algebra, backend)
    candidate = next(
        item for item in subgroup_page.candidates if item.self_orthogonal_lagrangian
    )
    context = PhaseLiftContext(algebra, ())
    budget = EnumerationBudget(max_phase_assignments=100, max_results=1)
    checkpoint = None
    completions = []
    while True:
        page = enumerate_phase_lifts(context, candidate, backend, budget, checkpoint)
        completions.extend(page.completions)
        if page.checkpoint is None:
            break
        checkpoint = page.checkpoint
    assert page.exactness is Exactness.CERTIFIED_EXACT
    assert page.assignments_total == algebra.analysis.module.phase_modulus
    assert len(completions) == 2
    assert {completion.phases for completion in completions} in (
        { (0,), (2,) },
        { (1,), (3,) },
    )
    assert all(completion.validation.valid for completion in completions)


def test_orbit_reduction_uses_explicit_automorphism(backend):
    algebra = _qubit_algebra(backend)
    page = enumerate_e1_subgroups(algebra, backend)
    lagrangians = tuple(
        candidate for candidate in page.candidates if candidate.self_orthogonal_lagrangian
    )
    paired = paired_boundary_presentation(algebra, backend)
    fourier = FiniteGroupHomomorphism.create(
        paired.group,
        paired.group,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        backend,
    )
    orbits = reduce_e1_orbits(lagrangians, (fourier,), algebra, backend)
    assert sorted(len(orbit.members) for orbit in orbits) == [1, 2]


def test_orbit_reduction_rejects_nonautomorphism(backend):
    algebra = _qubit_algebra(backend)
    page = enumerate_e1_subgroups(algebra, backend)
    lagrangians = tuple(
        candidate for candidate in page.candidates if candidate.self_orthogonal_lagrangian
    )
    paired = paired_boundary_presentation(algebra, backend)
    zero = FiniteGroupHomomorphism.create(
        paired.group,
        paired.group,
        SparseIntMatrix.zero(2, 2),
        backend,
    )
    with pytest.raises(ValueError, match="not an automorphism"):
        reduce_e1_orbits(lagrangians, (zero,), algebra, backend)


def _brute_subgroups_z4_squared():
    elements = tuple(itertools.product(range(4), repeat=2))
    zero = (0, 0)

    def add(left, right):
        return tuple((a + b) % 4 for a, b in zip(left, right))

    def generated(subgroup, element):
        cyclic = []
        current = zero
        while current not in cyclic:
            cyclic.append(current)
            current = add(current, element)
        return frozenset(add(left, right) for left in subgroup for right in cyclic)

    seen = {frozenset((zero,))}
    pending = [frozenset((zero,))]
    while pending:
        subgroup = pending.pop()
        for element in elements:
            enlarged = generated(subgroup, element)
            if enlarged not in seen:
                seen.add(enlarged)
                pending.append(enlarged)

    def pairing(left, right):
        return (left[1] * right[0] - left[0] * right[1]) % 4

    isotropic = {
        subgroup
        for subgroup in seen
        if all(pairing(left, right) == 0 for left in subgroup for right in subgroup)
    }
    lagrangian = {
        subgroup
        for subgroup in isotropic
        if subgroup
        == frozenset(
            element
            for element in elements
            if all(pairing(element, member) == 0 for member in subgroup)
        )
    }
    return seen, isotropic, lagrangian


def test_z4_e1_lagrangians_match_independent_composite_oracle(backend):
    module = PauliModule.from_dimensions((4,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(analysis, ("q",), backend, "z4-window")
    algebra = analyze_finite_boundary_algebra(analysis, window, backend)
    page = enumerate_e1_subgroups(algebra, backend)
    brute_subgroups, brute_isotropic, brute_lagrangians = _brute_subgroups_z4_squared()
    assert page.certificate.certified_complete
    assert page.certificate.distinct_subgroups == len(brute_subgroups) == 15
    assert len(page.candidates) == len(brute_isotropic) == 11
    assert sum(item.self_orthogonal_lagrangian for item in page.candidates) == len(brute_lagrangians) == 7


def test_checkpoint_is_bound_to_exact_search_domain(backend):
    algebra = _qubit_algebra(backend)
    partial = enumerate_e1_subgroups(
        algebra, backend, EnumerationBudget(max_work_units=1)
    )
    assert partial.checkpoint is not None

    other_module = PauliModule.from_dimensions((3,), ("q",))
    other_analysis = analyze_finite_stabilizer(other_module, (), backend)
    other_window = support_window_from_sites(other_analysis, ("q",), backend)
    other = analyze_finite_boundary_algebra(other_analysis, other_window, backend)
    with pytest.raises(ValueError, match="different paired algebra"):
        enumerate_e1_subgroups(other, backend, checkpoint=partial.checkpoint)


def test_element_memory_limit_returns_resumable_incomplete_certificate(backend):
    algebra = _qubit_algebra(backend)
    page = enumerate_e1_subgroups(
        algebra,
        backend,
        EnumerationBudget(max_elements=2),
    )
    assert page.checkpoint is not None
    assert not page.certificate.certified_complete
    assert page.certificate.exactness is Exactness.EXPERIMENTAL
    assert "max_elements=2" in page.certificate.verification[0]


def test_zero_pairing_degenerate_group_keeps_radical_distinct(backend):
    # This direct paired-presentation oracle checks the abstract group convention
    # used by E1: relation columns, not diagonal-coordinate assumptions.
    group = FiniteAbelianGroup.from_presentation(
        PresentedModule(1, SparseIntMatrix.diagonal((2,))), backend
    )
    assert group.invariant_factors == (2,)
