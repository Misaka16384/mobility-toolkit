"""Exact finite static fusion candidates for supplied Cheshire defects.

The construction in this module compares two explicit finite stabilizer
Hamiltonians.  It does not infer a finite-depth circuit, a thermodynamic fusion
rule, or a phase equivalence from the finite comparison.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core import CertificateLevel, Exactness, canonical_json
from mobility_toolkit.core.codes import StabilizerCodeSpec
from mobility_toolkit.defects.cheshire import (
    CheshireStaticAnalysis,
    ClosedLoop,
    HamiltonianTerm,
    LineDefect,
    LineTopology,
    OpenSegment,
    RationalFactor,
    analyze_toric_cheshire,
)
from mobility_toolkit.defects.local_algebra import DefectLocalAlgebra
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.geometry.cell_complex import CubicalComplex


STATIC_FUSION_SCOPE = (
    "Certified exact only as a replayable comparison of the supplied before/after "
    "finite 3+1D Z2 toric-code stabilizer Hamiltonians and finite support windows. "
    "No finite-depth fusion circuit, thermodynamic fusion rule, tube-shrinking "
    "equivalence, or superselection-sector completeness is claimed."
)


def _digest(value: object) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _normalize_defect(value: object) -> LineDefect:
    if isinstance(value, LineDefect):
        return value
    if isinstance(value, (OpenSegment, ClosedLoop)):
        return value.line
    raise TypeError("fusion defects must be LineDefect, OpenSegment, or ClosedLoop")


class NetworkNodeKind(str, Enum):
    ENDPOINT = "endpoint"
    INTERFACE = "interface"
    JUNCTION = "junction"


@dataclass(frozen=True)
class EndpointBinding:
    defect_id: str
    cube_cell_id: str

    SCHEMA_ID = "mobility_toolkit.cheshire_network_endpoint_binding.v1"

    def __post_init__(self) -> None:
        if not self.defect_id or not self.cube_cell_id:
            raise ValueError("endpoint binding IDs must be nonempty")

    def to_canonical_dict(self) -> dict:
        return {
            "cube_cell_id": self.cube_cell_id,
            "defect_id": self.defect_id,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class CheshireNetworkNode:
    node_id: str
    kind: NetworkNodeKind
    stratum_cell_ids: Tuple[str, ...]
    endpoint_bindings: Tuple[EndpointBinding, ...]

    SCHEMA_ID = "mobility_toolkit.cheshire_network_node.v1"

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("network node ID must be nonempty")
        if not isinstance(self.kind, NetworkNodeKind):
            raise TypeError("network node kind must be explicit")
        cells = tuple(sorted(set(self.stratum_cell_ids)))
        bindings = tuple(
            sorted(
                tuple(self.endpoint_bindings),
                key=lambda item: (item.defect_id, item.cube_cell_id),
            )
        )
        if len(bindings) != len(set(bindings)):
            raise ValueError("endpoint bindings must be unique")
        if not set(item.cube_cell_id for item in bindings).issubset(cells):
            raise ValueError("node stratum must contain every bound endpoint cube")
        if self.kind == NetworkNodeKind.ENDPOINT and len(bindings) != 1:
            raise ValueError("an endpoint node must bind exactly one endpoint")
        if self.kind == NetworkNodeKind.INTERFACE and len(bindings) != 2:
            raise ValueError("an interface node must bind exactly two endpoints")
        if self.kind == NetworkNodeKind.JUNCTION and len(bindings) < 3:
            raise ValueError("a junction node must bind at least three endpoints")
        object.__setattr__(self, "stratum_cell_ids", cells)
        object.__setattr__(self, "endpoint_bindings", bindings)

    def to_canonical_dict(self) -> dict:
        return {
            "endpoint_bindings": self.endpoint_bindings,
            "kind": self.kind,
            "node_id": self.node_id,
            "schema": self.SCHEMA_ID,
            "stratum_cell_ids": self.stratum_cell_ids,
        }


@dataclass(frozen=True)
class CheshireNetworkEdge:
    edge_id: str
    defect_id: str
    topology: LineTopology
    incident_node_ids: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.cheshire_network_edge.v1"

    def __post_init__(self) -> None:
        if not self.edge_id or not self.defect_id:
            raise ValueError("network edge IDs must be nonempty")
        if not isinstance(self.topology, LineTopology):
            raise TypeError("network edge topology must be explicit")
        nodes = tuple(self.incident_node_ids)
        expected = 2 if self.topology == LineTopology.OPEN_SEGMENT else 0
        if len(nodes) != expected or len(set(nodes)) != len(nodes):
            raise ValueError(
                f"{self.topology.value} edge requires {expected} distinct incident nodes"
            )
        object.__setattr__(self, "incident_node_ids", nodes)

    def to_canonical_dict(self) -> dict:
        return {
            "defect_id": self.defect_id,
            "edge_id": self.edge_id,
            "incident_node_ids": self.incident_node_ids,
            "schema": self.SCHEMA_ID,
            "topology": self.topology,
        }


@dataclass(frozen=True)
class CheshireDefectNetwork:
    nodes: Tuple[CheshireNetworkNode, ...]
    edges: Tuple[CheshireNetworkEdge, ...]
    provenance: str

    SCHEMA_ID = "mobility_toolkit.cheshire_defect_network.v1"

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        if not self.provenance:
            raise ValueError("network provenance must be nonempty")
        if len({item.node_id for item in nodes}) != len(nodes):
            raise ValueError("network node IDs must be unique")
        if len({item.edge_id for item in edges}) != len(edges):
            raise ValueError("network edge IDs must be unique")
        if len({item.defect_id for item in edges}) != len(edges):
            raise ValueError("each defect must occur on exactly one network edge")
        known_nodes = {item.node_id for item in nodes}
        unknown = {
            node_id
            for edge in edges
            for node_id in edge.incident_node_ids
            if node_id not in known_nodes
        }
        if unknown:
            raise ValueError("network edges reference unknown nodes: " + ", ".join(sorted(unknown)))
        used = {node_id for edge in edges for node_id in edge.incident_node_ids}
        if used != known_nodes:
            raise ValueError("network contains unreferenced nodes")
        object.__setattr__(self, "nodes", tuple(sorted(nodes, key=lambda item: item.node_id)))
        object.__setattr__(self, "edges", tuple(sorted(edges, key=lambda item: item.edge_id)))

    @classmethod
    def from_defects(
        cls, defects: Sequence[object], provenance: str = "canonical component network"
    ) -> "CheshireDefectNetwork":
        lines = tuple(_normalize_defect(item) for item in defects)
        nodes = []
        edges = []
        for line in lines:
            node_ids = []
            for index, cube_id in enumerate(line.endpoint_cube_ids):
                node_id = f"{line.defect_id}:endpoint:{index}"
                nodes.append(
                    CheshireNetworkNode(
                        node_id,
                        NetworkNodeKind.ENDPOINT,
                        (cube_id,),
                        (EndpointBinding(line.defect_id, cube_id),),
                    )
                )
                node_ids.append(node_id)
            edges.append(
                CheshireNetworkEdge(
                    f"edge:{line.defect_id}",
                    line.defect_id,
                    line.topology,
                    tuple(node_ids),
                )
            )
        network = cls(tuple(nodes), tuple(edges), provenance)
        network.validate_against(lines)
        return network

    def validate_against(self, defects: Sequence[object]) -> None:
        lines = tuple(_normalize_defect(item) for item in defects)
        by_id = {line.defect_id: line for line in lines}
        if len(by_id) != len(lines):
            raise ValueError("defect IDs must be unique")
        if set(by_id) != {edge.defect_id for edge in self.edges}:
            raise ValueError("network edges do not exactly cover supplied defects")
        node_by_id = {node.node_id: node for node in self.nodes}
        expected_bindings = {
            EndpointBinding(line.defect_id, cube_id)
            for line in lines
            for cube_id in line.endpoint_cube_ids
        }
        observed_bindings = {
            binding for node in self.nodes for binding in node.endpoint_bindings
        }
        if observed_bindings != expected_bindings:
            raise ValueError("network endpoint bindings do not exactly cover line endpoints")
        for edge in self.edges:
            line = by_id[edge.defect_id]
            if edge.topology != line.topology:
                raise ValueError("network edge topology disagrees with line defect")
            bound = {
                binding.cube_cell_id
                for node_id in edge.incident_node_ids
                for binding in node_by_id[node_id].endpoint_bindings
                if binding.defect_id == line.defect_id
            }
            if bound != set(line.endpoint_cube_ids):
                raise ValueError("edge incidences do not cover its physical endpoints")

    @property
    def has_junctions(self) -> bool:
        return any(node.kind == NetworkNodeKind.JUNCTION for node in self.nodes)

    def to_canonical_dict(self) -> dict:
        return {
            "edges": self.edges,
            "has_junctions": self.has_junctions,
            "nodes": self.nodes,
            "provenance": self.provenance,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FusionStratumProvenance:
    side: str
    defect_id: str
    topology: LineTopology
    core_cube_cell_ids: Tuple[str, ...]
    condensate_plaquette_ids: Tuple[str, ...]
    endpoint_cube_cell_ids: Tuple[str, ...]
    source: str

    SCHEMA_ID = "mobility_toolkit.cheshire_fusion_stratum_provenance.v1"

    @property
    def covered_cell_ids(self) -> Tuple[str, ...]:
        return tuple(
            sorted(
                set(self.core_cube_cell_ids)
                | set(self.condensate_plaquette_ids)
                | set(self.endpoint_cube_cell_ids)
            )
        )

    def to_canonical_dict(self) -> dict:
        return {
            "condensate_plaquette_ids": self.condensate_plaquette_ids,
            "core_cube_cell_ids": self.core_cube_cell_ids,
            "covered_cell_ids": self.covered_cell_ids,
            "defect_id": self.defect_id,
            "endpoint_cube_cell_ids": self.endpoint_cube_cell_ids,
            "schema": self.SCHEMA_ID,
            "side": self.side,
            "source": self.source,
            "topology": self.topology,
        }


def _strata(side: str, lines: Sequence[LineDefect]) -> Tuple[FusionStratumProvenance, ...]:
    return tuple(
        FusionStratumProvenance(
            side,
            line.defect_id,
            line.topology,
            line.cube_cell_ids,
            line.condensate_plaquette_ids,
            line.endpoint_cube_ids,
            "Phase-4 Cheshire line input and incidence-validated static report",
        )
        for line in lines
    )


def _term_key(term: HamiltonianTerm) -> str:
    return _digest(
        {
            "family": term.family,
            "operator": term.operator,
            "source_cell_ids": term.source_cell_ids,
        }
    )


@dataclass(frozen=True)
class StaticHamiltonianDelta:
    removed_term_hashes: Tuple[str, ...]
    added_term_hashes: Tuple[str, ...]
    removed_term_ids: Tuple[str, ...]
    added_term_ids: Tuple[str, ...]
    changed_source_cell_ids: Tuple[str, ...]
    stratum_coverage_verified: bool

    SCHEMA_ID = "mobility_toolkit.cheshire_static_hamiltonian_delta.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "added_term_hashes": self.added_term_hashes,
            "added_term_ids": self.added_term_ids,
            "changed_source_cell_ids": self.changed_source_cell_ids,
            "removed_term_hashes": self.removed_term_hashes,
            "removed_term_ids": self.removed_term_ids,
            "schema": self.SCHEMA_ID,
            "stratum_coverage_verified": self.stratum_coverage_verified,
        }


def _hamiltonian_delta(
    before: Sequence[HamiltonianTerm],
    after: Sequence[HamiltonianTerm],
    provenance: Sequence[FusionStratumProvenance],
) -> StaticHamiltonianDelta:
    before_by_key = {}
    after_by_key = {}
    for term in before:
        before_by_key.setdefault(_term_key(term), []).append(term)
    for term in after:
        after_by_key.setdefault(_term_key(term), []).append(term)
    before_counts = Counter({key: len(value) for key, value in before_by_key.items()})
    after_counts = Counter({key: len(value) for key, value in after_by_key.items()})
    removed_hashes = tuple(sorted((before_counts - after_counts).elements()))
    added_hashes = tuple(sorted((after_counts - before_counts).elements()))
    removed_terms = tuple(
        term
        for key, count in Counter(removed_hashes).items()
        for term in before_by_key[key][:count]
    )
    added_terms = tuple(
        term
        for key, count in Counter(added_hashes).items()
        for term in after_by_key[key][:count]
    )
    changed_sources = tuple(
        sorted(
            {
                cell_id
                for term in removed_terms + added_terms
                for cell_id in term.source_cell_ids
            }
        )
    )
    covered = {
        cell_id for item in provenance for cell_id in item.covered_cell_ids
    }
    coverage_verified = set(changed_sources).issubset(covered)
    return StaticHamiltonianDelta(
        removed_hashes,
        added_hashes,
        tuple(sorted(term.term_id for term in removed_terms)),
        tuple(sorted(term.term_id for term in added_terms)),
        changed_sources,
        coverage_verified,
    )


@dataclass(frozen=True)
class FiniteFusionLogicalCounting:
    before_component_count: int
    after_component_count: int
    before_local_codespace_dimension: int
    after_local_codespace_dimension: int
    local_codespace_ratio_after_over_before: RationalFactor
    before_fixed_sector_codespace_dimension: int
    after_fixed_sector_codespace_dimension: int
    fixed_sector_ratio_after_over_before: RationalFactor
    before_local_logical_invariant_factors: Tuple[int, ...]
    after_local_logical_invariant_factors: Tuple[int, ...]
    before_fixed_logical_invariant_factors: Tuple[int, ...]
    after_fixed_logical_invariant_factors: Tuple[int, ...]
    component_only_predicted_ratio: RationalFactor
    component_only_hypothesis_matches: bool

    SCHEMA_ID = "mobility_toolkit.cheshire_finite_fusion_logical_counting.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "after_component_count": self.after_component_count,
            "after_fixed_logical_invariant_factors": self.after_fixed_logical_invariant_factors,
            "after_fixed_sector_codespace_dimension": self.after_fixed_sector_codespace_dimension,
            "after_local_codespace_dimension": self.after_local_codespace_dimension,
            "after_local_logical_invariant_factors": self.after_local_logical_invariant_factors,
            "before_component_count": self.before_component_count,
            "before_fixed_logical_invariant_factors": self.before_fixed_logical_invariant_factors,
            "before_fixed_sector_codespace_dimension": self.before_fixed_sector_codespace_dimension,
            "before_local_codespace_dimension": self.before_local_codespace_dimension,
            "before_local_logical_invariant_factors": self.before_local_logical_invariant_factors,
            "component_only_hypothesis_matches": self.component_only_hypothesis_matches,
            "component_only_predicted_ratio": self.component_only_predicted_ratio,
            "fixed_sector_ratio_after_over_before": self.fixed_sector_ratio_after_over_before,
            "local_codespace_ratio_after_over_before": self.local_codespace_ratio_after_over_before,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class DefectFusionAlgebraData:
    side: str
    defect_id: str
    topology: LineTopology
    defect_local_algebra: DefectLocalAlgebra
    endpoint_local_algebras: Tuple[DefectLocalAlgebra, ...]
    charge_terminates_on_defect: bool
    charge_changes_fixed_sector: bool
    magnetic_terminates_on_defect: bool
    magnetic_conclusion_basis: str

    SCHEMA_ID = "mobility_toolkit.cheshire_defect_fusion_algebra_data.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "charge_changes_fixed_sector": self.charge_changes_fixed_sector,
            "charge_terminates_on_defect": self.charge_terminates_on_defect,
            "defect_id": self.defect_id,
            "defect_local_algebra": self.defect_local_algebra,
            "endpoint_local_algebras": self.endpoint_local_algebras,
            "magnetic_conclusion_basis": self.magnetic_conclusion_basis,
            "magnetic_terminates_on_defect": self.magnetic_terminates_on_defect,
            "schema": self.SCHEMA_ID,
            "side": self.side,
            "topology": self.topology,
        }


def _algebra_data(
    side: str, analysis: CheshireStaticAnalysis
) -> Tuple[DefectFusionAlgebraData, ...]:
    return tuple(
        DefectFusionAlgebraData(
            side,
            report.line_defect.defect_id,
            report.line_defect.topology,
            report.defect_local_algebra,
            tuple(item.local_algebra for item in report.endpoint_reports),
            report.charge_termination.terminates_on_defect,
            report.charge_termination.changes_fixed_sector,
            report.magnetic_termination.terminates_on_defect,
            report.magnetic_termination.conclusion_basis,
        )
        for report in analysis.defect_reports
    )


@dataclass(frozen=True)
class FiniteDepthFusionCircuitAssessment:
    status: Exactness
    circuit: None
    reason: str

    SCHEMA_ID = "mobility_toolkit.finite_depth_fusion_circuit_assessment.v1"

    def __post_init__(self) -> None:
        if self.status != Exactness.UNSUPPORTED or self.circuit is not None:
            raise ValueError("no finite-depth fusion circuit is implemented")
        if not self.reason:
            raise ValueError("unsupported circuit assessment needs a reason")

    def to_canonical_dict(self) -> dict:
        return {
            "circuit": self.circuit,
            "reason": self.reason,
            "schema": self.SCHEMA_ID,
            "status": self.status,
        }


@dataclass(frozen=True)
class StaticCheshireFusionCertificate:
    fusion_id: str
    input_hash: str
    before_local_code_hash: str
    after_local_code_hash: str
    before_fixed_code_hash: str
    after_fixed_code_hash: str
    local_delta_hash: str
    fixed_delta_hash: str
    network_hash: str
    logical_counting_hash: str
    algebra_and_termination_hash: str
    phase_and_commutation_verified: bool
    stratum_coverage_verified: bool
    network_incidence_verified: bool
    static_candidate_verified: bool
    transcript: Tuple[Tuple[str, str], ...]
    transcript_hash: str

    SCHEMA_ID = "mobility_toolkit.static_cheshire_fusion_certificate.v1"

    @property
    def structurally_verified(self) -> bool:
        return (
            self.phase_and_commutation_verified
            and self.stratum_coverage_verified
            and self.network_incidence_verified
            and self.static_candidate_verified
            and self.transcript_hash == _digest(self.transcript)
            and dict(self.transcript)
            == {
                "after_fixed_code": self.after_fixed_code_hash,
                "after_local_code": self.after_local_code_hash,
                "algebra_and_termination": self.algebra_and_termination_hash,
                "before_fixed_code": self.before_fixed_code_hash,
                "before_local_code": self.before_local_code_hash,
                "fixed_delta": self.fixed_delta_hash,
                "input": self.input_hash,
                "local_delta": self.local_delta_hash,
                "logical_counting": self.logical_counting_hash,
                "networks": self.network_hash,
            }
        )

    def to_canonical_dict(self) -> dict:
        return {
            "after_fixed_code_hash": self.after_fixed_code_hash,
            "after_local_code_hash": self.after_local_code_hash,
            "algebra_and_termination_hash": self.algebra_and_termination_hash,
            "before_fixed_code_hash": self.before_fixed_code_hash,
            "before_local_code_hash": self.before_local_code_hash,
            "fixed_delta_hash": self.fixed_delta_hash,
            "fusion_id": self.fusion_id,
            "input_hash": self.input_hash,
            "local_delta_hash": self.local_delta_hash,
            "logical_counting_hash": self.logical_counting_hash,
            "network_hash": self.network_hash,
            "network_incidence_verified": self.network_incidence_verified,
            "phase_and_commutation_verified": self.phase_and_commutation_verified,
            "schema": self.SCHEMA_ID,
            "static_candidate_verified": self.static_candidate_verified,
            "stratum_coverage_verified": self.stratum_coverage_verified,
            "structurally_verified": self.structurally_verified,
            "transcript": self.transcript,
            "transcript_hash": self.transcript_hash,
        }


@dataclass(frozen=True)
class StaticCheshireFusionResult:
    fusion_id: str
    host_complex: CubicalComplex
    before_defects: Tuple[LineDefect, ...]
    after_defects: Tuple[LineDefect, ...]
    before_network: CheshireDefectNetwork
    after_network: CheshireDefectNetwork
    tube_radius_lattice_steps: int
    before_analysis: CheshireStaticAnalysis
    after_analysis: CheshireStaticAnalysis
    before_local_code: StabilizerCodeSpec
    after_local_code: StabilizerCodeSpec
    before_fixed_sector_code: StabilizerCodeSpec
    after_fixed_sector_code: StabilizerCodeSpec
    stratum_provenance: Tuple[FusionStratumProvenance, ...]
    local_hamiltonian_delta: StaticHamiltonianDelta
    fixed_sector_hamiltonian_delta: StaticHamiltonianDelta
    logical_counting: FiniteFusionLogicalCounting
    defect_algebra_and_termination: Tuple[DefectFusionAlgebraData, ...]
    static_candidate_exactness: Exactness
    finite_depth_circuit: FiniteDepthFusionCircuitAssessment
    junction_completion_scope: str
    certificate_level: CertificateLevel
    theorem_scope: str
    certificate: StaticCheshireFusionCertificate

    SCHEMA_ID = "mobility_toolkit.static_cheshire_fusion_result.v1"

    def __post_init__(self) -> None:
        if self.static_candidate_exactness != Exactness.CERTIFIED_EXACT:
            raise ValueError("finite static candidate must be certified exact")
        if not self.certificate.structurally_verified:
            raise ValueError("static fusion certificate is structurally invalid")

    def verify_certificate(self, backend: FiniteIntegerBackend) -> None:
        verify_static_cheshire_fusion(self, backend)

    def to_canonical_dict(self) -> dict:
        return {
            "after_analysis": self.after_analysis,
            "after_defects": self.after_defects,
            "after_fixed_sector_code": self.after_fixed_sector_code,
            "after_local_code": self.after_local_code,
            "after_network": self.after_network,
            "before_analysis": self.before_analysis,
            "before_defects": self.before_defects,
            "before_fixed_sector_code": self.before_fixed_sector_code,
            "before_local_code": self.before_local_code,
            "before_network": self.before_network,
            "certificate": self.certificate,
            "certificate_level": self.certificate_level,
            "defect_algebra_and_termination": self.defect_algebra_and_termination,
            "finite_depth_circuit": self.finite_depth_circuit,
            "fixed_sector_hamiltonian_delta": self.fixed_sector_hamiltonian_delta,
            "fusion_id": self.fusion_id,
            "host_complex": self.host_complex,
            "junction_completion_scope": self.junction_completion_scope,
            "local_hamiltonian_delta": self.local_hamiltonian_delta,
            "logical_counting": self.logical_counting,
            "schema": self.SCHEMA_ID,
            "static_candidate_exactness": self.static_candidate_exactness,
            "stratum_provenance": self.stratum_provenance,
            "theorem_scope": self.theorem_scope,
            "tube_radius_lattice_steps": self.tube_radius_lattice_steps,
        }


def _code(analysis: CheshireStaticAnalysis, fixed: bool) -> StabilizerCodeSpec:
    terms = analysis.fixed_sector_terms if fixed else analysis.local_terms
    return StabilizerCodeSpec(
        analysis.cellular_code.code.pauli_module,
        tuple(term.operator for term in terms),
        (
            "explicit finite Cheshire Hamiltonian",
            "fixed Cheshire charge sectors" if fixed else "unfixed Cheshire charge sectors",
        ),
    )


def _logical_counting(
    before: CheshireStaticAnalysis, after: CheshireStaticAnalysis
) -> FiniteFusionLogicalCounting:
    before_count = len(before.defect_reports)
    after_count = len(after.defect_reports)
    actual, predicted, matches = component_count_topology_guard(
        before.local_analysis.codespace_dimension,
        after.local_analysis.codespace_dimension,
        before_count,
        after_count,
    )
    return FiniteFusionLogicalCounting(
        before_count,
        after_count,
        before.local_analysis.codespace_dimension,
        after.local_analysis.codespace_dimension,
        actual,
        before.fixed_sector_analysis.codespace_dimension,
        after.fixed_sector_analysis.codespace_dimension,
        RationalFactor(
            after.fixed_sector_analysis.codespace_dimension,
            before.fixed_sector_analysis.codespace_dimension,
        ),
        before.local_analysis.logical_invariant_factors,
        after.local_analysis.logical_invariant_factors,
        before.fixed_sector_analysis.logical_invariant_factors,
        after.fixed_sector_analysis.logical_invariant_factors,
        predicted,
        matches,
    )


def component_count_topology_guard(
    before_codespace_dimension: int,
    after_codespace_dimension: int,
    before_component_count: int,
    after_component_count: int,
) -> Tuple[RationalFactor, RationalFactor, bool]:
    """Compare exact finite counts with, but never substitute, a component rule."""

    if (
        before_codespace_dimension < 1
        or after_codespace_dimension < 1
        or before_component_count < 0
        or after_component_count < 0
    ):
        raise ValueError("codespace dimensions must be positive and counts nonnegative")
    delta = after_component_count - before_component_count
    predicted = (
        RationalFactor(2 ** delta, 1)
        if delta >= 0
        else RationalFactor(1, 2 ** (-delta))
    )
    actual = RationalFactor(after_codespace_dimension, before_codespace_dimension)
    return actual, predicted, actual == predicted


def _construct(
    fusion_id: str,
    complex_: CubicalComplex,
    before_lines: Tuple[LineDefect, ...],
    after_lines: Tuple[LineDefect, ...],
    backend: FiniteIntegerBackend,
    tube_radius_lattice_steps: int,
    before_network: CheshireDefectNetwork,
    after_network: CheshireDefectNetwork,
) -> StaticCheshireFusionResult:
    if not fusion_id:
        raise ValueError("fusion_id must be nonempty")
    if not before_lines or not after_lines:
        raise ValueError("static fusion requires nonempty before and after defect sets")
    before_network.validate_against(before_lines)
    after_network.validate_against(after_lines)
    before = analyze_toric_cheshire(
        complex_, before_lines, backend, tube_radius_lattice_steps
    )
    after = analyze_toric_cheshire(
        complex_, after_lines, backend, tube_radius_lattice_steps
    )
    before_local = _code(before, False)
    after_local = _code(after, False)
    before_fixed = _code(before, True)
    after_fixed = _code(after, True)
    provenance = _strata("before", before_lines) + _strata("after", after_lines)
    local_delta = _hamiltonian_delta(
        before.local_terms, after.local_terms, provenance
    )
    fixed_delta = _hamiltonian_delta(
        before.fixed_sector_terms, after.fixed_sector_terms, provenance
    )
    if not local_delta.stratum_coverage_verified or not fixed_delta.stratum_coverage_verified:
        raise ArithmeticError("Hamiltonian rewrite escapes declared defect strata")
    logical = _logical_counting(before, after)
    algebra = _algebra_data("before", before) + _algebra_data("after", after)
    phase_verified = (
        not before_local.basic_validation_errors()
        and not after_local.basic_validation_errors()
        and not before_fixed.basic_validation_errors()
        and not after_fixed.basic_validation_errors()
        and before.local_analysis.validation.valid
        and after.local_analysis.validation.valid
        and before.fixed_sector_analysis.validation.valid
        and after.fixed_sector_analysis.validation.valid
    )
    input_data = {
        "after_defects": after_lines,
        "after_network": after_network,
        "before_defects": before_lines,
        "before_network": before_network,
        "fusion_id": fusion_id,
        "host_complex": complex_,
        "tube_radius_lattice_steps": tube_radius_lattice_steps,
    }
    values = {
        "after_fixed_code": _digest(after_fixed),
        "after_local_code": _digest(after_local),
        "algebra_and_termination": _digest(algebra),
        "before_fixed_code": _digest(before_fixed),
        "before_local_code": _digest(before_local),
        "fixed_delta": _digest(fixed_delta),
        "input": _digest(input_data),
        "local_delta": _digest(local_delta),
        "logical_counting": _digest(logical),
        "networks": _digest((before_network, after_network)),
    }
    transcript = tuple(sorted(values.items()))
    certificate = StaticCheshireFusionCertificate(
        fusion_id,
        values["input"],
        values["before_local_code"],
        values["after_local_code"],
        values["before_fixed_code"],
        values["after_fixed_code"],
        values["local_delta"],
        values["fixed_delta"],
        values["networks"],
        values["logical_counting"],
        values["algebra_and_termination"],
        bool(phase_verified),
        local_delta.stratum_coverage_verified
        and fixed_delta.stratum_coverage_verified,
        True,
        bool(phase_verified),
        transcript,
        _digest(transcript),
    )
    if not certificate.structurally_verified:
        raise ArithmeticError("failed to construct static fusion certificate")
    junction_scope = (
        "Junction incidence and strata are schema-validated only; no junction-local "
        "Hamiltonian completion is inferred."
        if before_network.has_junctions or after_network.has_junctions
        else "No junction stratum is present."
    )
    return StaticCheshireFusionResult(
        fusion_id,
        complex_,
        before_lines,
        after_lines,
        before_network,
        after_network,
        tube_radius_lattice_steps,
        before,
        after,
        before_local,
        after_local,
        before_fixed,
        after_fixed,
        provenance,
        local_delta,
        fixed_delta,
        logical,
        algebra,
        Exactness.CERTIFIED_EXACT,
        FiniteDepthFusionCircuitAssessment(
            Exactness.UNSUPPORTED,
            None,
            "Static stabilizer counting does not construct or certify a finite-depth "
            "fusion circuit.",
        ),
        junction_scope,
        CertificateLevel.FULL,
        STATIC_FUSION_SCOPE,
        certificate,
    )


def construct_static_toric_cheshire_fusion(
    fusion_id: str,
    complex_: CubicalComplex,
    before_defects: Sequence[object],
    after_defects: Sequence[object],
    backend: FiniteIntegerBackend,
    tube_radius_lattice_steps: int = 0,
    before_network: Optional[CheshireDefectNetwork] = None,
    after_network: Optional[CheshireDefectNetwork] = None,
) -> StaticCheshireFusionResult:
    """Build a replayable finite static fusion candidate.

    ``before_defects`` and ``after_defects`` are independently incidence
    validated by :func:`analyze_toric_cheshire`.  Network objects carry only
    combinatorial endpoint/junction strata unless explicit Hamiltonian terms
    represented in the before/after defects certify more.
    """

    before_lines = tuple(_normalize_defect(item) for item in before_defects)
    after_lines = tuple(_normalize_defect(item) for item in after_defects)
    before_graph = before_network or CheshireDefectNetwork.from_defects(before_lines)
    after_graph = after_network or CheshireDefectNetwork.from_defects(after_lines)
    return _construct(
        fusion_id,
        complex_,
        before_lines,
        after_lines,
        backend,
        tube_radius_lattice_steps,
        before_graph,
        after_graph,
    )


def verify_static_cheshire_fusion(
    result: StaticCheshireFusionResult, backend: FiniteIntegerBackend
) -> None:
    """Semantically replay a static fusion result and reject resealed tampering."""

    if not result.certificate.structurally_verified:
        raise ValueError("static fusion certificate failed structural verification")
    replayed = _construct(
        result.fusion_id,
        result.host_complex,
        result.before_defects,
        result.after_defects,
        backend,
        result.tube_radius_lattice_steps,
        result.before_network,
        result.after_network,
    )
    if canonical_json(result) != canonical_json(replayed):
        raise ValueError("static fusion semantic replay does not match supplied result")


__all__ = [
    "CheshireDefectNetwork",
    "CheshireNetworkEdge",
    "CheshireNetworkNode",
    "DefectFusionAlgebraData",
    "EndpointBinding",
    "FiniteDepthFusionCircuitAssessment",
    "FiniteFusionLogicalCounting",
    "FusionStratumProvenance",
    "NetworkNodeKind",
    "StaticCheshireFusionCertificate",
    "StaticCheshireFusionResult",
    "StaticHamiltonianDelta",
    "component_count_topology_guard",
    "construct_static_toric_cheshire_fusion",
    "verify_static_cheshire_fusion",
]
