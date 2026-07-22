"""Resource-bounded, resumable E1 enumeration for finite paired algebras.

E1 is exhaustive only for the finite paired group recorded in
``E1SearchDomain``.  It makes no claim about larger support windows or a
thermodynamic boundary.  The implementation intentionally favors transparent
certificates over asymptotic performance; later backends may replace the
subgroup traversal without changing these contracts.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, Iterable, Optional, Sequence, Tuple

from sympy import Matrix as SympyMatrix

from mobility_toolkit.boundary.algebra import FiniteBoundaryAlgebra
from mobility_toolkit.core import Exactness, PauliOperator, PresentedModule, SparseIntMatrix
from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FiniteGroupHomomorphism,
    FiniteIntegerBackend,
    PairedFiniteAbelianGroup,
    StabilizerValidation,
    validate_stabilizer_generators,
)


ElementKey = Tuple[Tuple[int, int], ...]
IndexSubgroup = Tuple[int, ...]


def _plain_positive(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _columns(matrix: SparseIntMatrix) -> Tuple[Tuple[int, ...], ...]:
    rows = matrix.to_rows()
    return tuple(
        tuple(rows[row][column] for row in range(matrix.nrows))
        for column in range(matrix.ncols)
    )


def _matrix_from_columns(columns: Sequence[Sequence[int]], nrows: int) -> SparseIntMatrix:
    columns = tuple(tuple(column) for column in columns)
    return SparseIntMatrix(
        nrows,
        len(columns),
        tuple(
            (row, column_index, value)
            for column_index, column in enumerate(columns)
            for row, value in enumerate(column)
            if value
        ),
    )


@dataclass(frozen=True)
class EnumerationBudget:
    max_work_units: int = 100_000
    max_results: int = 1_000
    max_phase_assignments: int = 100_000
    max_elements: int = 4_096
    max_subgroups: int = 100_000

    SCHEMA_ID = "mobility_toolkit.enumeration_budget.v1"

    def __post_init__(self) -> None:
        _plain_positive(self.max_work_units, "max_work_units")
        _plain_positive(self.max_results, "max_results")
        _plain_positive(self.max_phase_assignments, "max_phase_assignments")
        _plain_positive(self.max_elements, "max_elements")
        _plain_positive(self.max_subgroups, "max_subgroups")

    def to_canonical_dict(self) -> dict:
        return {
            "max_phase_assignments": self.max_phase_assignments,
            "max_elements": self.max_elements,
            "max_results": self.max_results,
            "max_subgroups": self.max_subgroups,
            "max_work_units": self.max_work_units,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class E1SearchDomain:
    algebra_input_hash: str
    invariant_factors: Tuple[int, ...]
    group_order: int
    exponent: int
    presentation_rank: int
    pairing_modulus: int
    equivalence_relation: str = "raw_subgroups"
    finite_window_id: str = ""
    finite_window_site_ids: Tuple[str, ...] = ()
    finite_window_search_extent: Tuple[Tuple[str, int], ...] = ()

    SCHEMA_ID = "mobility_toolkit.e1_search_domain.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "algebra_input_hash": self.algebra_input_hash,
            "equivalence_relation": self.equivalence_relation,
            "exponent": self.exponent,
            "finite_window_id": self.finite_window_id,
            "finite_window_search_extent": self.finite_window_search_extent,
            "finite_window_site_ids": self.finite_window_site_ids,
            "group_order": self.group_order,
            "invariant_factors": self.invariant_factors,
            "pairing_modulus": self.pairing_modulus,
            "presentation_rank": self.presentation_rank,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class E1CompletenessCertificate:
    domain: E1SearchDomain
    elements_complete: bool
    subgroup_search_complete: bool
    output_complete: bool
    coordinate_tuples_scanned: int
    distinct_elements: int
    subgroup_join_tests: int
    distinct_subgroups: int
    exactness: Exactness
    verification: Tuple[str, ...]
    theorem_scope: str = (
        "exhaustion of the recorded finite paired group only; no larger-window or "
        "thermodynamic completeness follows"
    )

    SCHEMA_ID = "mobility_toolkit.e1_completeness_certificate.v1"

    @property
    def certified_complete(self) -> bool:
        return (
            self.elements_complete
            and self.subgroup_search_complete
            and self.output_complete
        )

    def to_canonical_dict(self) -> dict:
        return {
            "certified_complete": self.certified_complete,
            "coordinate_tuples_scanned": self.coordinate_tuples_scanned,
            "distinct_elements": self.distinct_elements,
            "distinct_subgroups": self.distinct_subgroups,
            "domain": self.domain,
            "elements_complete": self.elements_complete,
            "exactness": self.exactness,
            "output_complete": self.output_complete,
            "schema": self.SCHEMA_ID,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
            "verification": self.verification,
            "theorem_scope": self.theorem_scope,
        }


@dataclass(frozen=True)
class E1EnumerationCheckpoint:
    algebra_input_hash: str
    element_cursor: int = 0
    element_vectors: Tuple[Tuple[int, ...], ...] = ()
    pending_subgroups: Tuple[IndexSubgroup, ...] = ()
    seen_subgroups: Tuple[IndexSubgroup, ...] = ()
    active_subgroup: Optional[IndexSubgroup] = None
    active_element_cursor: int = 0
    subgroup_join_tests: int = 0
    subgroup_search_complete: bool = False
    output_cursor: int = 0

    SCHEMA_ID = "mobility_toolkit.e1_enumeration_checkpoint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "active_element_cursor": self.active_element_cursor,
            "active_subgroup": self.active_subgroup,
            "algebra_input_hash": self.algebra_input_hash,
            "element_cursor": self.element_cursor,
            "element_vectors": self.element_vectors,
            "output_cursor": self.output_cursor,
            "pending_subgroups": self.pending_subgroups,
            "schema": self.SCHEMA_ID,
            "seen_subgroups": self.seen_subgroups,
            "subgroup_join_tests": self.subgroup_join_tests,
            "subgroup_search_complete": self.subgroup_search_complete,
        }


@dataclass(frozen=True)
class E1SubgroupCandidate:
    algebra_input_hash: str
    element_indices: IndexSubgroup
    generator_indices: Tuple[int, ...]
    generator_vectors: Tuple[Tuple[int, ...], ...]
    invariant_factors: Tuple[int, ...]
    order: int
    isotropic: bool
    maximal_isotropic: bool
    self_orthogonal_lagrangian: bool

    SCHEMA_ID = "mobility_toolkit.e1_subgroup_candidate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "element_indices": self.element_indices,
            "algebra_input_hash": self.algebra_input_hash,
            "generator_indices": self.generator_indices,
            "generator_vectors": self.generator_vectors,
            "invariant_factors": self.invariant_factors,
            "isotropic": self.isotropic,
            "maximal_isotropic": self.maximal_isotropic,
            "order": self.order,
            "schema": self.SCHEMA_ID,
            "self_orthogonal_lagrangian": self.self_orthogonal_lagrangian,
        }


@dataclass(frozen=True)
class E1EnumerationPage:
    domain: E1SearchDomain
    candidates: Tuple[E1SubgroupCandidate, ...]
    checkpoint: Optional[E1EnumerationCheckpoint]
    certificate: E1CompletenessCertificate

    SCHEMA_ID = "mobility_toolkit.e1_enumeration_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "candidates": self.candidates,
            "certificate": self.certificate,
            "checkpoint": self.checkpoint,
            "domain": self.domain,
            "schema": self.SCHEMA_ID,
        }


class _ElementSpace:
    def __init__(self, paired: PairedFiniteAbelianGroup) -> None:
        self.paired = paired
        rows = paired.group.relation_lattice_basis.to_rows()
        self._inverse = SympyMatrix(rows).inv() if rows else SympyMatrix.zeros(0, 0)
        self._pairing = paired.pairing_matrix.to_rows()

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

    def pairing(self, left: Sequence[int], right: Sequence[int]) -> int:
        return sum(
            left[row] * self._pairing[row][column] * right[column]
            for row in range(len(left))
            for column in range(len(right))
        ) % self.paired.modulus


def paired_boundary_presentation(
    algebra: FiniteBoundaryAlgebra, backend: FiniteIntegerBackend
) -> PairedFiniteAbelianGroup:
    quotient = algebra.paired_algebra
    rank = quotient.quotient.inclusion_matrix.nrows
    group = FiniteAbelianGroup.from_presentation(
        PresentedModule(rank, quotient.quotient.inclusion_matrix), backend
    )
    return PairedFiniteAbelianGroup.create(
        group, quotient.modulus, quotient.presentation_pairing_matrix
    )


def _domain(algebra: FiniteBoundaryAlgebra, paired: PairedFiniteAbelianGroup) -> E1SearchDomain:
    input_hash = canonical_hash(
        "e1-finite-paired-algebra-v1",
        {"paired": paired, "window": algebra.window},
    )
    order = 1
    for factor in paired.group.invariant_factors:
        order *= factor
    exponent = paired.group.invariant_factors[-1] if paired.group.invariant_factors else 1
    return E1SearchDomain(
        input_hash,
        paired.group.invariant_factors,
        order,
        exponent,
        paired.group.presentation_rank,
        paired.modulus,
        finite_window_id=algebra.window.window_id,
        finite_window_site_ids=algebra.window.site_ids,
        finite_window_search_extent=algebra.window.search_extent,
    )


def _digits(index: int, base: int, length: int) -> Tuple[int, ...]:
    values = []
    for _ in range(length):
        values.append(index % base)
        index //= base
    return tuple(values)


def _closure(
    subgroup: IndexSubgroup,
    element_index: int,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> IndexSubgroup:
    if element_index in subgroup:
        return subgroup
    zero = keys[space.key((0,) * len(vectors[0]))] if vectors else 0
    cyclic = [zero]
    current = vectors[element_index]
    while space.key(current) != space.key((0,) * len(current)):
        cyclic.append(keys[space.key(current)])
        current = tuple(
            current[index] + vectors[element_index][index]
            for index in range(len(current))
        )
    members = set()
    for left_index in subgroup:
        for right_index in cyclic:
            total = tuple(
                vectors[left_index][index] + vectors[right_index][index]
                for index in range(len(vectors[left_index]))
            )
            members.add(keys[space.key(total)])
    return tuple(sorted(members))


def _canonical_generators(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    keys: Dict[ElementKey, int],
    space: _ElementSpace,
) -> Tuple[int, ...]:
    zero = keys[space.key((0,) * (len(vectors[0]) if vectors else 0))]
    generated: IndexSubgroup = (zero,)
    generators = []
    for element in subgroup:
        if element in generated:
            continue
        generators.append(element)
        generated = _closure(generated, element, vectors, keys, space)
        if generated == subgroup:
            break
    return tuple(generators)


def _isotropic(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    space: _ElementSpace,
) -> bool:
    return all(
        space.pairing(vectors[left], vectors[right]) == 0
        for left in subgroup
        for right in subgroup
    )


def _orthogonal(
    subgroup: IndexSubgroup,
    vectors: Sequence[Tuple[int, ...]],
    space: _ElementSpace,
) -> IndexSubgroup:
    return tuple(
        index
        for index, vector in enumerate(vectors)
        if all(space.pairing(vector, vectors[item]) == 0 for item in subgroup)
    )


def _candidate_records(
    subgroups: Sequence[IndexSubgroup],
    vectors: Sequence[Tuple[int, ...]],
    paired: PairedFiniteAbelianGroup,
    backend: FiniteIntegerBackend,
    space: _ElementSpace,
    algebra_input_hash: str,
) -> Tuple[E1SubgroupCandidate, ...]:
    keys = {space.key(vector): index for index, vector in enumerate(vectors)}
    isotropic_groups = tuple(group for group in subgroups if _isotropic(group, vectors, space))
    isotropic_sets = tuple(frozenset(group) for group in isotropic_groups)
    records = []
    for subgroup, member_set in zip(isotropic_groups, isotropic_sets):
        generators = _canonical_generators(subgroup, vectors, keys, space)
        generator_vectors = tuple(vectors[index] for index in generators)
        matrix = _matrix_from_columns(generator_vectors, paired.group.presentation_rank)
        finite_subgroup = paired.group.subgroup(matrix, backend)
        maximal = not any(
            member_set < other_set for other_set in isotropic_sets
        )
        records.append(
            E1SubgroupCandidate(
                algebra_input_hash,
                subgroup,
                generators,
                generator_vectors,
                finite_subgroup.invariant_factors(backend),
                len(subgroup),
                True,
                maximal,
                subgroup == _orthogonal(subgroup, vectors, space),
            )
        )
    return tuple(sorted(records, key=lambda item: item.element_indices))


def enumerate_e1_subgroups(
    algebra: FiniteBoundaryAlgebra,
    backend: FiniteIntegerBackend,
    budget: EnumerationBudget = EnumerationBudget(),
    checkpoint: Optional[E1EnumerationCheckpoint] = None,
) -> E1EnumerationPage:
    """Return one resumable page of all isotropic E1 subgroups.

    A non-``None`` checkpoint must be passed back unchanged to resume.  A
    ``certified_complete`` certificate proves exhaustion of the recorded
    finite presentation, not of larger windows.
    """

    paired = paired_boundary_presentation(algebra, backend)
    domain = _domain(algebra, paired)
    if checkpoint is None:
        checkpoint = E1EnumerationCheckpoint(domain.algebra_input_hash)
    elif checkpoint.algebra_input_hash != domain.algebra_input_hash:
        raise ValueError("E1 checkpoint belongs to a different paired algebra")

    if domain.group_order > budget.max_elements:
        certificate = E1CompletenessCertificate(
            domain,
            False,
            False,
            False,
            0 if checkpoint is None else checkpoint.element_cursor,
            0 if checkpoint is None else len(checkpoint.element_vectors),
            0 if checkpoint is None else checkpoint.subgroup_join_tests,
            0 if checkpoint is None else len(checkpoint.seen_subgroups),
            Exactness.EXPERIMENTAL,
            (f"group order exceeds max_elements={budget.max_elements}",),
        )
        return E1EnumerationPage(domain, (), checkpoint, certificate)

    space = _ElementSpace(paired)
    element_vectors = list(checkpoint.element_vectors)
    known_keys = {space.key(vector) for vector in element_vectors}
    element_cursor = checkpoint.element_cursor
    work = 0
    coordinate_limit = domain.exponent ** domain.presentation_rank
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

    pending = list(checkpoint.pending_subgroups)
    seen = set(checkpoint.seen_subgroups)
    active = checkpoint.active_subgroup
    active_cursor = checkpoint.active_element_cursor
    join_tests = checkpoint.subgroup_join_tests
    if elements_complete and not seen:
        zero_index = next(
            index
            for index, vector in enumerate(element_vectors)
            if space.key(vector) == space.key((0,) * domain.presentation_rank)
        )
        trivial = (zero_index,)
        pending = [trivial]
        seen = {trivial}

    keys = {space.key(vector): index for index, vector in enumerate(element_vectors)}
    subgroup_complete = checkpoint.subgroup_search_complete
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
                    work = budget.max_work_units
                    break
                seen.add(generated)
                pending.append(generated)
        if active_cursor == len(element_vectors):
            active = None
            active_cursor = 0
    if elements_complete and active is None and not pending:
        subgroup_complete = True

    all_candidates: Tuple[E1SubgroupCandidate, ...] = ()
    output_cursor = checkpoint.output_cursor
    page_candidates: Tuple[E1SubgroupCandidate, ...] = ()
    output_complete = False
    if subgroup_complete:
        all_candidates = _candidate_records(
            tuple(sorted(seen)),
            tuple(element_vectors),
            paired,
            backend,
            space,
            domain.algebra_input_hash,
        )
        end = min(output_cursor + budget.max_results, len(all_candidates))
        page_candidates = all_candidates[output_cursor:end]
        output_cursor = end
        output_complete = output_cursor == len(all_candidates)

    exactness = (
        Exactness.CERTIFIED_EXACT
        if elements_complete and subgroup_complete and output_complete
        else Exactness.EXPERIMENTAL
    )
    verification = []
    if elements_complete:
        verification.append("distinct cosets equal the certified finite group order")
    if subgroup_complete:
        verification.append("BFS closure under adjoining every finite-group element exhausted")
    if output_complete:
        verification.append("every isotropic subgroup record was emitted")
    certificate = E1CompletenessCertificate(
        domain,
        elements_complete,
        subgroup_complete,
        output_complete,
        element_cursor,
        len(element_vectors),
        join_tests,
        len(seen),
        exactness,
        tuple(verification),
    )
    next_checkpoint = None
    if not certificate.certified_complete:
        next_checkpoint = E1EnumerationCheckpoint(
            domain.algebra_input_hash,
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
    return E1EnumerationPage(domain, page_candidates, next_checkpoint, certificate)


@dataclass(frozen=True)
class PhaseLiftContext:
    algebra: FiniteBoundaryAlgebra
    bulk_generators: Tuple[PauliOperator, ...]

    SCHEMA_ID = "mobility_toolkit.phase_lift_context.v1"

    def __post_init__(self) -> None:
        generators = tuple(self.bulk_generators)
        if any(operator.module != self.algebra.analysis.module for operator in generators):
            raise ValueError("phase-lift bulk generators belong to a different module")
        matrix = self.algebra.analysis.coordinates.generator_matrix(generators)
        if matrix != self.algebra.analysis.validation.generator_matrix:
            raise ValueError("phase-lift bulk generators do not match the analyzed presentation")
        object.__setattr__(self, "bulk_generators", generators)

    def to_canonical_dict(self) -> dict:
        return {
            "algebra_window": self.algebra.window.window_id,
            "bulk_generators": self.bulk_generators,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PhaseLiftCheckpoint:
    candidate_hash: str
    assignment_cursor: int = 0

    SCHEMA_ID = "mobility_toolkit.phase_lift_checkpoint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "assignment_cursor": self.assignment_cursor,
            "candidate_hash": self.candidate_hash,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PhaseLiftCompletion:
    phases: Tuple[int, ...]
    boundary_generators: Tuple[PauliOperator, ...]
    validation: StabilizerValidation

    SCHEMA_ID = "mobility_toolkit.phase_lift_completion.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_generators": self.boundary_generators,
            "phases": self.phases,
            "schema": self.SCHEMA_ID,
            "validation": self.validation,
        }


@dataclass(frozen=True)
class PhaseLiftPage:
    completions: Tuple[PhaseLiftCompletion, ...]
    checkpoint: Optional[PhaseLiftCheckpoint]
    assignments_total: int
    assignments_tested: int
    exactness: Exactness
    theorem_scope: str = (
        "all phase assignments for this candidate generator presentation and supplied "
        "finite bulk stabilizer list only"
    )

    SCHEMA_ID = "mobility_toolkit.phase_lift_page.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "assignments_tested": self.assignments_tested,
            "assignments_total": self.assignments_total,
            "checkpoint": self.checkpoint,
            "completions": self.completions,
            "exactness": self.exactness,
            "schema": self.SCHEMA_ID,
            "theorem_scope": self.theorem_scope,
        }


def enumerate_phase_lifts(
    context: PhaseLiftContext,
    candidate: E1SubgroupCandidate,
    backend: FiniteIntegerBackend,
    budget: EnumerationBudget = EnumerationBudget(),
    checkpoint: Optional[PhaseLiftCheckpoint] = None,
) -> PhaseLiftPage:
    """Enumerate compatible scalar phases for one projective completion."""

    if not candidate.isotropic:
        raise ValueError("phase lifts require an isotropic projective subgroup")
    paired = paired_boundary_presentation(context.algebra, backend)
    expected_hash = _domain(context.algebra, paired).algebra_input_hash
    if candidate.algebra_input_hash != expected_hash:
        raise ValueError("phase-lift candidate belongs to a different boundary algebra")
    candidate_hash = canonical_hash("e1-phase-lift-candidate-v1", candidate)
    cursor = 0 if checkpoint is None else checkpoint.assignment_cursor
    if checkpoint is not None and checkpoint.candidate_hash != candidate_hash:
        raise ValueError("phase-lift checkpoint belongs to a different candidate")
    algebra = context.algebra
    quotient_vectors = _matrix_from_columns(
        candidate.generator_vectors,
        algebra.local_centralizer.preimage_lattice_basis.ncols,
    )
    ambient_vectors = algebra.local_centralizer.preimage_lattice_basis.matmul(
        quotient_vectors
    )
    projective_lifts = tuple(
        algebra.analysis.coordinates.operator(vector)
        for vector in _columns(ambient_vectors)
    )
    modulus = algebra.analysis.module.phase_modulus
    total = modulus ** len(projective_lifts)
    end = min(total, cursor + budget.max_phase_assignments)
    completions = []
    processed_end = cursor
    for assignment_index in range(cursor, end):
        phases = _digits(assignment_index, modulus, len(projective_lifts))
        lifted = tuple(
            operator.with_phase(phase)
            for operator, phase in zip(projective_lifts, phases)
        )
        validation = validate_stabilizer_generators(
            algebra.analysis.module, context.bulk_generators + lifted, backend
        )
        if validation.valid:
            completions.append(PhaseLiftCompletion(phases, lifted, validation))
        processed_end = assignment_index + 1
        if len(completions) >= budget.max_results:
            break
    complete = processed_end == total
    next_checkpoint = None if complete else PhaseLiftCheckpoint(candidate_hash, processed_end)
    return PhaseLiftPage(
        tuple(completions),
        next_checkpoint,
        total,
        processed_end,
        Exactness.CERTIFIED_EXACT if complete else Exactness.EXPERIMENTAL,
    )


@dataclass(frozen=True)
class E1Orbit:
    representative: IndexSubgroup
    members: Tuple[IndexSubgroup, ...]

    SCHEMA_ID = "mobility_toolkit.e1_orbit.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "members": self.members,
            "representative": self.representative,
            "schema": self.SCHEMA_ID,
        }


def reduce_e1_orbits(
    candidates: Sequence[E1SubgroupCandidate],
    actions: Sequence[FiniteGroupHomomorphism],
    algebra: FiniteBoundaryAlgebra,
    backend: FiniteIntegerBackend,
) -> Tuple[E1Orbit, ...]:
    """Exactly reduce a complete candidate set by explicit automorphisms."""

    paired = paired_boundary_presentation(algebra, backend)
    space = _ElementSpace(paired)
    for action in actions:
        if action.source != paired.group or action.target != paired.group:
            raise ValueError("orbit action belongs to a different finite group")
        if action.kernel(backend).order(backend) != 1:
            raise ValueError("orbit action is not an automorphism")
        if action.image(backend).order(backend) != paired.group.order(backend):
            raise ValueError("orbit action is not an automorphism")
        pulled_back = (
            action.lift_matrix.transpose()
            .matmul(paired.pairing_matrix)
            .matmul(action.lift_matrix)
        )
        difference = SparseIntMatrix(
            paired.group.presentation_rank,
            paired.group.presentation_rank,
            tuple(pulled_back.entries) + tuple(paired.pairing_matrix.negate().entries),
        )
        if any(value % paired.modulus for _, _, value in difference.entries):
            raise ValueError("orbit action does not preserve the pairing")
    # Candidate vectors collectively contain every group element only when the
    # trivial/nonisotropic elements are absent, so materialize the finite group.
    exponent = paired.group.invariant_factors[-1] if paired.group.invariant_factors else 1
    vectors = []
    keys: Dict[ElementKey, int] = {}
    for values in itertools.product(range(exponent), repeat=paired.group.presentation_rank):
        key = space.key(values)
        if key not in keys:
            keys[key] = len(vectors)
            vectors.append(tuple(values))
        if len(vectors) == paired.group.order(backend):
            break
    candidate_map = {candidate.element_indices: candidate for candidate in candidates}
    remaining = set(candidate_map)
    orbits = []
    for seed in sorted(tuple(remaining)):
        if seed not in remaining:
            continue
        orbit = {seed}
        frontier = [seed]
        while frontier:
            subgroup = frontier.pop()
            for action in actions:
                mapped = tuple(
                    sorted(
                        keys[
                            space.key(
                                tuple(
                                    row[0]
                                    for row in action.lift_matrix.matmul(
                                        _matrix_from_columns((vectors[index],), len(vectors[index]))
                                    ).to_rows()
                                )
                            )
                        ]
                        for index in subgroup
                    )
                )
                if mapped not in candidate_map:
                    raise ValueError("automorphism did not preserve the candidate family")
                if mapped not in orbit:
                    orbit.add(mapped)
                    frontier.append(mapped)
        remaining.difference_update(orbit)
        members = tuple(sorted(orbit))
        orbits.append(E1Orbit(members[0], members))
    return tuple(orbits)


__all__ = [
    "E1CompletenessCertificate",
    "E1EnumerationCheckpoint",
    "E1EnumerationPage",
    "E1Orbit",
    "E1SearchDomain",
    "E1SubgroupCandidate",
    "EnumerationBudget",
    "PhaseLiftCheckpoint",
    "PhaseLiftCompletion",
    "PhaseLiftContext",
    "PhaseLiftPage",
    "enumerate_e1_subgroups",
    "enumerate_phase_lifts",
    "paired_boundary_presentation",
    "reduce_e1_orbits",
]
