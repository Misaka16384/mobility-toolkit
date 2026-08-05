"""Static Cheshire-string constructions for finite 3D cellular codes.

The reference construction implements the stabilizer replacement in Eq. (8)
of Tantivasadakarn--Chen, arXiv:2307.03180, for the 3+1D Z2 toric code with
plaquette qubits.  All conclusions here are exact for the supplied finite
static Hamiltonian.  They do not imply a circuit-depth or phase-equivalence
statement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core.pauli import LocalPauliTerm, PauliOperator
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    Exactness,
)
from mobility_toolkit.defects.local_algebra import (
    DefectLocalAlgebra,
    defect_local_algebra,
)
from mobility_toolkit.defects.projection import (
    PinnedSubsystemProjection,
    project_pinned_z_subsystems,
)
from mobility_toolkit.defects.tube import (
    TubularDeletedRepresentation,
    compile_deleted_tube_representation,
)
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.stabilizer import (
    FiniteStabilizerAnalysis,
    analyze_finite_stabilizer,
)
from mobility_toolkit.geometry.cell_complex import (
    CellularCheck,
    CellularCode,
    CellularPauliConvention,
    CubicalComplex,
    cellular_stabilizer_code,
)


REFERENCE = "Tantivasadakarn--Chen arXiv:2307.03180 Eq. (6)--(8)"
STATIC_THEOREM_SCOPE = (
    "Certified exact for the supplied finite static stabilizer Hamiltonian and "
    "support windows; no thermodynamic stabilization, circuit-depth, deformation-"
    "equivalence, tube-shrinking, or fusion-dynamics claim."
)


class LineTopology(str, Enum):
    OPEN_SEGMENT = "open_segment"
    CLOSED_LOOP = "closed_loop"


@dataclass(frozen=True)
class LineDefect:
    defect_id: str
    cube_cell_ids: Tuple[str, ...]
    condensate_plaquette_ids: Tuple[str, ...]
    topology: LineTopology
    endpoint_cube_ids: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.line_defect.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.defect_id, str) or not self.defect_id:
            raise ValueError("defect_id must be a nonempty string")
        if not isinstance(self.topology, LineTopology):
            raise TypeError("line topology must be an explicit LineTopology")
        cubes = tuple(self.cube_cell_ids)
        plaquettes = tuple(self.condensate_plaquette_ids)
        endpoints = tuple(self.endpoint_cube_ids)
        if len(cubes) < 2 or len(set(cubes)) != len(cubes):
            raise ValueError("a line defect needs at least two distinct path cubes")
        expected_links = len(cubes) - 1
        if self.topology == LineTopology.CLOSED_LOOP:
            expected_links += 1
            if endpoints:
                raise ValueError("a closed loop cannot have endpoint cubes")
        elif self.topology == LineTopology.OPEN_SEGMENT:
            if endpoints != (cubes[0], cubes[-1]):
                raise ValueError("open-segment endpoints must be the first and last cubes")
        else:
            raise TypeError("line topology must be an explicit LineTopology")
        if len(plaquettes) != expected_links or len(set(plaquettes)) != len(plaquettes):
            raise ValueError("condensate plaquettes must give one distinct face per path link")
        object.__setattr__(self, "cube_cell_ids", cubes)
        object.__setattr__(self, "condensate_plaquette_ids", plaquettes)
        object.__setattr__(self, "endpoint_cube_ids", endpoints)

    def to_canonical_dict(self) -> dict:
        return {
            "condensate_plaquette_ids": self.condensate_plaquette_ids,
            "cube_cell_ids": self.cube_cell_ids,
            "defect_id": self.defect_id,
            "endpoint_cube_ids": self.endpoint_cube_ids,
            "schema": self.SCHEMA_ID,
            "topology": self.topology,
        }


def _require_3d(complex_: CubicalComplex) -> None:
    if complex_.dimension != 3:
        raise ValueError("the Cheshire reference constructors require a 3D cubical complex")


def _cube_ids_from_bases(
    complex_: CubicalComplex, cube_bases: Iterable[Sequence[int]]
) -> Tuple[str, ...]:
    _require_3d(complex_)
    by_base = {cell.base: cell.cell_id for cell in complex_.cells_by_dimension[3]}
    result = []
    for base in cube_bases:
        key = tuple(base)
        if key not in by_base:
            raise ValueError("cube base is not present in the supplied complex: " + repr(key))
        result.append(by_base[key])
    return tuple(result)


def _incident_plaquettes_by_cube(complex_: CubicalComplex) -> dict:
    boundary = complex_.chain_complex.boundary_maps[3]
    face_ids = complex_.chain_complex.cell_ids_by_dimension[2]
    cube_ids = complex_.chain_complex.cell_ids_by_dimension[3]
    incident = {cube_id: [] for cube_id in cube_ids}
    for row, column, coefficient in boundary.entries:
        if coefficient % 2:
            incident[cube_ids[column]].append(face_ids[row])
    return {
        cube_id: tuple(sorted(face_cell_ids))
        for cube_id, face_cell_ids in incident.items()
    }


def _shared_plaquette(
    left: str, right: str, incident: dict
) -> str:
    shared = tuple(sorted(set(incident[left]).intersection(incident[right])))
    if len(shared) != 1:
        raise ValueError(
            f"path cubes {left} and {right} share {len(shared)} plaquettes; "
            "use an unambiguous cellulation or construct LineDefect explicitly"
        )
    return shared[0]


def _line_from_bases(
    complex_: CubicalComplex,
    defect_id: str,
    cube_bases: Iterable[Sequence[int]],
    topology: LineTopology,
) -> LineDefect:
    cubes = _cube_ids_from_bases(complex_, cube_bases)
    incident = _incident_plaquettes_by_cube(complex_)
    pairs = list(zip(cubes, cubes[1:]))
    if topology == LineTopology.CLOSED_LOOP:
        pairs.append((cubes[-1], cubes[0]))
    plaquettes = tuple(_shared_plaquette(left, right, incident) for left, right in pairs)
    endpoints = (cubes[0], cubes[-1]) if topology == LineTopology.OPEN_SEGMENT else ()
    return LineDefect(defect_id, cubes, plaquettes, topology, endpoints)


@dataclass(frozen=True)
class OpenSegment:
    line: LineDefect

    SCHEMA_ID = "mobility_toolkit.open_cheshire_segment.v1"

    def __post_init__(self) -> None:
        if self.line.topology != LineTopology.OPEN_SEGMENT:
            raise ValueError("OpenSegment requires an open LineDefect")

    @classmethod
    def from_cube_bases(
        cls,
        complex_: CubicalComplex,
        defect_id: str,
        cube_bases: Iterable[Sequence[int]],
    ) -> "OpenSegment":
        return cls(
            _line_from_bases(
                complex_, defect_id, cube_bases, LineTopology.OPEN_SEGMENT
            )
        )

    def to_canonical_dict(self) -> dict:
        return {"line": self.line, "schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class ClosedLoop:
    line: LineDefect

    SCHEMA_ID = "mobility_toolkit.closed_cheshire_loop.v1"

    def __post_init__(self) -> None:
        if self.line.topology != LineTopology.CLOSED_LOOP:
            raise ValueError("ClosedLoop requires a closed LineDefect")

    @classmethod
    def from_cube_bases(
        cls,
        complex_: CubicalComplex,
        defect_id: str,
        cube_bases: Iterable[Sequence[int]],
    ) -> "ClosedLoop":
        return cls(
            _line_from_bases(complex_, defect_id, cube_bases, LineTopology.CLOSED_LOOP)
        )

    def to_canonical_dict(self) -> dict:
        return {"line": self.line, "schema": self.SCHEMA_ID}


def _cube_adjacency(complex_: CubicalComplex) -> dict:
    incident = _incident_plaquettes_by_cube(complex_)
    face_to_cubes = {}
    for cube_id, faces in incident.items():
        for face_id in faces:
            face_to_cubes.setdefault(face_id, []).append(cube_id)
    adjacency = {cube_id: set() for cube_id in incident}
    for cubes in face_to_cubes.values():
        for left in cubes:
            adjacency[left].update(right for right in cubes if right != left)
    return adjacency


@dataclass(frozen=True)
class TubularDefect:
    core_line: LineDefect
    radius_lattice_steps: int
    tube_cube_cell_ids: Tuple[str, ...]
    tube_site_ids: Tuple[str, ...]
    tube_wall_site_ids: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.tubular_defect.v1"

    @property
    def strata(self) -> "DefectStrata":
        return DefectStrata(
            self.core_line.cube_cell_ids,
            self.tube_wall_site_ids,
            self.core_line.endpoint_cube_ids,
        )

    def __post_init__(self) -> None:
        if (
            isinstance(self.radius_lattice_steps, bool)
            or not isinstance(self.radius_lattice_steps, int)
            or self.radius_lattice_steps < 0
        ):
            raise ValueError("tube radius must be a nonnegative integer")
        if not set(self.core_line.cube_cell_ids).issubset(self.tube_cube_cell_ids):
            raise ValueError("tube cube window must contain the core line")
        if not self.tube_site_ids:
            raise ValueError("tube window must contain at least one Pauli site")
        if not set(self.tube_wall_site_ids).issubset(self.tube_site_ids):
            raise ValueError("tube wall sites must belong to the tube support window")

    @classmethod
    def around_line(
        cls,
        complex_: CubicalComplex,
        line: LineDefect,
        radius_lattice_steps: int = 0,
    ) -> "TubularDefect":
        _require_3d(complex_)
        if isinstance(radius_lattice_steps, bool) or not isinstance(
            radius_lattice_steps, int
        ) or radius_lattice_steps < 0:
            raise ValueError("tube radius must be a nonnegative integer")
        adjacency = _cube_adjacency(complex_)
        cubes = set(line.cube_cell_ids)
        frontier = set(cubes)
        for _step in range(radius_lattice_steps):
            frontier = {
                neighbor
                for cube_id in frontier
                for neighbor in adjacency[cube_id]
                if neighbor not in cubes
            }
            cubes.update(frontier)
        incident = _incident_plaquettes_by_cube(complex_)
        sites = {face_id for cube_id in cubes for face_id in incident[cube_id]}
        face_to_cubes = {}
        for cube_id, face_ids in incident.items():
            for face_id in face_ids:
                face_to_cubes.setdefault(face_id, []).append(cube_id)
        wall = {
            face_id
            for face_id in sites
            if any(cube_id not in cubes for cube_id in face_to_cubes[face_id])
            or len(face_to_cubes[face_id]) == 1
        }
        return cls(
            line,
            radius_lattice_steps,
            tuple(sorted(cubes)),
            tuple(sorted(sites)),
            tuple(sorted(wall)),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "core_line": self.core_line,
            "radius_lattice_steps": self.radius_lattice_steps,
            "schema": self.SCHEMA_ID,
            "strata": self.strata,
            "tube_cube_cell_ids": self.tube_cube_cell_ids,
            "tube_site_ids": self.tube_site_ids,
            "tube_wall_site_ids": self.tube_wall_site_ids,
        }


@dataclass(frozen=True)
class DefectStrata:
    line_core_cube_cell_ids: Tuple[str, ...]
    tube_wall_site_ids: Tuple[str, ...]
    endpoint_cube_cell_ids: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.cheshire_defect_strata.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "endpoint_cube_cell_ids": self.endpoint_cube_cell_ids,
            "line_core_cube_cell_ids": self.line_core_cube_cell_ids,
            "schema": self.SCHEMA_ID,
            "tube_wall_site_ids": self.tube_wall_site_ids,
        }


@dataclass(frozen=True)
class HamiltonianTerm:
    term_id: str
    family: str
    source_cell_ids: Tuple[str, ...]
    operator: PauliOperator

    SCHEMA_ID = "mobility_toolkit.hamiltonian_term.v1"

    def __post_init__(self) -> None:
        if not self.term_id or not self.family:
            raise ValueError("Hamiltonian term ID and family must be nonempty")
        if not isinstance(self.operator, PauliOperator):
            raise TypeError("Hamiltonian term operator must be a PauliOperator")
        sources = tuple(self.source_cell_ids)
        if any(not isinstance(cell_id, str) or not cell_id for cell_id in sources):
            raise ValueError("Hamiltonian source cell IDs must be nonempty strings")
        object.__setattr__(self, "source_cell_ids", sources)

    def to_canonical_dict(self) -> dict:
        return {
            "family": self.family,
            "operator": self.operator,
            "schema": self.SCHEMA_ID,
            "source_cell_ids": self.source_cell_ids,
            "term_id": self.term_id,
        }


def _bulk_term(check: CellularCheck) -> HamiltonianTerm:
    family = "bulk_charge" if check.pauli_kind == "x" else "bulk_flux"
    return HamiltonianTerm(
        f"bulk:{check.pauli_kind}:{check.cell_id}",
        family,
        (check.cell_id,),
        check.operator,
    )


@dataclass(frozen=True)
class SyndromeEntry:
    term_id: str
    phase_exponent: int
    phase_modulus: int

    SCHEMA_ID = "mobility_toolkit.syndrome_entry.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.term_id, str) or not self.term_id:
            raise ValueError("syndrome term ID must be a nonempty string")
        if (
            isinstance(self.phase_modulus, bool)
            or not isinstance(self.phase_modulus, int)
            or self.phase_modulus <= 1
        ):
            raise ValueError("syndrome phase modulus must be an integer greater than one")
        if isinstance(self.phase_exponent, bool) or not isinstance(
            self.phase_exponent, int
        ):
            raise TypeError("syndrome phase exponent must be an integer")
        object.__setattr__(
            self, "phase_exponent", self.phase_exponent % self.phase_modulus
        )

    @property
    def violated(self) -> bool:
        return self.phase_exponent % self.phase_modulus != 0

    def to_canonical_dict(self) -> dict:
        return {
            "phase_exponent": self.phase_exponent,
            "phase_modulus": self.phase_modulus,
            "schema": self.SCHEMA_ID,
            "term_id": self.term_id,
            "violated": self.violated,
        }


@dataclass(frozen=True)
class SyndromeReport:
    entries: Tuple[SyndromeEntry, ...]

    SCHEMA_ID = "mobility_toolkit.syndrome_report.v1"

    @property
    def violated_term_ids(self) -> Tuple[str, ...]:
        return tuple(entry.term_id for entry in self.entries if entry.violated)

    @property
    def is_zero(self) -> bool:
        return not self.violated_term_ids

    def to_canonical_dict(self) -> dict:
        return {
            "entries": self.entries,
            "is_zero": self.is_zero,
            "schema": self.SCHEMA_ID,
            "violated_term_ids": self.violated_term_ids,
        }


def pauli_syndrome(
    probe: PauliOperator, terms: Sequence[HamiltonianTerm]
) -> SyndromeReport:
    terms = tuple(terms)
    if any(term.operator.module != probe.module for term in terms):
        raise ValueError("syndrome terms and probe must belong to the same Pauli module")
    return SyndromeReport(
        tuple(
            SyndromeEntry(
                term.term_id,
                term.operator.projective_pairing(probe),
                probe.module.phase_modulus,
            )
            for term in terms
        )
    )


@dataclass(frozen=True)
class TerminationReport:
    probe_id: str
    excitation_family: str
    probe: PauliOperator
    bulk_syndrome: SyndromeReport
    defect_syndrome: SyndromeReport
    fixed_sector_syndrome: SyndromeReport
    absorbed_bulk_term_ids: Tuple[str, ...]
    residual_bulk_term_ids: Tuple[str, ...]
    defect_only_term_ids: Tuple[str, ...]
    terminates_on_defect: bool
    changes_fixed_sector: bool
    probe_in_defect_centralizer: bool
    probe_in_defect_stabilizer: bool
    conclusion_basis: str
    no_solution_certificate: Optional["FluxNonTerminationCertificate"] = None

    SCHEMA_ID = "mobility_toolkit.termination_report.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "absorbed_bulk_term_ids": self.absorbed_bulk_term_ids,
            "bulk_syndrome": self.bulk_syndrome,
            "changes_fixed_sector": self.changes_fixed_sector,
            "defect_only_term_ids": self.defect_only_term_ids,
            "defect_syndrome": self.defect_syndrome,
            "excitation_family": self.excitation_family,
            "fixed_sector_syndrome": self.fixed_sector_syndrome,
            "probe": self.probe,
            "probe_id": self.probe_id,
            "probe_in_defect_centralizer": self.probe_in_defect_centralizer,
            "probe_in_defect_stabilizer": self.probe_in_defect_stabilizer,
            "conclusion_basis": self.conclusion_basis,
            "no_solution_certificate": self.no_solution_certificate,
            "residual_bulk_term_ids": self.residual_bulk_term_ids,
            "schema": self.SCHEMA_ID,
            "terminates_on_defect": self.terminates_on_defect,
        }


@dataclass(frozen=True)
class FluxNonTerminationCertificate:
    target_edge_cell_ids: Tuple[str, ...]
    target_boundary_vertex_cell_ids: Tuple[str, ...]
    syndrome_map_rank: int
    augmented_rank: int
    boundary_squared_zero_verified: bool
    all_bulk_flux_checks_retained: bool
    no_solution: bool
    exactness: Exactness
    theorem_scope: str

    SCHEMA_ID = "mobility_toolkit.flux_nontermination_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.boundary_squared_zero_verified
            and self.all_bulk_flux_checks_retained
            and bool(self.target_boundary_vertex_cell_ids)
            and self.augmented_rank > self.syndrome_map_rank
            and self.no_solution
        )

    def to_canonical_dict(self) -> dict:
        return {
            "all_bulk_flux_checks_retained": self.all_bulk_flux_checks_retained,
            "augmented_rank": self.augmented_rank,
            "boundary_squared_zero_verified": self.boundary_squared_zero_verified,
            "exactness": self.exactness,
            "no_solution": self.no_solution,
            "schema": self.SCHEMA_ID,
            "syndrome_map_rank": self.syndrome_map_rank,
            "target_boundary_vertex_cell_ids": self.target_boundary_vertex_cell_ids,
            "target_edge_cell_ids": self.target_edge_cell_ids,
            "theorem_scope": self.theorem_scope,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class Eq8TransformationCertificate:
    defect_id: str
    original_charge_product: PauliOperator
    condensate_product: PauliOperator
    sector_operator: PauliOperator
    transformed_product: PauliOperator
    product_identity_verified: bool
    local_commutation_verified: bool
    construction_scope: str

    SCHEMA_ID = "mobility_toolkit.cheshire_eq8_certificate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "condensate_product": self.condensate_product,
            "construction_scope": self.construction_scope,
            "defect_id": self.defect_id,
            "local_commutation_verified": self.local_commutation_verified,
            "original_charge_product": self.original_charge_product,
            "product_identity_verified": self.product_identity_verified,
            "schema": self.SCHEMA_ID,
            "sector_operator": self.sector_operator,
            "transformed_product": self.transformed_product,
        }


@dataclass(frozen=True)
class EndpointAlgebraReport:
    endpoint_id: str
    cube_cell_id: str
    window_site_ids: Tuple[str, ...]
    local_algebra: DefectLocalAlgebra

    SCHEMA_ID = "mobility_toolkit.cheshire_endpoint_algebra.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "cube_cell_id": self.cube_cell_id,
            "endpoint_id": self.endpoint_id,
            "local_algebra": self.local_algebra,
            "schema": self.SCHEMA_ID,
            "window_site_ids": self.window_site_ids,
        }


@dataclass(frozen=True)
class CheshireDefectReport:
    line_defect: LineDefect
    tube: TubularDefect
    sector_term: HamiltonianTerm
    transformation_certificate: Eq8TransformationCertificate
    defect_local_algebra: DefectLocalAlgebra
    endpoint_reports: Tuple[EndpointAlgebraReport, ...]
    charge_termination: TerminationReport
    magnetic_termination: TerminationReport

    SCHEMA_ID = "mobility_toolkit.cheshire_defect_report.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "charge_termination": self.charge_termination,
            "defect_local_algebra": self.defect_local_algebra,
            "endpoint_reports": self.endpoint_reports,
            "line_defect": self.line_defect,
            "magnetic_termination": self.magnetic_termination,
            "schema": self.SCHEMA_ID,
            "sector_term": self.sector_term,
            "transformation_certificate": self.transformation_certificate,
            "tube": self.tube,
        }


@dataclass(frozen=True)
class RationalFactor:
    numerator: int
    denominator: int

    SCHEMA_ID = "mobility_toolkit.rational_factor.v1"

    def __post_init__(self) -> None:
        if (
            isinstance(self.numerator, bool)
            or not isinstance(self.numerator, int)
            or isinstance(self.denominator, bool)
            or not isinstance(self.denominator, int)
            or self.numerator < 1
            or self.denominator < 1
        ):
            raise ValueError("rational factor entries must be positive")
        divisor = math.gcd(self.numerator, self.denominator)
        object.__setattr__(self, "numerator", self.numerator // divisor)
        object.__setattr__(self, "denominator", self.denominator // divisor)

    def to_canonical_dict(self) -> dict:
        return {
            "denominator": self.denominator,
            "numerator": self.numerator,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PinnedCondensateEliminationCertificate:
    deleted_site_ids: Tuple[str, ...]
    direct_representation: str
    pinned_elimination_representation: str
    local_logical_invariants_match: bool
    fixed_sector_logical_invariants_match: bool
    local_codespace_dimension_matches: bool
    fixed_sector_codespace_dimension_matches: bool
    equivalence_scope: str

    SCHEMA_ID = "mobility_toolkit.pinned_condensate_elimination_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.local_logical_invariants_match
            and self.fixed_sector_logical_invariants_match
            and self.local_codespace_dimension_matches
            and self.fixed_sector_codespace_dimension_matches
        )

    def to_canonical_dict(self) -> dict:
        return {
            "deleted_site_ids": self.deleted_site_ids,
            "pinned_elimination_representation": self.pinned_elimination_representation,
            "direct_representation": self.direct_representation,
            "equivalence_scope": self.equivalence_scope,
            "fixed_sector_codespace_dimension_matches": self.fixed_sector_codespace_dimension_matches,
            "fixed_sector_logical_invariants_match": self.fixed_sector_logical_invariants_match,
            "local_codespace_dimension_matches": self.local_codespace_dimension_matches,
            "local_logical_invariants_match": self.local_logical_invariants_match,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class CheshireStaticAnalysis:
    cellular_code: CellularCode
    bulk_terms: Tuple[HamiltonianTerm, ...]
    local_terms: Tuple[HamiltonianTerm, ...]
    fixed_sector_terms: Tuple[HamiltonianTerm, ...]
    bulk_analysis: FiniteStabilizerAnalysis
    local_analysis: FiniteStabilizerAnalysis
    fixed_sector_analysis: FiniteStabilizerAnalysis
    local_pinned_elimination: PinnedSubsystemProjection
    fixed_sector_pinned_elimination: PinnedSubsystemProjection
    pinned_elimination_certificate: PinnedCondensateEliminationCertificate
    tubular_deleted_representation: TubularDeletedRepresentation
    defect_reports: Tuple[CheshireDefectReport, ...]
    local_gsd_factor: RationalFactor
    fixed_sector_gsd_factor: RationalFactor
    exactness: Exactness
    certificate_level: CertificateLevel
    theorem_scope: str
    assumptions: Tuple[str, ...]
    backend_provenance: BackendProvenance

    SCHEMA_ID = "mobility_toolkit.cheshire_static_analysis.v1"

    def __post_init__(self) -> None:
        assumptions = tuple(sorted(set(self.assumptions)))
        if not self.pinned_elimination_certificate.verified:
            raise ValueError("pinned-condensate elimination certificate is not verified")
        if not self.tubular_deleted_representation.certificate.verified:
            raise ValueError("line/tube representation certificate is not verified")
        if any(
            not report.transformation_certificate.product_identity_verified
            or not report.transformation_certificate.local_commutation_verified
            for report in self.defect_reports
        ):
            raise ValueError("one or more Cheshire construction checks are not verified")
        object.__setattr__(self, "assumptions", assumptions)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "backend_provenance": self.backend_provenance,
            "bulk_analysis": self.bulk_analysis,
            "bulk_terms": self.bulk_terms,
            "cellular_code": self.cellular_code,
            "certificate_level": self.certificate_level,
            "defect_reports": self.defect_reports,
            "exactness": self.exactness,
            "fixed_sector_analysis": self.fixed_sector_analysis,
            "fixed_sector_gsd_factor": self.fixed_sector_gsd_factor,
            "fixed_sector_terms": self.fixed_sector_terms,
            "local_analysis": self.local_analysis,
            "local_pinned_elimination": self.local_pinned_elimination,
            "fixed_sector_pinned_elimination": self.fixed_sector_pinned_elimination,
            "pinned_elimination_certificate": self.pinned_elimination_certificate,
            "tubular_deleted_representation": self.tubular_deleted_representation,
            "local_gsd_factor": self.local_gsd_factor,
            "local_terms": self.local_terms,
            "schema": self.SCHEMA_ID,
            "theorem_scope": self.theorem_scope,
        }


def _operator_product(operators: Iterable[PauliOperator], identity: PauliOperator) -> PauliOperator:
    result = identity
    for operator in operators:
        result = result * operator
    return result


def _normalize_line(value: object) -> LineDefect:
    if isinstance(value, LineDefect):
        return value
    if isinstance(value, (OpenSegment, ClosedLoop)):
        return value.line
    raise TypeError("Cheshire defects must be LineDefect, OpenSegment, or ClosedLoop")


def _interface_plaquette(complex_: CubicalComplex, line: LineDefect) -> str:
    incident = _incident_plaquettes_by_cube(complex_)
    path = set(line.cube_cell_ids)
    face_to_cubes = {}
    for cube_id, faces in incident.items():
        for face_id in faces:
            face_to_cubes.setdefault(face_id, []).append(cube_id)
    candidates = []
    fallback = []
    condensates = set(line.condensate_plaquette_ids)
    for face_id, cubes in face_to_cubes.items():
        if face_id in condensates:
            continue
        path_count = sum(cube_id in path for cube_id in cubes)
        outside_count = sum(cube_id not in path for cube_id in cubes)
        if path_count == 1 and outside_count >= 1:
            candidates.append(face_id)
        elif path_count == 1:
            fallback.append(face_id)
    if candidates:
        return sorted(candidates)[0]
    if fallback:
        return sorted(fallback)[0]
    return line.condensate_plaquette_ids[0]


def _termination_report(
    probe_id: str,
    excitation_family: str,
    probe: PauliOperator,
    bulk_terms: Tuple[HamiltonianTerm, ...],
    local_terms: Tuple[HamiltonianTerm, ...],
    sector_terms: Tuple[HamiltonianTerm, ...],
    local_analysis: FiniteStabilizerAnalysis,
    backend: FiniteIntegerBackend,
    conclusion_basis: str = "positive_witness",
    no_solution_certificate: Optional[FluxNonTerminationCertificate] = None,
) -> TerminationReport:
    bulk_syndrome = pauli_syndrome(probe, bulk_terms)
    local_syndrome = pauli_syndrome(probe, local_terms)
    sector_syndrome = pauli_syndrome(probe, sector_terms)
    bulk_ids = set(bulk_syndrome.violated_term_ids)
    local_ids = set(local_syndrome.violated_term_ids)
    local_term_ids = {term.term_id for term in local_terms}
    absorbed = tuple(sorted(term_id for term_id in bulk_ids if term_id not in local_term_ids))
    residual = tuple(sorted(term_id for term_id in bulk_ids if term_id in local_ids))
    defect_only = tuple(sorted(term_id for term_id in local_ids if term_id not in bulk_ids))
    bulk_families = {term.term_id: term.family for term in bulk_terms}
    terminates = bool(absorbed) and not defect_only and all(
        bulk_families[term_id] == excitation_family for term_id in absorbed
    )
    if no_solution_certificate is not None:
        if not no_solution_certificate.verified:
            raise ArithmeticError("flux no-solution certificate did not verify")
        terminates = False
    vector = local_analysis.coordinates.vector(probe)
    in_centralizer = local_analysis.centralizer.contains(vector, backend)
    in_stabilizer = local_analysis.stabilizer.contains(vector, backend)
    if in_centralizer != local_syndrome.is_zero:
        raise ArithmeticError("syndrome and centralizer membership disagree")
    sector_only = set(sector_syndrome.violated_term_ids) - local_ids
    return TerminationReport(
        probe_id,
        excitation_family,
        probe,
        bulk_syndrome,
        local_syndrome,
        sector_syndrome,
        absorbed,
        residual,
        defect_only,
        terminates,
        bool(sector_only),
        in_centralizer,
        in_stabilizer,
        conclusion_basis,
        no_solution_certificate,
    )


def _gf2_rank(rows: Sequence[Sequence[int]]) -> int:
    work = [sum((value & 1) << column for column, value in enumerate(row)) for row in rows]
    rank = 0
    pivot = 0
    width = max((len(row) for row in rows), default=0)
    while pivot < width:
        candidate = next((index for index in range(rank, len(work)) if work[index] & (1 << pivot)), None)
        if candidate is None:
            pivot += 1
            continue
        work[rank], work[candidate] = work[candidate], work[rank]
        for index in range(len(work)):
            if index != rank and work[index] & (1 << pivot):
                work[index] ^= work[rank]
        rank += 1
        pivot += 1
    return rank


def _flux_nontermination_certificate(
    complex_: CubicalComplex,
    interface_plaquette_id: str,
    bulk_terms: Tuple[HamiltonianTerm, ...],
    local_terms: Tuple[HamiltonianTerm, ...],
) -> FluxNonTerminationCertificate:
    chain = complex_.chain_complex
    edge_ids = chain.cell_ids_by_dimension[1]
    face_ids = chain.cell_ids_by_dimension[2]
    vertex_ids = chain.cell_ids_by_dimension[0]
    d2_rows = chain.boundary_maps[2].to_rows()
    d1_rows = chain.boundary_maps[1].to_rows()
    face_column = face_ids.index(interface_plaquette_id)
    adjacent_edges = tuple(
        edge_ids[row] for row in range(len(edge_ids)) if d2_rows[row][face_column] % 2
    )
    target_edge = next(
        (
            edge_id
            for edge_id in adjacent_edges
            if any(d1_rows[row][edge_ids.index(edge_id)] % 2 for row in range(len(vertex_ids)))
        ),
        None,
    )
    if target_edge is None:
        raise ValueError("could not choose a non-cycle open-flux target near the defect")
    target_index = edge_ids.index(target_edge)
    boundary_vertices = tuple(
        vertex_ids[row]
        for row in range(len(vertex_ids))
        if d1_rows[row][target_index] % 2
    )
    target = tuple(1 if index == target_index else 0 for index in range(len(edge_ids)))
    map_rows = tuple(tuple(value % 2 for value in row) for row in d2_rows)
    augmented = tuple(row + (target[index],) for index, row in enumerate(map_rows))
    map_rank = _gf2_rank(map_rows)
    augmented_rank = _gf2_rank(augmented)
    bulk_flux_ids = {term.term_id for term in bulk_terms if term.family == "bulk_flux"}
    local_ids = {term.term_id for term in local_terms}
    certificate = FluxNonTerminationCertificate(
        (target_edge,),
        boundary_vertices,
        map_rank,
        augmented_rank,
        not chain.boundary_maps[1].matmul(chain.boundary_maps[2]).entries,
        bulk_flux_ids.issubset(local_ids),
        augmented_rank > map_rank,
        Exactness.CERTIFIED_EXACT,
        "Exact for the complete finite plaquette-Pauli syndrome map: retained edge-flux "
        "checks force every magnetic syndrome to be a cellular 1-cycle.",
    )
    if not certificate.verified:
        raise ArithmeticError("failed to certify magnetic nontermination")
    return certificate


def analyze_toric_cheshire(
    complex_: CubicalComplex,
    defects: Sequence[object],
    backend: FiniteIntegerBackend,
    tube_radius_lattice_steps: int = 0,
) -> CheshireStaticAnalysis:
    """Analyze user-specified static Cheshire lines in the 3+1D Z2 toric code."""

    _require_3d(complex_)
    lines = tuple(_normalize_line(defect) for defect in defects)
    if not lines:
        raise ValueError("at least one Cheshire line must be supplied")
    if len({line.defect_id for line in lines}) != len(lines):
        raise ValueError("Cheshire defect IDs must be unique")
    incident_geometry = _incident_plaquettes_by_cube(complex_)
    for line in lines:
        missing_path_cubes = tuple(
            cube_id for cube_id in line.cube_cell_ids if cube_id not in incident_geometry
        )
        if missing_path_cubes:
            raise ValueError(
                "line path cubes are absent from the supplied complex: "
                + ", ".join(missing_path_cubes)
            )
        pairs = list(zip(line.cube_cell_ids, line.cube_cell_ids[1:]))
        if line.topology == LineTopology.CLOSED_LOOP:
            pairs.append((line.cube_cell_ids[-1], line.cube_cell_ids[0]))
        expected_plaquettes = tuple(
            _shared_plaquette(left, right, incident_geometry)
            for left, right in pairs
        )
        if expected_plaquettes != line.condensate_plaquette_ids:
            raise ValueError(
                "condensate plaquettes do not match the ordered line links for defect "
                + line.defect_id
            )
    all_cubes = tuple(cube for line in lines for cube in line.cube_cell_ids)
    all_faces = tuple(face for line in lines for face in line.condensate_plaquette_ids)
    if len(set(all_cubes)) != len(all_cubes) or len(set(all_faces)) != len(all_faces):
        raise ValueError("Cheshire line components must have disjoint cores and condensates")

    cellular = cellular_stabilizer_code(
        complex_.chain_complex,
        2,
        2,
        convention=CellularPauliConvention.FOURIER_DUAL,
    )
    module = cellular.code.pauli_module
    bulk_terms = tuple(_bulk_term(check) for check in cellular.check_records)
    bulk_analysis = analyze_finite_stabilizer(
        module, tuple(term.operator for term in bulk_terms), backend
    )
    charges = {
        check.cell_id: check.operator
        for check in cellular.check_records
        if check.pauli_kind == "x"
    }
    missing_cubes = tuple(cube_id for cube_id in all_cubes if cube_id not in charges)
    known_sites = {system.site_id for system in module.local_systems}
    missing_faces = tuple(face_id for face_id in all_faces if face_id not in known_sites)
    if missing_cubes or missing_faces:
        raise ValueError(
            "defect cells are not present in the cellular code: "
            + ", ".join(missing_cubes + missing_faces)
        )

    removed = set(all_cubes)
    local_terms = [
        term
        for term in bulk_terms
        if not (term.family == "bulk_charge" and term.source_cell_ids[0] in removed)
    ]
    condensate_terms = {}
    for line in lines:
        for face_id in line.condensate_plaquette_ids:
            operator = module.operator((LocalPauliTerm.cyclic(face_id, z=1),))
            term = HamiltonianTerm(
                f"condensate:z:{line.defect_id}:{face_id}",
                "cheshire_charge_condensate",
                (face_id,),
                operator,
            )
            local_terms.append(term)
            condensate_terms[(line.defect_id, face_id)] = term
    local_terms_tuple = tuple(local_terms)
    local_analysis = analyze_finite_stabilizer(
        module, tuple(term.operator for term in local_terms_tuple), backend
    )

    sector_terms = []
    certificates = {}
    for line in lines:
        charge_product = _operator_product(
            (charges[cube_id] for cube_id in line.cube_cell_ids), module.identity()
        )
        condensate_product = _operator_product(
            (
                condensate_terms[(line.defect_id, face_id)].operator
                for face_id in line.condensate_plaquette_ids
            ),
            module.identity(),
        )
        sector_operator = charge_product * condensate_product
        sector_term = HamiltonianTerm(
            f"sector:q-gamma:{line.defect_id}",
            "cheshire_total_charge_sector",
            tuple(line.cube_cell_ids) + tuple(line.condensate_plaquette_ids),
            sector_operator,
        )
        transformed_product = sector_operator * condensate_product
        product_verified = transformed_product == charge_product
        commutation_verified = all(
            sector_operator.commutes_with(term.operator) for term in local_terms_tuple
        )
        if not product_verified or not commutation_verified:
            raise ArithmeticError("Cheshire stabilizer transformation certificate failed")
        if sector_operator.scalar_obstruction:
            raise ArithmeticError("Cheshire sector operator has a phase-lift obstruction")
        scope = (
            "Eq. (8) open-segment generator replacement"
            if line.topology == LineTopology.OPEN_SEGMENT
            else "static closed-loop extension of the Eq. (8) local condensate pattern"
        )
        certificates[line.defect_id] = Eq8TransformationCertificate(
            line.defect_id,
            charge_product,
            condensate_product,
            sector_operator,
            transformed_product,
            product_verified,
            commutation_verified,
            scope,
        )
        sector_terms.append(sector_term)

    fixed_terms = local_terms_tuple + tuple(sector_terms)
    fixed_analysis = analyze_finite_stabilizer(
        module, tuple(term.operator for term in fixed_terms), backend
    )
    pin_term_ids = tuple(
        condensate_terms[(line.defect_id, face_id)].term_id
        for line in lines
        for face_id in line.condensate_plaquette_ids
    )
    local_projection = project_pinned_z_subsystems(
        module,
        tuple((term.term_id, term.operator) for term in local_terms_tuple),
        all_faces,
        pin_term_ids,
        backend,
        local_analysis,
    )
    fixed_projection = project_pinned_z_subsystems(
        module,
        tuple((term.term_id, term.operator) for term in fixed_terms),
        all_faces,
        pin_term_ids,
        backend,
        fixed_analysis,
    )
    pinned_elimination_certificate = PinnedCondensateEliminationCertificate(
        tuple(sorted(all_faces)),
        "direct line-local stabilizer rewrite with explicit single-plaquette Z pins",
        "exact elimination of the explicitly pinned condensate plaquettes in the Z=+1 sector",
        local_analysis.logical_invariant_factors
        == local_projection.projected_analysis.logical_invariant_factors,
        fixed_analysis.logical_invariant_factors
        == fixed_projection.projected_analysis.logical_invariant_factors,
        local_analysis.codespace_dimension
        == local_projection.projected_analysis.codespace_dimension,
        fixed_analysis.codespace_dimension
        == fixed_projection.projected_analysis.codespace_dimension,
        "Exact stabilizer isomorphism for elimination of explicitly pinned condensate "
        "plaquettes only; this is not the separate tubular-neighborhood representation, "
        "an arbitrary-radius tube shrinking, or a phase-equivalence claim.",
    )
    if not pinned_elimination_certificate.verified:
        raise ArithmeticError("direct code and pinned-condensate elimination disagree")
    tubular_representation = compile_deleted_tube_representation(
        complex_, lines, local_projection, fixed_projection
    )
    sector_by_defect = dict(zip((line.defect_id for line in lines), sector_terms))
    incident = incident_geometry
    defect_reports = []
    for line in lines:
        tube = TubularDefect.around_line(
            complex_, line, tube_radius_lattice_steps
        )
        local_algebra = defect_local_algebra(
            local_analysis, tube.tube_site_ids, backend
        )
        endpoints = tuple(
            EndpointAlgebraReport(
                f"{line.defect_id}:endpoint:{index}",
                cube_id,
                tuple(sorted(incident[cube_id])),
                defect_local_algebra(local_analysis, incident[cube_id], backend),
            )
            for index, cube_id in enumerate(line.endpoint_cube_ids)
        )
        probe_face = _interface_plaquette(complex_, line)
        charge_probe = module.operator((LocalPauliTerm.cyclic(probe_face, z=1),))
        magnetic_probe = module.operator((LocalPauliTerm.cyclic(probe_face, x=1),))
        flux_certificate = _flux_nontermination_certificate(
            complex_, probe_face, bulk_terms, local_terms_tuple
        )
        charge_termination = _termination_report(
            f"{line.defect_id}:charge:{probe_face}",
            "bulk_charge",
            charge_probe,
            bulk_terms,
            local_terms_tuple,
            fixed_terms,
            local_analysis,
            backend,
        )
        magnetic_termination = _termination_report(
            f"{line.defect_id}:magnetic:{probe_face}",
            "bulk_flux",
            magnetic_probe,
            bulk_terms,
            local_terms_tuple,
            fixed_terms,
            local_analysis,
            backend,
            "exact_no_solution",
            flux_certificate,
        )
        defect_reports.append(
            CheshireDefectReport(
                line,
                tube,
                sector_by_defect[line.defect_id],
                certificates[line.defect_id],
                local_algebra,
                endpoints,
                charge_termination,
                magnetic_termination,
            )
        )

    provenance = BackendProvenance(
        getattr(backend, "name", backend.__class__.__name__),
        "certified finite stabilizer and integer preimage-lattice intersections",
        getattr(backend, "version", ""),
        (("tube_radius_lattice_steps", tube_radius_lattice_steps),),
    )
    return CheshireStaticAnalysis(
        cellular,
        bulk_terms,
        local_terms_tuple,
        fixed_terms,
        bulk_analysis,
        local_analysis,
        fixed_analysis,
        local_projection,
        fixed_projection,
        pinned_elimination_certificate,
        tubular_representation,
        tuple(defect_reports),
        RationalFactor(local_analysis.codespace_dimension, bulk_analysis.codespace_dimension),
        RationalFactor(fixed_analysis.codespace_dimension, bulk_analysis.codespace_dimension),
        Exactness.CERTIFIED_EXACT,
        CertificateLevel.STANDARD,
        STATIC_THEOREM_SCOPE,
        (
            "3+1D Z2 toric code on plaquette qubits",
            "user-specified static Cheshire condensation data",
            REFERENCE,
        ),
        provenance,
    )


@dataclass(frozen=True)
class CheshireScalingSample:
    label: str
    path_cube_count: int
    condensate_count: int
    tube_radius_lattice_steps: int
    tube_site_count: int
    bulk_codespace_dimension: int
    local_codespace_dimension: int
    fixed_sector_codespace_dimension: int
    defect_local_invariant_factors: Tuple[int, ...]
    defect_local_radical_invariant_factors: Tuple[int, ...]
    exactness: Exactness

    SCHEMA_ID = "mobility_toolkit.cheshire_scaling_sample.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_codespace_dimension": self.bulk_codespace_dimension,
            "condensate_count": self.condensate_count,
            "defect_local_invariant_factors": self.defect_local_invariant_factors,
            "defect_local_radical_invariant_factors": self.defect_local_radical_invariant_factors,
            "exactness": self.exactness,
            "fixed_sector_codespace_dimension": self.fixed_sector_codespace_dimension,
            "label": self.label,
            "local_codespace_dimension": self.local_codespace_dimension,
            "path_cube_count": self.path_cube_count,
            "schema": self.SCHEMA_ID,
            "tube_radius_lattice_steps": self.tube_radius_lattice_steps,
            "tube_site_count": self.tube_site_count,
        }


def cheshire_scaling_sample(
    label: str, analysis: CheshireStaticAnalysis, defect_index: int = 0
) -> CheshireScalingSample:
    report = analysis.defect_reports[defect_index]
    return CheshireScalingSample(
        label,
        len(report.line_defect.cube_cell_ids),
        len(report.line_defect.condensate_plaquette_ids),
        report.tube.radius_lattice_steps,
        len(report.tube.tube_site_ids),
        analysis.bulk_analysis.codespace_dimension,
        analysis.local_analysis.codespace_dimension,
        analysis.fixed_sector_analysis.codespace_dimension,
        report.defect_local_algebra.invariant_factors,
        report.defect_local_algebra.radical_invariant_factors,
        analysis.exactness,
    )


__all__ = [
    "CheshireDefectReport",
    "CheshireScalingSample",
    "CheshireStaticAnalysis",
    "PinnedCondensateEliminationCertificate",
    "ClosedLoop",
    "EndpointAlgebraReport",
    "Eq8TransformationCertificate",
    "HamiltonianTerm",
    "DefectStrata",
    "FluxNonTerminationCertificate",
    "LineDefect",
    "LineTopology",
    "OpenSegment",
    "RationalFactor",
    "SyndromeEntry",
    "SyndromeReport",
    "TerminationReport",
    "TubularDefect",
    "analyze_toric_cheshire",
    "cheshire_scaling_sample",
    "pauli_syndrome",
]
