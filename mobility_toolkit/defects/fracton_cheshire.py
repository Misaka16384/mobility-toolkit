"""Finite, experimental X-cube lineon-condensate Cheshire reference.

The finite Pauli calculations in this module are exact.  The supplied local
completion adds the microscopic rigid z-lineon hopping/condensation terms and
deletes every anticommuting bulk check.  Calling the result a thermodynamic
Cheshire defect remains experimental: no uniform gap, multiplication,
Morita-equivalence, or circuit claim is made.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from mobility_toolkit.boundary_halfspace.xcube import (
    BoundaryToBulkBehavior,
    XCubeOrientationBenchmark,
    xcube_orientation_benchmark,
)
from mobility_toolkit.boundary_halfspace.geometry import PrimitiveNormal
from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    LocalPauliTerm,
    OperatorTemplate,
    PauliModule,
    PauliOperator,
    canonical_hash,
)
from mobility_toolkit.finite import FiniteIntegerBackend
from mobility_toolkit.geometry import (
    CrossingPolicy,
    ExplicitOperatorSpec,
    FiniteCode,
    InstanceSelector,
    LatticeCoordinate,
    LocalModification,
    SiteAddress,
    SupportAliasPolicy,
    compile_periodic_code,
    rectangular_region,
)
from mobility_toolkit.models import z2_xcube_model


IntegerVector = Tuple[int, ...]


@dataclass(frozen=True, order=True)
class LatticeProbeTerm:
    """One local Pauli term before finite-region identifications."""

    address: SiteAddress
    x_exponent: int = 0
    z_exponent: int = 0

    SCHEMA_ID = "mobility_toolkit.lattice_probe_term.v1"

    def __post_init__(self) -> None:
        if isinstance(self.x_exponent, bool) or not isinstance(self.x_exponent, int):
            raise TypeError("x_exponent must be an integer")
        if isinstance(self.z_exponent, bool) or not isinstance(self.z_exponent, int):
            raise TypeError("z_exponent must be an integer")
        if not (self.x_exponent % 2 or self.z_exponent % 2):
            raise ValueError("a lattice probe term must be projectively nontrivial")

    def to_canonical_dict(self) -> dict:
        return {
            "address": self.address,
            "schema": self.SCHEMA_ID,
            "x_exponent": self.x_exponent,
            "z_exponent": self.z_exponent,
        }


@dataclass(frozen=True)
class XCubeAxialLineRequest:
    """Explicit finite geometry, line-local rewrite, probe, and local window."""

    normal: PrimitiveNormal
    shape: Tuple[int, int, int]
    periodic_axes: Tuple[int, ...]
    modification: LocalModification
    tube_anchor_coordinates: Tuple[LatticeCoordinate, ...]
    probe_terms: Tuple[LatticeProbeTerm, ...]
    window_addresses: Tuple[SiteAddress, ...]

    SCHEMA_ID = "mobility_toolkit.xcube_axial_line_request.v1"

    def __post_init__(self) -> None:
        if self.normal.dimension != 3:
            raise ValueError("X-cube reference normal must have dimension three")
        if len(self.shape) != 3 or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in self.shape
        ):
            raise ValueError("shape must contain three positive integers")
        if tuple(sorted(set(self.periodic_axes))) != self.periodic_axes:
            raise ValueError("periodic_axes must be sorted and unique")
        if not self.probe_terms:
            raise ValueError("the finite reference requires an explicit probe")
        if not self.window_addresses:
            raise ValueError("the finite reference requires an explicit local window")
        object.__setattr__(
            self,
            "tube_anchor_coordinates",
            tuple(sorted(set(self.tube_anchor_coordinates))),
        )
        object.__setattr__(self, "probe_terms", tuple(self.probe_terms))
        object.__setattr__(
            self, "window_addresses", tuple(sorted(set(self.window_addresses)))
        )

    def to_canonical_dict(self) -> dict:
        return {
            "modification": self.modification,
            "normal": self.normal,
            "periodic_axes": self.periodic_axes,
            "probe_terms": self.probe_terms,
            "schema": self.SCHEMA_ID,
            "shape": self.shape,
            "tube_anchor_coordinates": self.tube_anchor_coordinates,
            "window_addresses": self.window_addresses,
        }


@dataclass(frozen=True, order=True)
class GeneratorInstanceKey:
    template_hash: str
    anchor: LatticeCoordinate

    SCHEMA_ID = "mobility_toolkit.generator_instance_key.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "anchor": self.anchor,
            "schema": self.SCHEMA_ID,
            "template_hash": self.template_hash,
        }


@dataclass(frozen=True)
class FiniteSyndromeEntry:
    generator_hash: str
    pairing_phase: int
    source_instances: Tuple[GeneratorInstanceKey, ...]

    SCHEMA_ID = "mobility_toolkit.fracton_finite_syndrome_entry.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "generator_hash": self.generator_hash,
            "pairing_phase": self.pairing_phase,
            "schema": self.SCHEMA_ID,
            "source_instances": self.source_instances,
        }


@dataclass(frozen=True)
class BinaryDefectPairedAlgebra:
    """Exact GF(2) paired quotient in the explicitly supplied site window."""

    window_site_ids: Tuple[str, ...]
    quotient_basis: Tuple[PauliOperator, ...]
    pairing_matrix: Tuple[Tuple[int, ...], ...]
    local_centralizer_dimension: int
    local_stabilizer_dimension: int
    pairing_rank: int
    radical_dimension: int

    SCHEMA_ID = "mobility_toolkit.binary_defect_paired_algebra.v1"

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return (2,) * len(self.quotient_basis)

    @property
    def radical_invariant_factors(self) -> Tuple[int, ...]:
        return (2,) * self.radical_dimension

    @property
    def verified(self) -> bool:
        size = len(self.quotient_basis)
        return (
            len(self.pairing_matrix) == size
            and all(len(row) == size for row in self.pairing_matrix)
            and all(self.pairing_matrix[index][index] == 0 for index in range(size))
            and all(
                self.pairing_matrix[left][right]
                == self.pairing_matrix[right][left]
                for left in range(size)
                for right in range(size)
            )
            and self.local_centralizer_dimension
            - self.local_stabilizer_dimension
            == size
            and _gf2_rank(_bit_rows(self.pairing_matrix)) == self.pairing_rank
            and self.radical_dimension == size - self.pairing_rank
        )

    def to_canonical_dict(self) -> dict:
        return {
            "invariant_factors": self.invariant_factors,
            "local_centralizer_dimension": self.local_centralizer_dimension,
            "local_stabilizer_dimension": self.local_stabilizer_dimension,
            "pairing_matrix": self.pairing_matrix,
            "pairing_rank": self.pairing_rank,
            "quotient_basis": self.quotient_basis,
            "radical_dimension": self.radical_dimension,
            "radical_invariant_factors": self.radical_invariant_factors,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
            "window_site_ids": self.window_site_ids,
        }


@dataclass(frozen=True)
class FiniteTranslationConstraint:
    shift: IntegerVector
    translated_probe_hash: str
    bulk_syndrome_size: int
    defect_syndrome_size: int
    bulk_excitation_nontrivial: bool
    terminates_on_supplied_defect: bool

    SCHEMA_ID = "mobility_toolkit.fracton_finite_translation_constraint.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_excitation_nontrivial": self.bulk_excitation_nontrivial,
            "bulk_syndrome_size": self.bulk_syndrome_size,
            "defect_syndrome_size": self.defect_syndrome_size,
            "schema": self.SCHEMA_ID,
            "shift": self.shift,
            "terminates_on_supplied_defect": self.terminates_on_supplied_defect,
            "translated_probe_hash": self.translated_probe_hash,
        }


@dataclass(frozen=True)
class FractonFiniteScalingSample:
    shape: Tuple[int, int, int]
    line_length_lattice_steps: int
    qubit_count: int
    bulk_stabilizer_rank: int
    defect_stabilizer_rank: int
    bulk_codespace_dimension: int
    defect_codespace_dimension: int
    removed_instance_count: int
    added_operator_count: int

    SCHEMA_ID = "mobility_toolkit.fracton_finite_scaling_sample.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_codespace_dimension": self.bulk_codespace_dimension,
            "bulk_stabilizer_rank": self.bulk_stabilizer_rank,
            "added_operator_count": self.added_operator_count,
            "defect_codespace_dimension": self.defect_codespace_dimension,
            "defect_stabilizer_rank": self.defect_stabilizer_rank,
            "line_length_lattice_steps": self.line_length_lattice_steps,
            "qubit_count": self.qubit_count,
            "removed_instance_count": self.removed_instance_count,
            "schema": self.SCHEMA_ID,
            "shape": self.shape,
        }


@dataclass(frozen=True)
class XCubeFractonLineCertificate:
    source_orientation: XCubeOrientationBenchmark
    probe_operator: PauliOperator
    probe_hash: str
    bulk_syndrome: Tuple[FiniteSyndromeEntry, ...]
    bulk_syndrome_hash: str
    defect_syndrome: Tuple[FiniteSyndromeEntry, ...]
    defect_syndrome_hash: str
    removed_instances: Tuple[GeneratorInstanceKey, ...]
    added_condensation_operators: Tuple[PauliOperator, ...]
    added_condensation_hashes: Tuple[str, ...]
    hidden_charge_operator: PauliOperator
    hidden_charge_hash: str
    tube_anchor_coordinates: Tuple[LatticeCoordinate, ...]
    bulk_validation_verified: bool
    defect_validation_verified: bool
    finite_geometry_verified: bool
    modification_locality_verified: bool
    removal_covers_bulk_syndrome: bool
    local_algebra_verified: bool
    removed_lineon_sector_only: bool
    removed_records_fully_selected: bool
    added_condensation_present: bool
    added_condensation_commutes: bool
    rank_deficit_relative_to_bulk: int
    hidden_charge_commutes: bool
    hidden_charge_independent: bool
    hidden_charge_restores_bulk_rank: bool

    SCHEMA_ID = "mobility_toolkit.xcube_fracton_line_certificate.v2"

    @property
    def verified(self) -> bool:
        bulk_instances = {
            instance
            for entry in self.bulk_syndrome
            for instance in entry.source_instances
        }
        return (
            self.source_orientation.behavior
            is BoundaryToBulkBehavior.NOT_SURJECTIVE
            and self.source_orientation.half_space.normal.components == (0, 0, 1)
            and canonical_hash(PauliOperator.SCHEMA_ID, self.probe_operator)
            == self.probe_hash
            and canonical_hash("xcube-fracton-bulk-syndrome", self.bulk_syndrome)
            == self.bulk_syndrome_hash
            and canonical_hash("xcube-fracton-defect-syndrome", self.defect_syndrome)
            == self.defect_syndrome_hash
            and bool(self.added_condensation_operators)
            and tuple(
                canonical_hash(PauliOperator.SCHEMA_ID, operator)
                for operator in self.added_condensation_operators
            )
            == self.added_condensation_hashes
            and canonical_hash(
                PauliOperator.SCHEMA_ID, self.hidden_charge_operator
            )
            == self.hidden_charge_hash
            and bool(self.bulk_syndrome)
            and not self.defect_syndrome
            and not self.probe_operator.scalar_obstruction
            and self.bulk_validation_verified
            and self.defect_validation_verified
            and self.finite_geometry_verified
            and self.modification_locality_verified
            and self.removal_covers_bulk_syndrome
            and bulk_instances.issubset(set(self.removed_instances))
            and self.local_algebra_verified
            and self.removed_lineon_sector_only
            and self.removed_records_fully_selected
            and self.added_condensation_present
            and self.added_condensation_commutes
            and self.rank_deficit_relative_to_bulk == 1
            and self.hidden_charge_commutes
            and self.hidden_charge_independent
            and self.hidden_charge_restores_bulk_rank
        )

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_syndrome": self.bulk_syndrome,
            "bulk_syndrome_hash": self.bulk_syndrome_hash,
            "bulk_validation_verified": self.bulk_validation_verified,
            "added_condensation_hashes": self.added_condensation_hashes,
            "added_condensation_operators": self.added_condensation_operators,
            "added_condensation_commutes": self.added_condensation_commutes,
            "added_condensation_present": self.added_condensation_present,
            "defect_syndrome": self.defect_syndrome,
            "defect_syndrome_hash": self.defect_syndrome_hash,
            "defect_validation_verified": self.defect_validation_verified,
            "finite_geometry_verified": self.finite_geometry_verified,
            "hidden_charge_commutes": self.hidden_charge_commutes,
            "hidden_charge_hash": self.hidden_charge_hash,
            "hidden_charge_independent": self.hidden_charge_independent,
            "hidden_charge_operator": self.hidden_charge_operator,
            "hidden_charge_restores_bulk_rank":
                self.hidden_charge_restores_bulk_rank,
            "local_algebra_verified": self.local_algebra_verified,
            "modification_locality_verified": self.modification_locality_verified,
            "probe_hash": self.probe_hash,
            "probe_operator": self.probe_operator,
            "rank_deficit_relative_to_bulk": self.rank_deficit_relative_to_bulk,
            "removal_covers_bulk_syndrome": self.removal_covers_bulk_syndrome,
            "removed_instances": self.removed_instances,
            "removed_lineon_sector_only": self.removed_lineon_sector_only,
            "removed_records_fully_selected":
                self.removed_records_fully_selected,
            "schema": self.SCHEMA_ID,
            "source_orientation": self.source_orientation,
            "tube_anchor_coordinates": self.tube_anchor_coordinates,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class XCubeFractonLineReference:
    model_id: str
    request: XCubeAxialLineRequest
    bulk_compilation_certificate: object
    defect_compilation_certificate: object
    probe_operator: PauliOperator
    bulk_syndrome: Tuple[FiniteSyndromeEntry, ...]
    defect_syndrome: Tuple[FiniteSyndromeEntry, ...]
    condensation_operators: Tuple[PauliOperator, ...]
    hidden_charge_operator: PauliOperator
    local_algebra: BinaryDefectPairedAlgebra
    translation_constraints: Tuple[FiniteTranslationConstraint, ...]
    scaling_sample: FractonFiniteScalingSample
    certificate: XCubeFractonLineCertificate

    SCHEMA_ID = "mobility_toolkit.xcube_fracton_line_reference.v2"

    @property
    def terminating_shifts(self) -> Tuple[IntegerVector, ...]:
        return tuple(
            item.shift
            for item in self.translation_constraints
            if item.terminates_on_supplied_defect
        )

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_compilation_certificate": self.bulk_compilation_certificate,
            "bulk_syndrome": self.bulk_syndrome,
            "certificate": self.certificate,
            "condensation_operators": self.condensation_operators,
            "defect_compilation_certificate": self.defect_compilation_certificate,
            "defect_syndrome": self.defect_syndrome,
            "local_algebra": self.local_algebra,
            "hidden_charge_operator": self.hidden_charge_operator,
            "model_id": self.model_id,
            "probe_operator": self.probe_operator,
            "request": self.request,
            "scaling_sample": self.scaling_sample,
            "schema": self.SCHEMA_ID,
            "terminating_shifts": self.terminating_shifts,
            "translation_constraints": self.translation_constraints,
        }


def xcube_axial_line_reference_request(
    line_length_lattice_steps: int = 1,
) -> XCubeAxialLineRequest:
    """Build an embedded finite local z-lineon-condensate completion."""

    if (
        isinstance(line_length_lattice_steps, bool)
        or not isinstance(line_length_lattice_steps, int)
        or line_length_lattice_steps < 1
    ):
        raise ValueError("line_length_lattice_steps must be a positive integer")
    model = z2_xcube_model()
    shape = (2, 2, line_length_lattice_steps + 5)
    region = rectangular_region(
        shape,
        model.code.species,
        periodic_axes=(0, 1),
    )
    cross_zx_hash = canonical_hash(
        OperatorTemplate.SCHEMA_ID, model.code.stabilizer_templates[1]
    )
    path_coordinates = tuple(
        LatticeCoordinate((1, 1, 2 + offset))
        for offset in range(line_length_lattice_steps)
    )
    anchors = tuple(
        LatticeCoordinate((1, 1, 1 + offset))
        for offset in range(line_length_lattice_steps + 1)
    )
    selectors = tuple(
        InstanceSelector(cross_zx_hash, anchor) for anchor in anchors
    )
    add_operators = []
    for index, coordinate in enumerate(path_coordinates):
        resolved = region.resolve(SiteAddress(coordinate, "edge_x"))
        if resolved is None:
            raise ArithmeticError("embedded z-lineon link failed to resolve")
        add_operators.append(
            ExplicitOperatorSpec(
                f"z-lineon-hop-{index}",
                0,
                (LocalPauliTerm.cyclic(resolved.physical_site_id, x=1),),
            )
        )
    modification = LocalModification(
        "experimental-xcube-standard-z-lineon-condensate",
        remove_instances=selectors,
        add_operators=tuple(add_operators),
        assumptions=(
            "add X(edge_x) on consecutive z links to condense q2 z-lineons",
            "delete all and only anticommuting cross_zx checks",
            "retain every already-commuting bulk stabilizer",
            "finite local commuting completion; no thermodynamic gap claim",
        ),
    )
    probe = (
        LatticeProbeTerm(
            SiteAddress(path_coordinates[0], "edge_x"),
            x_exponent=1,
        ),
    )
    window = tuple(
        SiteAddress(coordinate, "edge_x")
        for coordinate in path_coordinates
    )
    return XCubeAxialLineRequest(
        PrimitiveNormal((0, 0, 1)),
        shape,
        (0, 1),
        modification,
        anchors,
        probe,
        window,
    )


def _unsupported(
    request: XCubeAxialLineRequest, reason: str, orientation_result: ComputationResult
) -> ComputationResult:
    return ComputationResult(
        operation="defects.xcube_fracton_line_reference",
        input_data=request,
        value=None,
        exactness=Exactness.UNSUPPORTED,
        assumptions=("finite reference preflight only",),
        theorem_scope=reason,
        verification=(
            ("orientation_exactness", orientation_result.exactness),
            ("requested_normal", request.normal.components),
        ),
        warnings=(
            "No finite line-defect conclusion is extrapolated to this request.",
            "No thermodynamic, dynamical, condensation, or completion claim is made.",
        ),
    )


def _instantiate_probe(
    module: PauliModule,
    region: object,
    terms: Sequence[LatticeProbeTerm],
) -> Optional[PauliOperator]:
    operator = module.identity()
    for term in terms:
        resolved = region.resolve(term.address)
        if resolved is None:
            return None
        image = resolved.frame.apply((term.x_exponent,), (term.z_exponent,))
        operator = operator * module.operator(
            (
                LocalPauliTerm(
                    resolved.physical_site_id,
                    image.x_exponents,
                    image.z_exponents,
                ),
            ),
            phase=image.phase,
        )
    return operator


def _syndrome(
    code: FiniteCode, operator: PauliOperator
) -> Tuple[FiniteSyndromeEntry, ...]:
    entries = []
    for record in code.compiled_generators:
        phase = operator.projective_pairing(record.operator)
        if phase == 0:
            continue
        instances = tuple(
            sorted(
                GeneratorInstanceKey(source.template_hash, source.anchor)
                for source in record.sources
                if hasattr(source, "template_hash") and hasattr(source, "anchor")
            )
        )
        entries.append(
            FiniteSyndromeEntry(
                canonical_hash(PauliOperator.SCHEMA_ID, record.operator),
                phase,
                instances,
            )
        )
    return tuple(sorted(entries, key=lambda item: item.generator_hash))


def _operator_vector(operator: PauliOperator) -> int:
    systems = operator.module.local_systems
    index = {system.site_id: position for position, system in enumerate(systems)}
    width = len(systems)
    value = 0
    for term in operator.terms:
        position = index[term.site_id]
        if term.x_exponents[0] % 2:
            value ^= 1 << position
        if term.z_exponents[0] % 2:
            value ^= 1 << (width + position)
    return value


def _bit_rows(matrix: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    return tuple(
        sum((value & 1) << column for column, value in enumerate(row))
        for row in matrix
    )


def _gf2_rref(rows: Sequence[int], width: int) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    reduced = [value for value in rows if value]
    pivot_columns = []
    rank = 0
    for column in range(width):
        pivot = next(
            (
                index
                for index in range(rank, len(reduced))
                if reduced[index] & (1 << column)
            ),
            None,
        )
        if pivot is None:
            continue
        reduced[rank], reduced[pivot] = reduced[pivot], reduced[rank]
        for index in range(len(reduced)):
            if index != rank and reduced[index] & (1 << column):
                reduced[index] ^= reduced[rank]
        pivot_columns.append(column)
        rank += 1
    return tuple(reduced[:rank]), tuple(pivot_columns)


def _gf2_rank(rows: Sequence[int]) -> int:
    width = max((value.bit_length() for value in rows), default=0)
    return len(_gf2_rref(rows, width)[0])


def _gf2_nullspace(rows: Sequence[int], width: int) -> Tuple[int, ...]:
    reduced, pivots = _gf2_rref(rows, width)
    free = tuple(column for column in range(width) if column not in set(pivots))
    result = []
    for column in free:
        vector = 1 << column
        for pivot, row in zip(pivots, reduced):
            if (row & vector).bit_count() % 2:
                vector ^= 1 << pivot
        result.append(vector)
    return tuple(result)


def _independent_basis(rows: Sequence[int]) -> Tuple[int, ...]:
    width = max((value.bit_length() for value in rows), default=0)
    return _gf2_rref(rows, width)[0]


def _local_vector_to_operator(
    module: PauliModule, site_ids: Sequence[str], vector: int
) -> PauliOperator:
    size = len(site_ids)
    return module.operator(
        tuple(
            LocalPauliTerm.cyclic(
                site_id,
                x=(vector >> index) & 1,
                z=(vector >> (size + index)) & 1,
            )
            for index, site_id in enumerate(site_ids)
            if (vector >> index) & 1 or (vector >> (size + index)) & 1
        )
    )


def _binary_local_algebra(
    code: FiniteCode, window_site_ids: Sequence[str]
) -> BinaryDefectPairedAlgebra:
    systems = code.pauli_module.local_systems
    site_index = {system.site_id: index for index, system in enumerate(systems)}
    requested = tuple(sorted(set(window_site_ids)))
    if any(site_id not in site_index for site_id in requested):
        raise ValueError("the defect-local window contains an unknown site")
    nsites = len(systems)
    stabilizer_basis = _independent_basis(
        tuple(_operator_vector(operator) for operator in code.generators)
    )
    selected = tuple(site_index[site_id] for site_id in requested)
    selected_full = selected + tuple(nsites + index for index in selected)
    selected_set = set(selected_full)
    outside = tuple(index for index in range(2 * nsites) if index not in selected_set)

    centralizer_equations = []
    for stabilizer in stabilizer_basis:
        equation = 0
        for local_index, global_index in enumerate(selected):
            if stabilizer & (1 << (nsites + global_index)):
                equation ^= 1 << local_index
            if stabilizer & (1 << global_index):
                equation ^= 1 << (len(selected) + local_index)
        centralizer_equations.append(equation)
    local_centralizer = _gf2_nullspace(
        centralizer_equations, 2 * len(selected)
    )

    coefficient_equations = tuple(
        sum(
            ((stabilizer >> global_index) & 1) << coefficient
            for coefficient, stabilizer in enumerate(stabilizer_basis)
        )
        for global_index in outside
    )
    coefficient_kernel = _gf2_nullspace(
        coefficient_equations, len(stabilizer_basis)
    )
    local_stabilizers = []
    for coefficients in coefficient_kernel:
        full = 0
        for index, stabilizer in enumerate(stabilizer_basis):
            if coefficients & (1 << index):
                full ^= stabilizer
        local = 0
        for local_index, global_index in enumerate(selected):
            if full & (1 << global_index):
                local ^= 1 << local_index
            if full & (1 << (nsites + global_index)):
                local ^= 1 << (len(selected) + local_index)
        local_stabilizers.append(local)
    local_stabilizer_basis = _independent_basis(local_stabilizers)

    spanning = list(local_stabilizer_basis)
    quotient_basis = []
    current_rank = _gf2_rank(spanning)
    for vector in local_centralizer:
        trial_rank = _gf2_rank(tuple(spanning) + (vector,))
        if trial_rank > current_rank:
            spanning.append(vector)
            quotient_basis.append(vector)
            current_rank = trial_rank

    size = len(selected)

    def pairing(left: int, right: int) -> int:
        mask = (1 << size) - 1
        left_x, left_z = left & mask, (left >> size) & mask
        right_x, right_z = right & mask, (right >> size) & mask
        return (
            (left_x & right_z).bit_count() + (left_z & right_x).bit_count()
        ) % 2

    pairing_matrix = tuple(
        tuple(pairing(left, right) for right in quotient_basis)
        for left in quotient_basis
    )
    pairing_rank = _gf2_rank(_bit_rows(pairing_matrix))
    result = BinaryDefectPairedAlgebra(
        requested,
        tuple(
            _local_vector_to_operator(code.pauli_module, requested, vector)
            for vector in quotient_basis
        ),
        pairing_matrix,
        len(local_centralizer),
        len(local_stabilizer_basis),
        pairing_rank,
        len(quotient_basis) - pairing_rank,
    )
    if not result.verified:
        raise ArithmeticError("binary defect-local paired-algebra certificate failed")
    return result


def _translation_constraints(
    request: XCubeAxialLineRequest,
    bulk: FiniteCode,
    defect: FiniteCode,
) -> Tuple[FiniteTranslationConstraint, ...]:
    base = request.probe_terms[0].address.coordinate.free
    constraints = []
    for target in itertools.product(*(range(length) for length in request.shape)):
        shift = tuple(right - left for left, right in zip(base, target))
        translated_terms = tuple(
            LatticeProbeTerm(
                SiteAddress(
                    term.address.coordinate.translated(shift),
                    term.address.species_id,
                ),
                term.x_exponent,
                term.z_exponent,
            )
            for term in request.probe_terms
        )
        probe = _instantiate_probe(bulk.pauli_module, bulk.region, translated_terms)
        if probe is None:
            continue
        bulk_syndrome = _syndrome(bulk, probe)
        defect_syndrome = _syndrome(defect, probe)
        constraints.append(
            FiniteTranslationConstraint(
                shift,
                canonical_hash(PauliOperator.SCHEMA_ID, probe),
                len(bulk_syndrome),
                len(defect_syndrome),
                bool(bulk_syndrome),
                bool(bulk_syndrome) and not defect_syndrome,
            )
        )
    return tuple(sorted(constraints, key=lambda item: item.shift))


def analyze_xcube_fracton_line_reference(
    request: XCubeAxialLineRequest,
    backend: FiniteIntegerBackend,
) -> ComputationResult:
    """Run exact finite algebra for an explicit local axial completion."""

    if not isinstance(request, XCubeAxialLineRequest):
        raise TypeError("request must be an XCubeAxialLineRequest")
    orientation = xcube_orientation_benchmark(request.normal)
    if (
        request.normal.components != (0, 0, 1)
        or orientation.value is None
        or request.periodic_axes != (0, 1)
    ):
        return _unsupported(
            request,
            "This finite reference is registered only for the axial c>=0 oracle "
            "with periodic x,y and open z.",
            orientation,
        )

    model = z2_xcube_model()
    region = rectangular_region(
        request.shape, model.code.species, periodic_axes=request.periodic_axes
    )
    compile_kwargs = {
        "crossing_policy": CrossingPolicy.OMIT_WHOLE_INSTANCE,
        "support_alias_policy": SupportAliasPolicy.NORMAL_FORM_PUSHFORWARD,
        "backend": backend,
    }
    bulk = compile_periodic_code(model.code, region, **compile_kwargs)
    defect = compile_periodic_code(
        model.code,
        region,
        modifications=(request.modification,),
        **compile_kwargs,
    )
    probe = _instantiate_probe(bulk.pauli_module, region, request.probe_terms)
    if probe is None:
        return _unsupported(
            request, "The supplied probe crosses the open finite boundary.", orientation
        )
    bulk_syndrome = _syndrome(bulk, probe)
    defect_syndrome = _syndrome(defect, probe)
    added_condensation_operators = tuple(
        bulk.pauli_module.operator(specification.terms, phase=specification.phase)
        for specification in request.modification.add_operators
    )
    added_condensation_hashes = tuple(
        canonical_hash(PauliOperator.SCHEMA_ID, operator)
        for operator in added_condensation_operators
    )
    defect_generator_hashes = {
        canonical_hash(PauliOperator.SCHEMA_ID, operator)
        for operator in defect.generators
    }
    added_condensation_present = set(added_condensation_hashes).issubset(
        defect_generator_hashes
    )
    added_condensation_commutes = all(
        not _syndrome(defect, operator)
        for operator in added_condensation_operators
    )
    removed = tuple(
        sorted(
            GeneratorInstanceKey(selector.template_hash, selector.anchor)
            for selector in request.modification.remove_instances
        )
    )
    tube_anchors = set(request.tube_anchor_coordinates)
    locality = all(instance.anchor in tube_anchors for instance in removed)
    removed_set = set(removed)
    removed_records = tuple(
        record
        for record in bulk.compiled_generators
        if any(
            GeneratorInstanceKey(source.template_hash, source.anchor)
            in removed_set
            for source in record.sources
            if hasattr(source, "template_hash") and hasattr(source, "anchor")
        )
    )
    removed_record_instances = tuple(
        {
            GeneratorInstanceKey(source.template_hash, source.anchor)
            for source in record.sources
            if hasattr(source, "template_hash") and hasattr(source, "anchor")
        }
        for record in removed_records
    )
    removed_records_fully_selected = bool(removed_records) and all(
        instances and instances.issubset(removed_set)
        for instances in removed_record_instances
    )
    cross_zx_hash = canonical_hash(
        OperatorTemplate.SCHEMA_ID, model.code.stabilizer_templates[1]
    )
    removed_lineon_sector_only = bool(removed) and all(
        instance.template_hash == cross_zx_hash for instance in removed
    )
    hidden_charge = bulk.pauli_module.identity()
    for record in removed_records:
        hidden_charge = hidden_charge * record.operator
    bulk_instances = {
        instance
        for entry in bulk_syndrome
        for instance in entry.source_instances
    }
    resolved_window = tuple(
        region.resolve(address) for address in request.window_addresses
    )
    if any(item is None for item in resolved_window):
        return _unsupported(
            request,
            "The supplied defect-local window crosses the open finite boundary.",
            orientation,
        )
    local_algebra = _binary_local_algebra(
        defect, tuple(item.physical_site_id for item in resolved_window)
    )
    translations = _translation_constraints(request, bulk, defect)
    nqubits = len(bulk.pauli_module.local_systems)
    bulk_rank = _gf2_rank(
        tuple(_operator_vector(operator) for operator in bulk.generators)
    )
    defect_rank = _gf2_rank(
        tuple(_operator_vector(operator) for operator in defect.generators)
    )
    hidden_charge_vector = _operator_vector(hidden_charge)
    hidden_charge_commutes = not _syndrome(defect, hidden_charge)
    hidden_charge_augmented_rank = _gf2_rank(
        tuple(_operator_vector(operator) for operator in defect.generators)
        + (hidden_charge_vector,)
    )
    hidden_charge_independent = hidden_charge_augmented_rank == defect_rank + 1
    hidden_charge_restores_bulk_rank = hidden_charge_augmented_rank == bulk_rank
    rank_deficit = bulk_rank - defect_rank
    scaling = FractonFiniteScalingSample(
        request.shape,
        len(added_condensation_operators),
        nqubits,
        bulk_rank,
        defect_rank,
        2 ** (nqubits - bulk_rank),
        2 ** (nqubits - defect_rank),
        len(removed),
        len(added_condensation_operators),
    )
    certificate = XCubeFractonLineCertificate(
        orientation.value,
        probe,
        canonical_hash(PauliOperator.SCHEMA_ID, probe),
        bulk_syndrome,
        canonical_hash("xcube-fracton-bulk-syndrome", bulk_syndrome),
        defect_syndrome,
        canonical_hash("xcube-fracton-defect-syndrome", defect_syndrome),
        removed,
        added_condensation_operators,
        added_condensation_hashes,
        hidden_charge,
        canonical_hash(PauliOperator.SCHEMA_ID, hidden_charge),
        request.tube_anchor_coordinates,
        bulk.validation.valid,
        defect.validation.valid,
        request.periodic_axes == (0, 1)
        and set(request.periodic_axes).isdisjoint({2}),
        locality,
        bulk_instances.issubset(set(removed)),
        local_algebra.verified,
        removed_lineon_sector_only,
        removed_records_fully_selected,
        added_condensation_present,
        added_condensation_commutes,
        rank_deficit,
        hidden_charge_commutes,
        hidden_charge_independent,
        hidden_charge_restores_bulk_rank,
    )
    value = XCubeFractonLineReference(
        model.model_id,
        request,
        bulk.compilation_certificate,
        defect.compilation_certificate,
        probe,
        bulk_syndrome,
        defect_syndrome,
        added_condensation_operators,
        hidden_charge,
        local_algebra,
        translations,
        scaling,
        certificate,
    )
    return ComputationResult(
        operation="defects.xcube_fracton_line_reference",
        input_data=request,
        value=value,
        exactness=Exactness.EXPERIMENTAL,
        assumptions=(
            "Ruba--Yang Eq. (140) Z2 X-cube presentation",
            "finite x,y-periodic and z-open slab",
            "q2 z-lineon is created/hopped by X(edge_x) along z",
            "local X(edge_x) condensate terms replace anticommuting cross_zx checks",
            "defect endpoints are embedded away from the physical open-z boundary",
            "small-period support aliases are phase-aware and recorded",
        ),
        theorem_scope=(
            "Syndromes, commutators, local projector replacement, binary paired "
            "quotients, hidden-charge independence, translation scans, and "
            "stabilizer ranks are exact for this supplied finite code. A uniform "
            "thermodynamic gap and circuit-certified Cheshire interpretation are "
            "not established."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate=certificate,
        verification=(
            ("finite_certificate_verified", certificate.verified),
            ("finite_local_algebra_verified", local_algebra.verified),
            ("source_orientation_behavior", orientation.value.behavior),
            ("thermodynamic_claim", False),
        ),
        backend_provenance=BackendProvenance(
            getattr(backend, "name", backend.__class__.__name__),
            "finite geometry compilation plus exact GF(2) paired linear algebra",
            getattr(backend, "version", ""),
            (("shape", request.shape),),
        ),
        diagnostics=(
            "The microscopic z-lineon hopping probe has nonzero bulk syndrome and "
            "zero syndrome after the local condensate completion."
            if bulk_syndrome and not defect_syndrome
            else "The supplied z-lineon probe is not absorbed by the completion.",
            "The product of all replaced cross_zx checks is a commuting independent "
            "hidden-charge operator whose restoration recovers the bulk rank."
            if (
                hidden_charge_commutes
                and hidden_charge_independent
                and hidden_charge_restores_bulk_rank
            )
            else "The expected finite hidden-charge certificate failed.",
        ),
        warnings=(
            "The ordinary 2D anyon Lagrangian-subgroup criterion is not applied.",
            "The local terms form an exact finite commuting completion, but no "
            "uniform thermodynamic spectral gap is certified.",
            "A finite hidden-charge qubit is not by itself a thermodynamic species "
            "or mobility-enriched algebra classification.",
            "Finite translation data do not imply thermodynamic mobility.",
            "No creation, deformation, fusion, circuit-depth, adiabatic, or "
            "dynamical claim is made.",
        ),
    )


__all__ = [
    "BinaryDefectPairedAlgebra",
    "FiniteSyndromeEntry",
    "FiniteTranslationConstraint",
    "FractonFiniteScalingSample",
    "GeneratorInstanceKey",
    "LatticeProbeTerm",
    "XCubeAxialLineRequest",
    "XCubeFractonLineCertificate",
    "XCubeFractonLineReference",
    "analyze_xcube_fracton_line_reference",
    "xcube_axial_line_reference_request",
]
