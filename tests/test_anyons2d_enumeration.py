import itertools
from functools import lru_cache

import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    CondensateEnumerationBudget,
    FiniteMetricGroup,
    enumerate_condensates,
)
from mobility_toolkit.core import Exactness, SparseIntMatrix
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _metric(orders, modulus, braiding, spins, backend):
    group = FiniteAbelianGroup.from_coordinate_orders(orders, backend)
    return FiniteMetricGroup.create(
        group,
        modulus,
        SparseIntMatrix.from_rows(braiding),
        spins,
        backend,
    )


@lru_cache(maxsize=None)
def _brute_subgroups(orders):
    """Independent powerset oracle; intentionally does not use search internals."""

    elements = tuple(itertools.product(*(range(order) for order in orders)))
    zero = (0,) * len(orders)
    result = []
    for mask in range(1 << len(elements)):
        if not (mask & (1 << elements.index(zero))):
            continue
        subset = frozenset(
            element for index, element in enumerate(elements) if mask & (1 << index)
        )
        if all(
            tuple((left[i] + right[i]) % orders[i] for i in range(len(orders)))
            in subset
            for left in subset
            for right in subset
        ):
            result.append(subset)
    return tuple(result)


def _brute_condensates(orders, modulus, spin, braiding):
    all_elements = tuple(itertools.product(*(range(order) for order in orders)))
    bosonic = []
    lagrangian = []
    for subgroup in _brute_subgroups(orders):
        if not all(spin(element) % modulus == 0 for element in subgroup):
            continue
        # Check B independently even though polarization of q would imply it.
        if not all(
            braiding(left, right) % modulus == 0
            for left in subgroup
            for right in subgroup
        ):
            continue
        bosonic.append(subgroup)
        orthogonal = frozenset(
            element
            for element in all_elements
            if all(braiding(element, member) % modulus == 0 for member in subgroup)
        )
        if orthogonal == subgroup:
            lagrangian.append(subgroup)
    return tuple(bosonic), tuple(lagrangian)


def _collect(metric, backend, budget, checkpoint=None):
    candidates = []
    pages = 0
    while True:
        page = enumerate_condensates(metric, backend, budget, checkpoint)
        pages += 1
        candidates.extend(page.candidates)
        if page.checkpoint is None:
            return tuple(candidates), page.certificate, pages
        checkpoint = page.checkpoint
        assert not page.certificate.certified_complete
        assert page.certificate.exactness == Exactness.EXPERIMENTAL
        assert pages < 1_000


def _candidate_signature(candidate, orders, backend):
    return frozenset(
        element
        for element in itertools.product(*(range(order) for order in orders))
        if candidate.subgroup.contains(element, backend)
    )


@pytest.mark.parametrize(
    "name,orders,modulus,matrix,spins,spin,braiding,expected_lagrangians",
    (
        (
            "z2_toric",
            (2, 2),
            2,
            ((0, 1), (1, 0)),
            (0, 0),
            lambda x: x[0] * x[1],
            lambda x, y: x[0] * y[1] + x[1] * y[0],
            2,
        ),
        (
            "z4_toric",
            (4, 4),
            4,
            ((0, 1), (1, 0)),
            (0, 0),
            lambda x: x[0] * x[1],
            lambda x, y: x[0] * y[1] + x[1] * y[0],
            3,
        ),
        (
            "double_semion",
            (2, 2),
            4,
            ((2, 0), (0, 2)),
            (1, 3),
            lambda x: x[0] + 3 * x[1] + x[0] * (x[0] - 1) + x[1] * (x[1] - 1),
            lambda x, y: 2 * x[0] * y[0] + 2 * x[1] * y[1],
            1,
        ),
    ),
)
def test_exhaustive_raw_condensates_match_independent_powerset_oracle(
    name,
    orders,
    modulus,
    matrix,
    spins,
    spin,
    braiding,
    expected_lagrangians,
    backend,
):
    metric = _metric(orders, modulus, matrix, spins, backend)
    oracle_bosonic, oracle_lagrangian = _brute_condensates(
        orders, modulus, spin, braiding
    )
    candidates, certificate, _ = _collect(
        metric,
        backend,
        CondensateEnumerationBudget(
            max_work_units=100_000,
            max_results=1_000,
            max_elements=64,
            max_subgroups=1_000,
        ),
    )
    observed = {_candidate_signature(candidate, orders, backend) for candidate in candidates}
    observed_lagrangian = {
        _candidate_signature(candidate, orders, backend)
        for candidate in candidates
        if candidate.lagrangian
    }
    assert observed == set(oracle_bosonic), name
    assert observed_lagrangian == set(oracle_lagrangian), name
    assert len(observed_lagrangian) == expected_lagrangians
    assert certificate.bosonic_subgroups == len(oracle_bosonic)
    assert certificate.lagrangian_subgroups == expected_lagrangians
    assert certificate.certified_complete
    assert certificate.exactness == Exactness.CERTIFIED_EXACT
    assert certificate.domain.equivalence_relation == "raw_subgroups"
    assert "no quotient by automorphisms" in certificate.theorem_scope
    assert all(not candidate.condensation.local_completion_constructed for candidate in candidates)


def test_z4_raw_count_is_not_baked_in_as_boundary_classification(backend):
    # The independent oracle derives three raw Lagrangians: electric Z4,
    # magnetic Z4, and the Z2xZ2 subgroup of two-torsion elements.  This happens
    # to agree numerically with the three boundary classes discussed by Liang et
    # al.; this test asserts only raw subgroup equality, not equivalence orbits,
    # Morita classes, or existence of three locally completed Hamiltonians.
    bosonic, lagrangian = _brute_condensates(
        (4, 4),
        4,
        lambda x: x[0] * x[1],
        lambda x, y: x[0] * y[1] + x[1] * y[0],
    )
    assert len(lagrangian) == 3
    assert len(bosonic) >= len(lagrangian)


def test_pagination_and_resume_emit_each_raw_candidate_once(backend):
    metric = _metric(
        (4, 4), 4, ((0, 1), (1, 0)), (0, 0), backend
    )
    candidates, certificate, pages = _collect(
        metric,
        backend,
        CondensateEnumerationBudget(
            max_work_units=7,
            max_results=1,
            max_elements=64,
            max_subgroups=1_000,
        ),
    )
    signatures = tuple(_candidate_signature(item, (4, 4), backend) for item in candidates)
    assert pages > len(candidates)  # early pages advance element/subgroup cursors only
    assert len(signatures) == len(set(signatures))
    assert certificate.certified_complete
    assert certificate.output_complete


def test_resource_limits_never_claim_completeness_and_can_resume(backend):
    metric = _metric(
        (4, 4), 4, ((0, 1), (1, 0)), (0, 0), backend
    )
    blocked = enumerate_condensates(
        metric,
        backend,
        CondensateEnumerationBudget(max_elements=3),
    )
    assert blocked.candidates == ()
    assert blocked.checkpoint is not None
    assert not blocked.certificate.certified_complete
    assert blocked.certificate.exactness == Exactness.EXPERIMENTAL
    assert blocked.certificate.limit_reason == "group order exceeds max_elements=3"

    subgroup_limited = enumerate_condensates(
        metric,
        backend,
        CondensateEnumerationBudget(
            max_work_units=1_000,
            max_results=1_000,
            max_elements=64,
            max_subgroups=1,
        ),
    )
    assert subgroup_limited.checkpoint is not None
    assert not subgroup_limited.certificate.subgroup_search_complete
    assert subgroup_limited.certificate.exactness == Exactness.EXPERIMENTAL
    assert subgroup_limited.certificate.limit_reason == "subgroup state reached max_subgroups=1"

    resumed_candidates, resumed_certificate, _ = _collect(
        metric,
        backend,
        CondensateEnumerationBudget(
            max_work_units=100_000,
            max_results=1_000,
            max_elements=64,
            max_subgroups=1_000,
        ),
        subgroup_limited.checkpoint,
    )
    assert resumed_candidates
    assert resumed_certificate.certified_complete
