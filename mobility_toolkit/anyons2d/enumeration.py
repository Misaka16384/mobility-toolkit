"""Resource-bounded exhaustive enumeration of abstract anyon condensates.

The search domain is one explicitly supplied finite metric group.  Candidates
are raw subgroups, not automorphism or Morita-equivalence orbits, and every
emitted candidate is replay-checked by :mod:`mobility_toolkit.anyons2d.condensation`.
No local commuting-projector completion is constructed or implied.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Optional, Sequence, Tuple

from sympy import Matrix as SympyMatrix

from mobility_toolkit.anyons2d.condensation import (
    CondensationCertificate,
    test_condensation,
)
from mobility_toolkit.anyons2d.metric import FiniteMetricGroup
from mobility_toolkit.core import Exactness, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import FiniteIntegerBackend, FiniteSubgroup


ElementKey = Tuple[Tuple[int, int], ...]
IndexSubgroup = Tuple[int, ...]


def _positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _digits(index: int, base: int, length: int) -> Tuple[int, ...]:
    result = []
    for _ in range(length):
        result.append(index % base)
        index //= base
    return tuple(result)


def _matrix_from_columns(
    columns: Sequence[Sequence[int]], nrows: int
) -> SparseIntMatrix:
    materialized = tuple(tuple(column) for column in columns)
    return SparseIntMatrix(
        nrows,
        len(materialized),
        tuple(
            (row, column_index, value)
            for column_index, column in enumerate(materialized)
            for row, value in enumerate(column)
            if value
        ),
    )


@dataclass(frozen=True)
class CondensateEnumerationBudget:
    max_work_units: int = 100_000
    max_results: int = 1_000
    max_elements: int = 4_096
    max_subgroups: int = 100_000

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_budget.v1"

    def __post_init__(self) -> None:
        _positive(self.max_work_units, "max_work_units")
        _positive(self.max_results, "max_results")
        _positive(self.max_elements, "max_elements")
        _positive(self.max_subgroups, "max_subgroups")

    def to_canonical_dict(self) -> dict:
        return {
            "max_elements": self.max_elements,
            "max_results": self.max_results,
            "max_subgroups": self.max_subgroups,
            "max_work_units": self.max_work_units,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CondensateSearchDomain:
    metric_hash: str
    invariant_factors: Tuple[int, ...]
    group_order: int
    exponent: int
    presentation_rank: int
    phase_modulus: int
    equivalence_relation: str = "raw_subgroups"
    candidate_definition: str = (
        "all subgroups on which the quadratic refinement vanishes; Lagrangian "
        "means equality with the symmetric-monodromy orthogonal complement"
    )

    SCHEMA_ID = "mobility_toolkit.condensate_search_domain.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidate_definition": self.candidate_definition,
            "equivalence_relation": self.equivalence_relation,
            "exponent": self.exponent,
            "group_order": self.group_order,
            "invariant_factors": self.invariant_factors,
            "metric_hash": self.metric_hash,
            "phase_modulus": self.phase_modulus,
            "presentation_rank": self.presentation_rank,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CondensateEnumerationCheckpoint:
    metric_hash: str
    element_cursor: int = 0
    element_vectors: Tuple[Tuple[int, ...], ...] = ()
    pending_subgroups: Tuple[IndexSubgroup, ...] = ()
    seen_subgroups: Tuple[IndexSubgroup, ...] = ()
    active_subgroup: Optional[IndexSubgroup] = None
    active_element_cursor: int = 0
    subgroup_join_tests: int = 0
    subgroup_search_complete: bool = False
    output_cursor: int = 0

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_checkpoint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "active_element_cursor": self.active_element_cursor,
            "active_subgroup": self.active_subgroup,
            "element_cursor": self.element_cursor,
            "element_vectors": self.element_vectors,
            "metric_hash": self.metric_hash,
            "output_cursor": self.output_cursor,
            "pending_subgroups": self.pending_subgroups,
            "schema": self.SCHEMA_ID,
            "seen_subgroups": self.seen_subgroups,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
        }


@dataclass(frozen=True)
class CondensateCandidate:
    metric_hash: str
    element_indices: IndexSubgroup
    generator_indices: Tuple[int, ...]
    generator_vectors: Tuple[Tuple[int, ...], ...]
    subgroup: FiniteSubgroup
    invariant_factors: Tuple[int, ...]
    condensation: CondensationCertificate

    SCHEMA_ID = "mobility_toolkit.condensate_candidate.v1"

    @property
    def order(self) -> int:
        return len(self.element_indices)

    @property
    def lagrangian(self) -> bool:
        return self.condensation.lagrangian

    def to_canonical_dict(self) -> dict:
        return {
            "condensation": self.condensation,
            "element_indices": self.element_indices,
            "generator_indices": self.generator_indices,
            "generator_vectors": self.generator_vectors,
            "invariant_factors": self.invariant_factors,
            "lagrangian": self.lagrangian,
            "metric_hash": self.metric_hash,
            "order": self.order,
            "schema": self.SCHEMA_ID,
            "subgroup": self.subgroup,
        }


@dataclass(frozen=True)
class CondensateCompletenessCertificate:
    domain: CondensateSearchDomain
    elements_complete: bool
    subgroup_search_complete: bool
    output_complete: bool
    coordinate_tuples_scanned: int
    distinct_elements: int
    subgroup_join_tests: int
    distinct_subgroups: int
    bosonic_subgroups: int
    lagrangian_subgroups: int
    exactness: Exactness
    verification: Tuple[str, ...]
    limit_reason: Optional[str] = None
    theorem_scope: str = (
        "exhaustion of raw subgroups of the recorded abstract finite metric group; "
        "no quotient by automorphisms and no local Hamiltonian completion"
    )

    SCHEMA_ID = "mobility_toolkit.condensate_completeness_certificate.v1"

    @property
    def certified_complete(self) -> bool:
        return self.elements_complete and self.subgroup_search_complete and self.output_complete

    def to_canonical_dict(self) -> dict:
        return {
            "bosonic_subgroups": self.bosonic_subgroups,
            "certified_complete": self.certified_complete,
            "coordinate_tuples_scanned": self.coordinate_tuples_scanned,
            "distinct_elements": self.distinct_elements,
            "distinct_subgroups": self.distinct_subgroups,
            "domain": self.domain,
            "elements_complete": self.elements_complete,
            "exactness": self.exactness,
            "lagrangian_subgroups": self.lagrangian_subgroups,
            "limit_reason": self.limit_reason,
            "output_complete": self.output_complete,
            "schema": self.SCHEMA_ID,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
            "theorem_scope": self.theorem_scope,
            "verification": self.verification,
        }


@dataclass(frozen=True)
class CondensateEnumerationPage:
    domain: CondensateSearchDomain
    candidates: Tuple[CondensateCandidate, ...]
    checkpoint: Optional[CondensateEnumerationCheckpoint]
    certificate: CondensateCompletenessCertificate

    SCHEMA_ID = "mobility_toolkit.condensate_enumeration_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "certificate": self.certificate,
            "checkpoint": self.checkpoint,
            "domain": self.domain,
            "schema": self.SCHEMA_ID,
        }


class _ElementSpace:
    def __init__(self, metric: FiniteMetricGroup) -> None:
        rows = metric.group.relation_lattice_basis.to_rows()
        self.metric = metric
        self._inverse = SympyMatrix(rows).inv() if rows else SympyMatrix.zeros(0, 0)

    def key(self, vector: Sequence[int]) -> ElementKey:
        if not vector:
            return ()
        coordinates = self._inverse * SympyMatrix(tuple(vector))
        result = []
        for value in coordinates:
            rational = Fraction(int(value.p), int(value.q))
            reduced = rational - math.floor(rational)
            result.append((reduced.numerator, reduced.denominator))
        return tuple(result)


def _domain(metric: FiniteMetricGroup, backend: FiniteIntegerBackend) -> CondensateSearchDomain:
    order = metric.group.order(backend)
    exponent = metric.group.invariant_factors[-1] if metric.group.invariant_factors else 1
    return CondensateSearchDomain(
        canonical_hash("finite-metric-condensates-v1", metric),
        metric.group.invariant_factors,
        order,
        exponent,
        metric.group.presentation_rank,
        metric.phase_modulus,
    )


def _closure(
    subgroup: IndexSubgroup,
    element_index: int,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> IndexSubgroup:
    if element_index in subgroup:
        return subgroup
    rank = len(vectors[0]) if vectors else 0
    zero_key = space.key((0,) * rank)
    cyclic = [keys[zero_key]]
    current = vectors[element_index]
    while space.key(current) != zero_key:
        cyclic.append(keys[space.key(current)])
        current = tuple(
            current[index] + vectors[element_index][index] for index in range(rank)
        )
    members = set()
    for left_index in subgroup:
        for right_index in cyclic:
            total = tuple(
                vectors[left_index][index] + vectors[right_index][index]
                for index in range(rank)
            )
            members.add(keys[space.key(total)])
    return tuple(sorted(members))


def _canonical_generators(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> Tuple[int, ...]:
    rank = len(vectors[0]) if vectors else 0
    generated: IndexSubgroup = (keys[space.key((0,) * rank)],)
    result = []
    for index in subgroup:
        if index in generated:
            continue
        result.append(index)
        generated = _closure(generated, index, vectors, keys, space)
        if generated == subgroup:
            break
    return tuple(result)


def _verify_subgroup_family(
    subgroups: Sequence[IndexSubgroup],
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
    require_exhaustive: bool,
) -> None:
    family = set(subgroups)
    zero = keys[space.key((0,) * (len(vectors[0]) if vectors else 0))]
    if (zero,) not in family:
        raise ArithmeticError("subgroup search state omits the trivial subgroup")
    for subgroup in family:
        if tuple(sorted(set(subgroup))) != subgroup or zero not in subgroup:
            raise ArithmeticError("subgroup search state contains a malformed subgroup")
        if any(index < 0 or index >= len(vectors) for index in subgroup):
            raise ArithmeticError("subgroup search state has an invalid element index")
        member_set = set(subgroup)
        rank = len(vectors[0]) if vectors else 0
        for left in subgroup:
            for right in subgroup:
                total = tuple(
                    vectors[left][axis] + vectors[right][axis] for axis in range(rank)
                )
                if keys[space.key(total)] not in member_set:
                    raise ArithmeticError("subgroup search state contains a non-subgroup")
        if require_exhaustive:
            for index in range(len(vectors)):
                if _closure(subgroup, index, vectors, keys, space) not in family:
                    raise ArithmeticError("claimed subgroup exhaustion is incomplete")


def _candidate_records(
    subgroups: Sequence[IndexSubgroup],
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
    metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    metric_hash: str,
) -> Tuple[CondensateCandidate, ...]:
    records = []
    for member_indices in sorted(subgroups):
        generators = _canonical_generators(member_indices, vectors, keys, space)
        generator_vectors = tuple(vectors[index] for index in generators)
        subgroup = metric.group.subgroup(
            _matrix_from_columns(generator_vectors, metric.group.presentation_rank),
            backend,
        )
        condensation = test_condensation(metric, subgroup, backend)
        if condensation.bosonic:
            records.append(
                CondensateCandidate(
                    metric_hash,
                    member_indices,
                    generators,
                    generator_vectors,
                    subgroup,
                    subgroup.invariant_factors(backend),
                    condensation,
                )
            )
    return tuple(records)


def _validate_checkpoint(
    checkpoint: CondensateEnumerationCheckpoint,
    domain: CondensateSearchDomain,
) -> None:
    if checkpoint.metric_hash != domain.metric_hash:
        raise ValueError("condensate checkpoint belongs to a different metric group")
    scalar_fields = (
        checkpoint.element_cursor,
        checkpoint.active_element_cursor,
        checkpoint.subgroup_join_tests,
        checkpoint.output_cursor,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in scalar_fields):
        raise ValueError("condensate checkpoint has an invalid cursor")
    if any(len(vector) != domain.presentation_rank for vector in checkpoint.element_vectors):
        raise ValueError("condensate checkpoint has an invalid element vector")
    if checkpoint.active_element_cursor > len(checkpoint.element_vectors):
        raise ValueError("condensate checkpoint active cursor is out of range")
    if checkpoint.subgroup_search_complete and (
        checkpoint.pending_subgroups or checkpoint.active_subgroup is not None
    ):
        raise ValueError("completed condensate checkpoint still has pending work")
    if not checkpoint.subgroup_search_complete and checkpoint.output_cursor:
        raise ValueError("condensate checkpoint emitted output before search completion")
    if len(set(checkpoint.seen_subgroups)) != len(checkpoint.seen_subgroups):
        raise ValueError("condensate checkpoint repeats a seen subgroup")
    if len(set(checkpoint.pending_subgroups)) != len(checkpoint.pending_subgroups):
        raise ValueError("condensate checkpoint repeats pending work")
    seen = set(checkpoint.seen_subgroups)
    if any(subgroup not in seen for subgroup in checkpoint.pending_subgroups):
        raise ValueError("condensate checkpoint has unseen pending work")
    if checkpoint.active_subgroup is not None and checkpoint.active_subgroup not in seen:
        raise ValueError("condensate checkpoint has an unseen active subgroup")


def enumerate_condensates(
    metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    budget: CondensateEnumerationBudget = CondensateEnumerationBudget(),
    checkpoint: Optional[CondensateEnumerationCheckpoint] = None,
) -> CondensateEnumerationPage:
    """Return one page of every raw bosonic subgroup of ``metric``.

    Passing the returned checkpoint resumes the exact BFS.  A page is certified
    complete only after all finite-group elements, all raw subgroups, and all
    candidate output pages have been exhausted.
    """

    domain = _domain(metric, backend)
    if checkpoint is None:
        checkpoint = CondensateEnumerationCheckpoint(domain.metric_hash)
    _validate_checkpoint(checkpoint, domain)

    if domain.group_order > budget.max_elements:
        certificate = CondensateCompletenessCertificate(
            domain,
            False,
            False,
            False,
            checkpoint.element_cursor,
            len(checkpoint.element_vectors),
            checkpoint.subgroup_join_tests,
            len(checkpoint.seen_subgroups),
            0,
            0,
            Exactness.EXPERIMENTAL,
            (),
            f"group order exceeds max_elements={budget.max_elements}",
        )
        return CondensateEnumerationPage(domain, (), checkpoint, certificate)

    space = _ElementSpace(metric)
    element_vectors = list(checkpoint.element_vectors)
    known_keys = {space.key(vector) for vector in element_vectors}
    if len(known_keys) != len(element_vectors):
        raise ValueError("condensate checkpoint repeats a finite-group element")
    element_cursor = checkpoint.element_cursor
    coordinate_limit = domain.exponent ** domain.presentation_rank
    if element_cursor > coordinate_limit:
        raise ValueError("condensate checkpoint element cursor is out of range")
    work = 0
    while len(element_vectors) < domain.group_order and element_cursor < coordinate_limit:
        if work >= budget.max_work_units:
            break
        vector = _digits(element_cursor, domain.exponent, domain.presentation_rank)
        element_cursor += 1
        work += 1
        key = space.key(vector)
        if key not in known_keys:
            known_keys.add(key)
            element_vectors.append(vector)
    elements_complete = len(element_vectors) == domain.group_order
    if element_cursor == coordinate_limit and not elements_complete:
        raise ArithmeticError("finite-group element materialization contradicts its order")

    pending = list(checkpoint.pending_subgroups)
    seen = set(checkpoint.seen_subgroups)
    active = checkpoint.active_subgroup
    active_cursor = checkpoint.active_element_cursor
    join_tests = checkpoint.subgroup_join_tests
    subgroup_complete = checkpoint.subgroup_search_complete
    if elements_complete:
        keys = {space.key(vector): index for index, vector in enumerate(element_vectors)}
        if not seen:
            trivial = (keys[space.key((0,) * domain.presentation_rank)],)
            pending = [trivial]
            seen = {trivial}
        _verify_subgroup_family(tuple(seen), element_vectors, keys, space, False)
    else:
        keys = {}
        if seen or pending or active is not None:
            raise ValueError("checkpoint started subgroup traversal before elements completed")

    hit_subgroup_limit = False
    while elements_complete and not subgroup_complete and work < budget.max_work_units:
        if active is None:
            if not pending:
                subgroup_complete = True
                break
            active = pending.pop(0)
            active_cursor = 0
        while active_cursor < len(element_vectors) and work < budget.max_work_units:
            element_index = active_cursor
            active_cursor += 1
            work += 1
            join_tests += 1
            generated = _closure(active, element_index, element_vectors, keys, space)
            if generated not in seen:
                if len(seen) >= budget.max_subgroups:
                    active_cursor -= 1
                    hit_subgroup_limit = True
                    work = budget.max_work_units
                    break
                seen.add(generated)
                pending.append(generated)
        if active_cursor == len(element_vectors):
            active = None
            active_cursor = 0
    if elements_complete and active is None and not pending:
        subgroup_complete = True
    if subgroup_complete:
        _verify_subgroup_family(tuple(seen), element_vectors, keys, space, True)

    all_candidates: Tuple[CondensateCandidate, ...] = ()
    output_cursor = checkpoint.output_cursor
    page_candidates: Tuple[CondensateCandidate, ...] = ()
    output_complete = False
    if subgroup_complete:
        all_candidates = _candidate_records(
            tuple(seen),
            tuple(element_vectors),
            keys,
            space,
            metric,
            backend,
            domain.metric_hash,
        )
        if output_cursor > len(all_candidates):
            raise ValueError("condensate checkpoint output cursor is out of range")
        end = min(output_cursor + budget.max_results, len(all_candidates))
        page_candidates = all_candidates[output_cursor:end]
        output_cursor = end
        output_complete = output_cursor == len(all_candidates)

    complete = elements_complete and subgroup_complete and output_complete
    verification = []
    if elements_complete:
        verification.append("distinct quotient cosets equal the exact finite-group order")
    if subgroup_complete:
        verification.append(
            "the subgroup family contains the trivial subgroup and is closed under adjoining every group element"
        )
        verification.append("every candidate was replay-checked by its quadratic condensation certificate")
    if output_complete:
        verification.append("every raw bosonic subgroup record was emitted across the checkpoint sequence")
    limit_reason = None
    if not elements_complete and work >= budget.max_work_units:
        limit_reason = f"page reached max_work_units={budget.max_work_units}"
    elif hit_subgroup_limit:
        limit_reason = f"subgroup state reached max_subgroups={budget.max_subgroups}"
    elif not subgroup_complete and work >= budget.max_work_units:
        limit_reason = f"page reached max_work_units={budget.max_work_units}"
    elif subgroup_complete and not output_complete:
        limit_reason = f"page reached max_results={budget.max_results}"
    certificate = CondensateCompletenessCertificate(
        domain,
        elements_complete,
        subgroup_complete,
        output_complete,
        element_cursor,
        len(element_vectors),
        join_tests,
        len(seen),
        len(all_candidates) if subgroup_complete else 0,
        sum(candidate.lagrangian for candidate in all_candidates) if subgroup_complete else 0,
        Exactness.CERTIFIED_EXACT if complete else Exactness.EXPERIMENTAL,
        tuple(verification),
        limit_reason,
    )
    next_checkpoint = None
    if not complete:
        next_checkpoint = CondensateEnumerationCheckpoint(
            domain.metric_hash,
            element_cursor,
            tuple(element_vectors),
            tuple(pending),
            tuple(sorted(seen)),
            active,
            active_cursor,
            join_tests,
            subgroup_complete,
            output_cursor,
        )
    return CondensateEnumerationPage(
        domain, page_candidates, next_checkpoint, certificate
    )


__all__ = [
    "CondensateCandidate",
    "CondensateCompletenessCertificate",
    "CondensateEnumerationBudget",
    "CondensateEnumerationCheckpoint",
    "CondensateEnumerationPage",
    "CondensateSearchDomain",
    "enumerate_condensates",
]
