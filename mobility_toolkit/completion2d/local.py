"""Certified finite local completions for explicitly lifted 2D Abelian anyons.

This module deliberately starts after anyon extraction.  The caller supplies
an exact finite metric group, a Lagrangian subgroup, phase-aware short Pauli
strings, and a finite patch Hamiltonian.  The verifier proves that these data
fit together inside the declared finite locality window.  It does not infer
anyon data from an arbitrary stabilizer presentation and it does not turn a
finite verification into a thermodynamic gap theorem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.anyons2d import (
    CondensationCertificate,
    FiniteMetricGroup,
    test_condensation,
)
from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    PauliModule,
    PauliOperator,
    SparseIntMatrix,
    StabilizerCodeSpec,
)
from mobility_toolkit.finite import (
    FiniteIntegerBackend,
    FiniteSubgroup,
    MembershipWitness,
    StabilizerValidation,
    analyze_finite_stabilizer,
)
from mobility_toolkit.finite.pauli import FinitePauliCoordinates


def _plain_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _column(values: Sequence[int]) -> SparseIntMatrix:
    values = tuple(_plain_int(value, "coordinate") for value in values)
    return SparseIntMatrix(
        len(values),
        1,
        tuple((row, 0, value) for row, value in enumerate(values) if value),
    )


def _matrix_from_columns(
    columns: Sequence[Sequence[int]], nrows: int
) -> SparseIntMatrix:
    columns = tuple(tuple(column) for column in columns)
    if any(len(column) != nrows for column in columns):
        raise ValueError("matrix column has the wrong rank")
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


def _matrix_columns(matrix: SparseIntMatrix) -> Tuple[Tuple[int, ...], ...]:
    rows = matrix.to_rows()
    return tuple(
        tuple(rows[row][column] for row in range(matrix.nrows))
        for column in range(matrix.ncols)
    )


def _operator_support(operator: PauliOperator) -> Tuple[str, ...]:
    return tuple(term.site_id for term in operator.terms)


def _diameter(
    support: Sequence[str], coordinate_map: dict
) -> int:
    support = tuple(support)
    if len(support) < 2:
        return 0
    return max(
        max(
            abs(coordinate_map[left][axis] - coordinate_map[right][axis])
            for axis in range(2)
        )
        for left in support
        for right in support
    )


@dataclass(frozen=True)
class NamedPauliTerm:
    """A Hamiltonian generator with a stable semantic identifier."""

    term_id: str
    operator: PauliOperator

    SCHEMA_ID = "mobility_toolkit.named_pauli_term_2d.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.term_id, str) or not self.term_id:
            raise ValueError("term_id must be a nonempty string")
        if not isinstance(self.operator, PauliOperator):
            raise TypeError("operator must be a PauliOperator")

    def to_canonical_dict(self) -> dict:
        return {
            "operator": self.operator,
            "schema": self.SCHEMA_ID,
            "term_id": self.term_id,
        }


@dataclass(frozen=True)
class FiniteBoundaryLocalityDomain:
    """The exact finite support/depth domain in which completion is certified."""

    window_label: str
    site_coordinates: Tuple[Tuple[str, Tuple[int, int]], ...]
    boundary_site_ids: Tuple[str, ...]
    site_depths: Tuple[Tuple[str, int], ...]
    max_completion_depth: int
    max_boundary_term_sites: int
    max_boundary_term_diameter: int
    max_short_string_sites: int

    SCHEMA_ID = "mobility_toolkit.finite_boundary_locality_domain_2d.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.window_label, str) or not self.window_label:
            raise ValueError("window_label must be a nonempty string")
        coordinates = tuple(
            (
                site_id,
                tuple(_plain_int(value, "site coordinate") for value in coordinate),
            )
            for site_id, coordinate in self.site_coordinates
        )
        if any(
            not isinstance(site_id, str)
            or not site_id
            or len(coordinate) != 2
            for site_id, coordinate in coordinates
        ):
            raise ValueError("site coordinates require unique nonempty IDs and 2D coordinates")
        if len({site_id for site_id, _ in coordinates}) != len(coordinates):
            raise ValueError("site coordinates repeat a site ID")
        boundary = tuple(sorted(set(self.boundary_site_ids)))
        if not boundary or not set(boundary) <= {site_id for site_id, _ in coordinates}:
            raise ValueError("boundary_site_ids must be a nonempty subset of known sites")
        depths = tuple(
            (site_id, _plain_int(depth, "site depth"))
            for site_id, depth in self.site_depths
        )
        if len({site_id for site_id, _ in depths}) != len(depths):
            raise ValueError("site depths repeat a site ID")
        if {site_id for site_id, _ in depths} != {site_id for site_id, _ in coordinates}:
            raise ValueError("site depths must cover exactly the coordinate sites")
        if any(depth < 0 for _, depth in depths):
            raise ValueError("site depths must be nonnegative")
        for field_name in (
            "max_completion_depth",
            "max_boundary_term_sites",
            "max_boundary_term_diameter",
            "max_short_string_sites",
        ):
            value = _plain_int(getattr(self, field_name), field_name)
            if value < 0 or (
                field_name in {"max_boundary_term_sites", "max_short_string_sites"}
                and value < 1
            ):
                raise ValueError(f"{field_name} has an invalid bound")
        object.__setattr__(self, "site_coordinates", tuple(sorted(coordinates)))
        object.__setattr__(self, "boundary_site_ids", boundary)
        object.__setattr__(self, "site_depths", tuple(sorted(depths)))

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_site_ids": self.boundary_site_ids,
            "max_boundary_term_diameter": self.max_boundary_term_diameter,
            "max_boundary_term_sites": self.max_boundary_term_sites,
            "max_completion_depth": self.max_completion_depth,
            "max_short_string_sites": self.max_short_string_sites,
            "schema": self.SCHEMA_ID,
            "site_coordinates": self.site_coordinates,
            "site_depths": self.site_depths,
            "window_label": self.window_label,
        }


@dataclass(frozen=True)
class CondensateStringLift:
    """One explicitly supplied short Pauli string ending at the boundary."""

    label: str
    anyon_representative: Tuple[int, ...]
    operator: PauliOperator
    remote_excitation_term_ids: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.condensate_string_lift_2d.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("string-lift label must be nonempty")
        representative = tuple(
            _plain_int(value, "anyon coordinate")
            for value in self.anyon_representative
        )
        if not isinstance(self.operator, PauliOperator):
            raise TypeError("string lift must be a PauliOperator")
        remote = tuple(sorted(set(self.remote_excitation_term_ids)))
        if not remote or any(not isinstance(term_id, str) or not term_id for term_id in remote):
            raise ValueError("a terminating short string needs named remote excitations")
        object.__setattr__(self, "anyon_representative", representative)
        object.__setattr__(self, "remote_excitation_term_ids", remote)

    def to_canonical_dict(self) -> dict:
        return {
            "anyon_representative": self.anyon_representative,
            "label": self.label,
            "operator": self.operator,
            "remote_excitation_term_ids": self.remote_excitation_term_ids,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class LocalBoundaryCompletionRequest:
    """Explicit finite-patch input for one proposed Abelian gapped boundary."""

    metric: FiniteMetricGroup
    pauli_module: PauliModule
    bulk_terms: Tuple[NamedPauliTerm, ...]
    boundary_terms: Tuple[NamedPauliTerm, ...]
    string_lifts: Tuple[CondensateStringLift, ...]
    locality_domain: FiniteBoundaryLocalityDomain
    source_scope: str
    assumptions: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.local_boundary_completion_request_2d.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.metric, FiniteMetricGroup):
            raise TypeError("metric must be a FiniteMetricGroup")
        if not isinstance(self.pauli_module, PauliModule):
            raise TypeError("pauli_module must be a PauliModule")
        if not isinstance(self.source_scope, str) or not self.source_scope:
            raise ValueError("source_scope must be a nonempty string")
        bulk = tuple(sorted(tuple(self.bulk_terms), key=lambda item: item.term_id))
        boundary = tuple(sorted(tuple(self.boundary_terms), key=lambda item: item.term_id))
        lifts = tuple(self.string_lifts)
        named = bulk + boundary
        if any(not isinstance(item, NamedPauliTerm) for item in named):
            raise TypeError("Hamiltonian terms must be NamedPauliTerm objects")
        if len({item.term_id for item in named}) != len(named):
            raise ValueError("Hamiltonian term IDs must be unique")
        if any(item.operator.module != self.pauli_module for item in named):
            raise ValueError("all Hamiltonian terms must belong to pauli_module")
        if not lifts or any(not isinstance(item, CondensateStringLift) for item in lifts):
            raise ValueError("at least one CondensateStringLift is required")
        if len({item.label for item in lifts}) != len(lifts):
            raise ValueError("string-lift labels must be unique")
        if any(item.operator.module != self.pauli_module for item in lifts):
            raise ValueError("all string lifts must belong to pauli_module")
        coordinate_sites = {site_id for site_id, _ in self.locality_domain.site_coordinates}
        if set(system.site_id for system in self.pauli_module.local_systems) != coordinate_sites:
            raise ValueError("locality coordinates must cover exactly the Pauli-module sites")
        object.__setattr__(self, "bulk_terms", bulk)
        object.__setattr__(self, "boundary_terms", boundary)
        object.__setattr__(self, "string_lifts", lifts)
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "boundary_terms": self.boundary_terms,
            "bulk_terms": self.bulk_terms,
            "locality_domain": self.locality_domain,
            "metric": self.metric,
            "pauli_module": self.pauli_module,
            "schema": self.SCHEMA_ID,
            "source_scope": self.source_scope,
            "string_lifts": self.string_lifts,
        }


@dataclass(frozen=True)
class LocalityWitness:
    object_id: str
    role: str
    support_site_ids: Tuple[str, ...]
    support_size: int
    diameter: int
    maximum_depth: int
    within_declared_domain: bool

    SCHEMA_ID = "mobility_toolkit.locality_witness_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "diameter": self.diameter,
            "maximum_depth": self.maximum_depth,
            "object_id": self.object_id,
            "role": self.role,
            "schema": self.SCHEMA_ID,
            "support_site_ids": self.support_site_ids,
            "support_size": self.support_size,
            "within_declared_domain": self.within_declared_domain,
        }


@dataclass(frozen=True)
class FusionLiftRelationWitness:
    relation_coefficients: Tuple[int, ...]
    relation_operator: PauliOperator
    stabilizer_membership: MembershipWitness
    stabilizer_generator_coefficients: Tuple[int, ...]
    phase_compatible: bool

    SCHEMA_ID = "mobility_toolkit.fusion_lift_relation_witness_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "phase_compatible": self.phase_compatible,
            "relation_coefficients": self.relation_coefficients,
            "relation_operator": self.relation_operator,
            "schema": self.SCHEMA_ID,
            "stabilizer_generator_coefficients": self.stabilizer_generator_coefficients,
            "stabilizer_membership": self.stabilizer_membership,
        }


@dataclass(frozen=True)
class StringTerminationWitness:
    label: str
    anyon_representative: Tuple[int, ...]
    actual_excitation_term_ids: Tuple[str, ...]
    declared_remote_excitation_term_ids: Tuple[str, ...]
    boundary_commutation_verified: bool
    exact_remote_syndrome_verified: bool

    SCHEMA_ID = "mobility_toolkit.string_termination_witness_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "actual_excitation_term_ids": self.actual_excitation_term_ids,
            "anyon_representative": self.anyon_representative,
            "boundary_commutation_verified": self.boundary_commutation_verified,
            "declared_remote_excitation_term_ids":
                self.declared_remote_excitation_term_ids,
            "exact_remote_syndrome_verified": self.exact_remote_syndrome_verified,
            "label": self.label,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class LocalBoundaryCompletionCertificate:
    stabilizer_validation: StabilizerValidation
    condensate: CondensationCertificate
    anyon_generator_matrix: SparseIntMatrix
    anyon_relation_lattice: SparseIntMatrix
    anyon_relation_witness: SparseIntMatrix
    fusion_lift_relations: Tuple[FusionLiftRelationWitness, ...]
    locality_witnesses: Tuple[LocalityWitness, ...]
    termination_witnesses: Tuple[StringTerminationWitness, ...]
    phase_aware_completion_verified: bool
    fusion_lift_verified: bool
    local_support_verified: bool
    termination_verified: bool

    SCHEMA_ID = "mobility_toolkit.local_boundary_completion_certificate_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anyon_generator_matrix": self.anyon_generator_matrix,
            "anyon_relation_lattice": self.anyon_relation_lattice,
            "anyon_relation_witness": self.anyon_relation_witness,
            "condensate": self.condensate,
            "fusion_lift_relations": self.fusion_lift_relations,
            "fusion_lift_verified": self.fusion_lift_verified,
            "local_support_verified": self.local_support_verified,
            "locality_witnesses": self.locality_witnesses,
            "phase_aware_completion_verified": self.phase_aware_completion_verified,
            "schema": self.SCHEMA_ID,
            "stabilizer_validation": self.stabilizer_validation,
            "termination_verified": self.termination_verified,
            "termination_witnesses": self.termination_witnesses,
        }


@dataclass(frozen=True)
class LocalBoundaryCompletion:
    completed_code: StabilizerCodeSpec
    anyon_fusion_invariant_factors: Tuple[int, ...]
    condensate_invariant_factors: Tuple[int, ...]
    codespace_dimension: int
    boundary_logical_invariant_factors: Tuple[int, ...]
    certificate: LocalBoundaryCompletionCertificate

    SCHEMA_ID = "mobility_toolkit.local_boundary_completion_2d.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anyon_fusion_invariant_factors": self.anyon_fusion_invariant_factors,
            "boundary_logical_invariant_factors": self.boundary_logical_invariant_factors,
            "certificate": self.certificate,
            "codespace_dimension": self.codespace_dimension,
            "completed_code": self.completed_code,
            "condensate_invariant_factors": self.condensate_invariant_factors,
            "schema": self.SCHEMA_ID,
        }


def _locality_witnesses(
    request: LocalBoundaryCompletionRequest,
) -> Tuple[LocalityWitness, ...]:
    domain = request.locality_domain
    coordinates = dict(domain.site_coordinates)
    depths = dict(domain.site_depths)
    boundary_sites = set(domain.boundary_site_ids)
    witnesses = []
    for item in request.boundary_terms:
        support = _operator_support(item.operator)
        diameter = _diameter(support, coordinates)
        maximum_depth = max((depths[site_id] for site_id in support), default=0)
        within = (
            set(support) <= boundary_sites
            and len(support) <= domain.max_boundary_term_sites
            and diameter <= domain.max_boundary_term_diameter
            and maximum_depth <= domain.max_completion_depth
        )
        witnesses.append(
            LocalityWitness(
                item.term_id,
                "boundary_hamiltonian_term",
                support,
                len(support),
                diameter,
                maximum_depth,
                within,
            )
        )
    for item in request.string_lifts:
        support = _operator_support(item.operator)
        diameter = _diameter(support, coordinates)
        maximum_depth = max((depths[site_id] for site_id in support), default=0)
        within = (
            len(support) <= domain.max_short_string_sites
            and maximum_depth <= domain.max_completion_depth
        )
        witnesses.append(
            LocalityWitness(
                item.label,
                "short_string_lift",
                support,
                len(support),
                diameter,
                maximum_depth,
                within,
            )
        )
    return tuple(witnesses)


def _anyon_relations(
    metric: FiniteMetricGroup,
    lifts: Sequence[CondensateStringLift],
    backend: FiniteIntegerBackend,
) -> Tuple[SparseIntMatrix, SparseIntMatrix, SparseIntMatrix]:
    generator_matrix = _matrix_from_columns(
        tuple(item.anyon_representative for item in lifts),
        metric.group.presentation_rank,
    )
    equations = SparseIntMatrix.hstack(
        generator_matrix, metric.group.relation_lattice_basis.negate()
    )
    kernel = backend.integer_kernel(equations).basis
    coefficient_rows = tuple(range(len(lifts)))
    relation_generators = kernel.select_rows(coefficient_rows)
    relation_lattice = backend.column_lattice_basis(relation_generators).basis
    if relation_lattice.ncols != len(lifts):
        raise ArithmeticError("anyon-generator relation lattice is not full rank")
    image = generator_matrix.matmul(relation_lattice)
    relation_witness = backend.solve_full_lattice(
        metric.group.relation_lattice_basis, image
    )
    if metric.group.relation_lattice_basis.matmul(relation_witness) != image:
        raise ArithmeticError("anyon fusion relation witness is invalid")
    return generator_matrix, relation_lattice, relation_witness


def _stabilizer_expression(
    operator: PauliOperator,
    generators: Sequence[PauliOperator],
    stabilizer: FiniteSubgroup,
    validation: StabilizerValidation,
    coordinates: FinitePauliCoordinates,
    backend: FiniteIntegerBackend,
) -> Tuple[MembershipWitness, Tuple[int, ...], bool]:
    vector = coordinates.vector(operator)
    membership = stabilizer.membership_witness(vector, backend)
    if membership is None:
        raise ValueError("short-string fusion relation is not a completed stabilizer")
    ambient_relations = SparseIntMatrix.diagonal(coordinates.coordinate_orders)
    input_matrix = SparseIntMatrix.hstack(
        validation.generator_matrix, ambient_relations
    )
    lattice_result = backend.column_lattice_basis(input_matrix)
    basis_coefficients = backend.solve_full_lattice(
        lattice_result.basis, _column(vector)
    )
    certificate = lattice_result.certificate
    basis_to_inputs = SparseIntMatrix(
        input_matrix.ncols,
        len(certificate.nonzero_rows),
        tuple(
            (column, basis_column, value)
            for basis_column, hnf_row in enumerate(certificate.nonzero_rows)
            for row, column, value in certificate.unimodular_transform.entries
            if row == hnf_row
        ),
    )
    if input_matrix.matmul(basis_to_inputs) != lattice_result.basis:
        raise ArithmeticError("column-lattice expression certificate is invalid")
    input_coefficients = basis_to_inputs.matmul(basis_coefficients)
    coefficients = tuple(
        input_coefficients.to_rows()[index][0] for index in range(len(generators))
    )
    stabilizer_product = operator.module.identity()
    for generator, coefficient in zip(generators, coefficients):
        stabilizer_product = stabilizer_product * generator.power(coefficient)
    phase_compatible = (operator * stabilizer_product.inverse()).is_identity
    return membership, coefficients, phase_compatible


def verify_local_boundary_completion(
    request: LocalBoundaryCompletionRequest,
    backend: FiniteIntegerBackend,
) -> ComputationResult:
    """Construct and exactly verify one explicit finite 2D boundary completion."""

    completed_named_terms = request.bulk_terms + request.boundary_terms
    generators = tuple(item.operator for item in completed_named_terms)
    analysis = analyze_finite_stabilizer(request.pauli_module, generators, backend)
    completed_code = StabilizerCodeSpec(
        request.pauli_module,
        generators,
        request.assumptions
        + (
            "explicit finite 2D patch",
            "explicit metric-group and short-string lifting data",
        ),
    )

    generator_matrix, relation_lattice, relation_witness = _anyon_relations(
        request.metric, request.string_lifts, backend
    )
    condensate_subgroup = request.metric.group.subgroup(generator_matrix, backend)
    condensation = test_condensation(request.metric, condensate_subgroup, backend)
    if not condensation.lagrangian:
        raise ValueError("a gapped-boundary completion requires a Lagrangian condensate")

    locality = _locality_witnesses(request)
    if not all(witness.within_declared_domain for witness in locality):
        raise ValueError("a completion term or short string exceeds the declared locality domain")

    fusion_relations = []
    for relation in _matrix_columns(relation_lattice):
        relation_operator = request.pauli_module.identity()
        for lift, coefficient in zip(request.string_lifts, relation):
            relation_operator = relation_operator * lift.operator.power(coefficient)
        membership, stabilizer_coefficients, phase_compatible = _stabilizer_expression(
            relation_operator,
            generators,
            analysis.stabilizer,
            analysis.validation,
            analysis.coordinates,
            backend,
        )
        if not phase_compatible:
            raise ValueError("short-string fusion relation has an incompatible scalar phase")
        fusion_relations.append(
            FusionLiftRelationWitness(
                relation,
                relation_operator,
                membership,
                stabilizer_coefficients,
                phase_compatible,
            )
        )

    all_ids = {item.term_id for item in completed_named_terms}
    bulk_ids = {item.term_id for item in request.bulk_terms}
    boundary_ids = {item.term_id for item in request.boundary_terms}
    termination = []
    for lift in request.string_lifts:
        request.metric.spin_exponent(lift.anyon_representative)
        if not condensate_subgroup.contains(lift.anyon_representative, backend):
            raise ArithmeticError("string lift does not represent an element of the condensate")
        declared = set(lift.remote_excitation_term_ids)
        if not declared <= bulk_ids or declared & boundary_ids:
            raise ValueError("remote excitation IDs must name bulk, not boundary, terms")
        actual = tuple(
            item.term_id
            for item in completed_named_terms
            if not lift.operator.commutes_with(item.operator)
        )
        if not set(actual) <= all_ids:
            raise ArithmeticError("computed string syndrome contains an unknown term")
        boundary_ok = not set(actual) & boundary_ids
        remote_ok = set(actual) == declared
        if not boundary_ok or not remote_ok:
            raise ValueError(
                f"short string {lift.label!r} does not have exactly its declared remote syndrome"
            )
        termination.append(
            StringTerminationWitness(
                lift.label,
                lift.anyon_representative,
                tuple(sorted(actual)),
                lift.remote_excitation_term_ids,
                boundary_ok,
                remote_ok,
            )
        )

    certificate = LocalBoundaryCompletionCertificate(
        stabilizer_validation=analysis.validation,
        condensate=condensation,
        anyon_generator_matrix=generator_matrix,
        anyon_relation_lattice=relation_lattice,
        anyon_relation_witness=relation_witness,
        fusion_lift_relations=tuple(fusion_relations),
        locality_witnesses=locality,
        termination_witnesses=tuple(termination),
        phase_aware_completion_verified=analysis.validation.valid,
        fusion_lift_verified=all(item.phase_compatible for item in fusion_relations),
        local_support_verified=all(item.within_declared_domain for item in locality),
        termination_verified=all(
            item.boundary_commutation_verified
            and item.exact_remote_syndrome_verified
            for item in termination
        ),
    )
    value = LocalBoundaryCompletion(
        completed_code=completed_code,
        anyon_fusion_invariant_factors=request.metric.group.invariant_factors,
        condensate_invariant_factors=condensate_subgroup.invariant_factors(backend),
        codespace_dimension=analysis.codespace_dimension,
        boundary_logical_invariant_factors=analysis.logical_invariant_factors,
        certificate=certificate,
    )
    return ComputationResult(
        operation="verify_local_gapped_boundary_2d",
        input_data=request,
        value=value,
        exactness=Exactness.BOUNDED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=(
            "Exact phase-aware verification on the explicitly recorded finite 2D "
            "patch and locality window. Lagrangianity is exact for the supplied "
            "finite Abelian metric group. This does not prove a thermodynamic "
            "spectral gap or extract anyons from an arbitrary stabilizer code."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("anyon_fusion_snf_verified", True),
            ("boundary_terms_commute_phase_aware", True),
            ("fusion_relations_lift_modulo_stabilizers", True),
            ("lagrangian_condensate_verified", True),
            ("locality_bounds_verified", True),
            ("short_string_termination_verified", True),
        ),
        backend_provenance=BackendProvenance(
            backend=backend.name,
            algorithm=(
                "finite metric-group condensation + FLINT lattice relations + "
                "phase-aware finite stabilizer completion"
            ),
            version=backend.version,
            parameters=(
                ("finite_window", request.locality_domain.window_label),
                ("max_completion_depth", request.locality_domain.max_completion_depth),
                ("max_short_string_sites", request.locality_domain.max_short_string_sites),
            ),
        ),
        resource_usage=(
            ("anyon_group_order", request.metric.group.order(backend)),
            ("boundary_terms", len(request.boundary_terms)),
            ("bulk_terms", len(request.bulk_terms)),
            ("pauli_sites", len(request.pauli_module.local_systems)),
            ("string_lifts", len(request.string_lifts)),
        ),
        warnings=(
            "bounded_exact applies only to this supplied finite completion; no "
            "completeness claim is made over other microscopic boundary Hamiltonians",
        ),
    )


def unsupported_automatic_anyon_extraction(
    code: StabilizerCodeSpec,
) -> ComputationResult:
    """Return a structured refusal for unsupported arbitrary-code extraction."""

    return ComputationResult(
        operation="extract_anyons_and_boundary_strings_2d",
        input_data=code,
        value=None,
        exactness=Exactness.UNSUPPORTED,
        theorem_scope=(
            "The current exact pipeline begins with an explicitly supplied finite "
            "Abelian metric group and certified short-string lifts."
        ),
        diagnostics=(
            "No saturation/period certificate was supplied for automatic anyon extraction.",
            "Provide explicit metric-group and short-string lifting data instead.",
        ),
        warnings=(
            "A small finite truncation is not accepted as a completeness certificate "
            "for all anyons of an arbitrary translation-invariant code.",
        ),
    )


__all__ = [
    "CondensateStringLift",
    "FiniteBoundaryLocalityDomain",
    "FusionLiftRelationWitness",
    "LocalBoundaryCompletion",
    "LocalBoundaryCompletionCertificate",
    "LocalBoundaryCompletionRequest",
    "LocalityWitness",
    "NamedPauliTerm",
    "StringTerminationWitness",
    "unsupported_automatic_anyon_extraction",
    "verify_local_boundary_completion",
]
