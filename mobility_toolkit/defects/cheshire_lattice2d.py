"""Finite 2D toric descendant-defect realizations and Clifford witnesses.

The lattice realization is an explicit square-cellular, edge-qubit toric patch
with a finite vertical slit.  Bulk checks touching the slit endpoint qubits are
removed and replaced by the two commuting short folded-string generators of
the selected Lagrangian subgroup.  This is an exact finite commuting-Pauli
realization of the boundary operator algebra; it is not a thermodynamic gap
proof.

Circuit witnesses are kept equally honest.  Creation uses a sequential
head-to-tail CNOT circuit producing a GHZ/repetition-chain stabilizer pattern:
the local bond terms are retained while the global sector term is recorded
separately.  Motion/deformation/fusion use bounded-depth disjoint Clifford
layers.  Exact Pauli conjugation is replayed, but no minimum-depth theorem is
claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

from mobility_toolkit.core import (
    LocalPauliTerm,
    PauliModule,
    PauliOperator,
    canonical_hash,
)
from mobility_toolkit.finite import (
    FiniteIntegerBackend,
    analyze_finite_stabilizer,
)
from mobility_toolkit.geometry import (
    cellular_stabilizer_code,
    rectangular_cubical_complex,
)

from mobility_toolkit.defects.cheshire_classification import (
    EvidenceStatus,
    FusionCoefficient1D,
    TORIC_SPECIES_ORDER,
    fuse_toric_2d_species,
    toric_2d_defect_classification,
)


@dataclass(frozen=True)
class LatticeHamiltonianTerm:
    term_id: str
    role: str
    operator: PauliOperator

    SCHEMA_ID = "mobility_toolkit.cheshire_lattice_hamiltonian_term.v2"

    def __post_init__(self) -> None:
        if not self.term_id or not self.role:
            raise ValueError("Hamiltonian term ID and role must be nonempty")
        if not isinstance(self.operator, PauliOperator):
            raise TypeError("Hamiltonian term operator must be a PauliOperator")

    @property
    def support_site_ids(self) -> Tuple[str, ...]:
        return tuple(item.site_id for item in self.operator.terms)

    def to_canonical_dict(self) -> dict:
        return {
            "operator": self.operator,
            "role": self.role,
            "schema": self.SCHEMA_ID,
            "support_site_ids": self.support_site_ids,
            "term_id": self.term_id,
        }


@dataclass(frozen=True)
class LatticeSiteGeometry:
    site_id: str
    midpoint_twice: Tuple[int, int]
    edge_axis: int
    role: str

    SCHEMA_ID = "mobility_toolkit.cheshire_lattice_site_geometry.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "edge_axis": self.edge_axis,
            "midpoint_twice": self.midpoint_twice,
            "role": self.role,
            "schema": self.SCHEMA_ID,
            "site_id": self.site_id,
        }


@dataclass(frozen=True)
class ShortFoldedStringLift:
    lift_id: str
    folded_anyon_vector: Tuple[int, int, int, int]
    row: int
    operator: PauliOperator
    endpoint_role: str

    SCHEMA_ID = "mobility_toolkit.short_folded_string_lift.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "endpoint_role": self.endpoint_role,
            "folded_anyon_vector": self.folded_anyon_vector,
            "lift_id": self.lift_id,
            "operator": self.operator,
            "row": self.row,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class LatticeRealizationCertificate:
    pairwise_commutation_verified: bool
    removed_terms_touch_slit_verified: bool
    folded_generators_realized_verified: bool
    stabilizer_validation_verified: bool
    source_bulk_term_count: int
    retained_bulk_term_count: int
    removed_bulk_term_count: int
    defect_term_count: int
    transcript_hash: str
    theorem_scope: str

    SCHEMA_ID = "mobility_toolkit.cheshire_lattice_realization_certificate.v2"

    @property
    def verified(self) -> bool:
        return (
            self.pairwise_commutation_verified
            and self.removed_terms_touch_slit_verified
            and self.folded_generators_realized_verified
            and self.stabilizer_validation_verified
            and bool(self.transcript_hash)
        )

    def to_canonical_dict(self) -> dict:
        return {
            "defect_term_count": self.defect_term_count,
            "folded_generators_realized_verified":
                self.folded_generators_realized_verified,
            "pairwise_commutation_verified": self.pairwise_commutation_verified,
            "removed_bulk_term_count": self.removed_bulk_term_count,
            "removed_terms_touch_slit_verified":
                self.removed_terms_touch_slit_verified,
            "retained_bulk_term_count": self.retained_bulk_term_count,
            "schema": self.SCHEMA_ID,
            "source_bulk_term_count": self.source_bulk_term_count,
            "stabilizer_validation_verified": self.stabilizer_validation_verified,
            "theorem_scope": self.theorem_scope,
            "transcript_hash": self.transcript_hash,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class LatticeRealization:
    species_id: str
    lattice_kind: str
    shape: Tuple[int, int]
    slit_rows: Tuple[int, ...]
    pauli_module: PauliModule
    site_geometry: Tuple[LatticeSiteGeometry, ...]
    bulk_hamiltonian_terms: Tuple[LatticeHamiltonianTerm, ...]
    retained_bulk_terms: Tuple[LatticeHamiltonianTerm, ...]
    removed_bulk_terms: Tuple[LatticeHamiltonianTerm, ...]
    truncated_bulk_terms: Tuple[LatticeHamiltonianTerm, ...]
    defect_terms: Tuple[LatticeHamiltonianTerm, ...]
    endpoint_term_ids: Tuple[str, ...]
    short_folded_string_lifts: Tuple[ShortFoldedStringLift, ...]
    codespace_dimension: int
    logical_invariant_factors: Tuple[int, ...]
    diagram_json: Tuple[Tuple[str, object], ...]
    tikz: str
    evidence_status: EvidenceStatus
    certificate: LatticeRealizationCertificate
    warnings: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.cheshire_lattice_realization.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_hamiltonian_terms": self.bulk_hamiltonian_terms,
            "certificate": self.certificate,
            "codespace_dimension": self.codespace_dimension,
            "defect_terms": self.defect_terms,
            "diagram_json": self.diagram_json,
            "endpoint_term_ids": self.endpoint_term_ids,
            "evidence_status": self.evidence_status,
            "lattice_kind": self.lattice_kind,
            "logical_invariant_factors": self.logical_invariant_factors,
            "pauli_module": self.pauli_module,
            "removed_bulk_terms": self.removed_bulk_terms,
            "retained_bulk_terms": self.retained_bulk_terms,
            "schema": self.SCHEMA_ID,
            "shape": self.shape,
            "short_folded_string_lifts": self.short_folded_string_lifts,
            "site_geometry": self.site_geometry,
            "slit_rows": self.slit_rows,
            "species_id": self.species_id,
            "tikz": self.tikz,
            "truncated_bulk_terms": self.truncated_bulk_terms,
            "warnings": self.warnings,
        }


def _all_commute(terms: Sequence[LatticeHamiltonianTerm]) -> bool:
    values = tuple(terms)
    return all(
        left.operator.commutes_with(right.operator)
        for index, left in enumerate(values)
        for right in values[index + 1 :]
    )


def _generator_operator(
    module: PauliModule,
    left_site: str,
    right_site: str,
    vector: Sequence[int],
) -> PauliOperator:
    e_left, m_left, e_right, m_right = tuple(int(value) % 2 for value in vector)
    terms = []
    if e_left or m_left:
        terms.append(
            LocalPauliTerm.cyclic(left_site, x=m_left, z=e_left)
        )
    if e_right or m_right:
        terms.append(
            LocalPauliTerm.cyclic(right_site, x=m_right, z=e_right)
        )
    return module.operator(tuple(terms))


def _tikz_for_realization(
    shape: Tuple[int, int],
    geometry: Sequence[LatticeSiteGeometry],
    defect_terms: Sequence[LatticeHamiltonianTerm],
) -> str:
    width, height = shape
    lines = [
        r"\begin{tikzpicture}[scale=0.55]",
        rf"\draw[step=1cm,gray!45,thin] (0,0) grid ({width},{height});",
        rf"\draw[blue!70!black,very thick] (2,0) -- (2,{height});",
    ]
    coordinate_by_id = {
        item.site_id: (item.midpoint_twice[0] / 2, item.midpoint_twice[1] / 2)
        for item in geometry
    }
    for term in defect_terms:
        points = [
            coordinate_by_id[site_id]
            for site_id in term.support_site_ids
            if site_id in coordinate_by_id
        ]
        if len(points) == 1:
            x, y = points[0]
            lines.append(rf"\fill[red!75!black] ({x},{y}) circle (2.3pt);")
        elif len(points) == 2:
            (x0, y0), (x1, y1) = points
            lines.append(
                rf"\draw[red!75!black,line width=1.2pt] ({x0},{y0}) -- ({x1},{y1});"
            )
    lines.append(r"\end{tikzpicture}")
    return "\n".join(lines)


def realize_toric_2d_defect(
    species_id: str,
    line_length_lattice_steps: int,
    backend: FiniteIntegerBackend,
) -> LatticeRealization:
    """Build and exactly verify one finite square-lattice slit realization."""

    if species_id not in TORIC_SPECIES_ORDER:
        raise ValueError("unknown toric species: " + species_id)
    if (
        isinstance(line_length_lattice_steps, bool)
        or not isinstance(line_length_lattice_steps, int)
        or line_length_lattice_steps < 1
    ):
        raise ValueError("line_length_lattice_steps must be a positive integer")

    height = line_length_lattice_steps
    shape = (4, height)
    complex_ = rectangular_cubical_complex(shape)
    cellular = cellular_stabilizer_code(complex_.chain_complex, 1, 2)
    module = cellular.code.pauli_module
    edge_cells = tuple(complex_.cells_by_dimension[1])
    by_axis_base = {
        (cell.varying_axes, cell.base): cell for cell in edge_cells
    }
    slit_pairs = []
    for row in range(height):
        left = by_axis_base[((0,), (1, row))]
        right = by_axis_base[((0,), (2, row))]
        slit_pairs.append((left.cell_id, right.cell_id))
    slit_sites = {site for pair in slit_pairs for site in pair}

    bulk_terms = tuple(
        LatticeHamiltonianTerm(
            f"bulk:{record.pauli_kind}:{record.cell_id}",
            "bulk_stabilizer",
            record.operator,
        )
        for record in cellular.check_records
    )
    removed = tuple(
        item
        for item in bulk_terms
        if set(item.support_site_ids) & slit_sites
    )
    retained = tuple(item for item in bulk_terms if item not in removed)

    classification = toric_2d_defect_classification(backend)
    species = next(item for item in classification.species if item.species_id == species_id)
    defect_terms = []
    lifts = []
    for row, (left_site, right_site) in enumerate(slit_pairs):
        for generator_index, vector in enumerate(species.folded_generators):
            operator = _generator_operator(module, left_site, right_site, vector)
            term_id = f"defect:{species_id}:r{row}:g{generator_index}"
            role = (
                "endpoint_defect_generator"
                if row in {0, height - 1}
                else "interior_defect_generator"
            )
            defect_terms.append(LatticeHamiltonianTerm(term_id, role, operator))
            lifts.append(
                ShortFoldedStringLift(
                    lift_id="lift:" + term_id,
                    folded_anyon_vector=tuple(vector),
                    row=row,
                    operator=operator,
                    endpoint_role=(
                        "open_interval_endpoint"
                        if row in {0, height - 1}
                        else "interior_short_lift"
                    ),
                )
            )

    completed = retained + tuple(defect_terms)
    if not _all_commute(completed):
        raise ArithmeticError("constructed toric slit Hamiltonian is not commuting")
    analysis = analyze_finite_stabilizer(
        module, tuple(item.operator for item in completed), backend
    )
    removed_touch = all(set(item.support_site_ids) & slit_sites for item in removed)
    realized_vectors = tuple(
        item.folded_anyon_vector
        for item in lifts[: len(species.folded_generators)]
    )
    folded_verified = realized_vectors == species.folded_generators

    geometry = []
    for cell in edge_cells:
        midpoint = tuple(
            2 * cell.base[axis] + (1 if axis in cell.varying_axes else 0)
            for axis in range(2)
        )
        role = (
            "left_slit_endpoint_operator"
            if cell.cell_id in {pair[0] for pair in slit_pairs}
            else (
                "right_slit_endpoint_operator"
                if cell.cell_id in {pair[1] for pair in slit_pairs}
                else "bulk_edge_qubit"
            )
        )
        geometry.append(
            LatticeSiteGeometry(
                cell.cell_id,
                midpoint,
                cell.varying_axes[0],
                role,
            )
        )
    geometry = tuple(sorted(geometry, key=lambda item: item.site_id))
    endpoint_ids = tuple(
        item.term_id
        for item in defect_terms
        if item.role == "endpoint_defect_generator"
    )
    diagram_json = (
        ("defect_axis", "vertical"),
        ("defect_x_coordinate", 2),
        ("edge_qubit_count", len(edge_cells)),
        ("line_length_lattice_steps", height),
        ("removed_bulk_term_ids", tuple(item.term_id for item in removed)),
        ("retained_bulk_term_ids", tuple(item.term_id for item in retained)),
        ("defect_term_ids", tuple(item.term_id for item in defect_terms)),
    )
    theorem_scope = (
        "Exact finite commuting-Pauli realization on the recorded square-cellular "
        "edge-qubit patch. Bulk checks touching the slit endpoint-operator sites "
        "are removed and replaced by the selected folded Lagrangian generators. "
        "No thermodynamic gap or uniqueness theorem is inferred."
    )
    transcript_hash = canonical_hash(
        "mobility_toolkit.toric_2d_lattice_realization_transcript.v2",
        {
            "analysis": analysis.validation,
            "defect_terms": tuple(defect_terms),
            "removed": removed,
            "retained": retained,
            "species": species,
        },
    )
    certificate = LatticeRealizationCertificate(
        pairwise_commutation_verified=True,
        removed_terms_touch_slit_verified=removed_touch,
        folded_generators_realized_verified=folded_verified,
        stabilizer_validation_verified=analysis.validation.valid,
        source_bulk_term_count=len(bulk_terms),
        retained_bulk_term_count=len(retained),
        removed_bulk_term_count=len(removed),
        defect_term_count=len(defect_terms),
        transcript_hash=transcript_hash,
        theorem_scope=theorem_scope,
    )
    if not certificate.verified:
        raise ArithmeticError("toric lattice realization certificate failed")
    return LatticeRealization(
        species_id=species_id,
        lattice_kind="square_cellular_edge_qubit_z2_toric_with_vertical_slit",
        shape=shape,
        slit_rows=tuple(range(height)),
        pauli_module=module,
        site_geometry=geometry,
        bulk_hamiltonian_terms=bulk_terms,
        retained_bulk_terms=retained,
        removed_bulk_terms=removed,
        truncated_bulk_terms=(),
        defect_terms=tuple(defect_terms),
        endpoint_term_ids=endpoint_ids,
        short_folded_string_lifts=tuple(lifts),
        codespace_dimension=analysis.codespace_dimension,
        logical_invariant_factors=analysis.logical_invariant_factors,
        diagram_json=diagram_json,
        tikz=_tikz_for_realization(shape, geometry, defect_terms),
        evidence_status=EvidenceStatus.BOUNDED_EXACT,
        certificate=certificate,
        warnings=(
            "This is a finite folded-boundary operator-algebra realization, not a thermodynamic gap proof.",
            "Endpoint-local topological superselection data require a separate scaling argument.",
        ),
    )


@dataclass(frozen=True)
class CliffordGate:
    gate_kind: str
    site_ids: Tuple[str, ...]
    rotation_generator: Optional[PauliOperator] = None

    SCHEMA_ID = "mobility_toolkit.clifford_gate.v2"

    def __post_init__(self) -> None:
        arity = {"h": 1, "s": 1, "sdg": 1, "cnot": 2, "cz": 2}
        if self.gate_kind not in {*arity, "pauli_r"}:
            raise ValueError("unsupported Clifford gate kind: " + self.gate_kind)
        if self.gate_kind in arity and len(self.site_ids) != arity[self.gate_kind]:
            raise ValueError("Clifford gate has the wrong arity")
        if len(set(self.site_ids)) != len(self.site_ids):
            raise ValueError("Clifford gate repeats a site")
        if self.gate_kind == "pauli_r":
            if self.rotation_generator is None:
                raise ValueError("pauli_r requires an exact Pauli generator")
            if self.rotation_generator.projective_element_order != 2:
                raise ValueError("pauli_r generator must have projective order two")
            if tuple(
                term.site_id for term in self.rotation_generator.terms
            ) != tuple(sorted(self.site_ids)):
                raise ValueError(
                    "pauli_r site_ids must equal the sorted generator support"
                )
        elif self.rotation_generator is not None:
            raise ValueError(
                "rotation_generator is valid only for a pauli_r gate"
            )

    def to_canonical_dict(self) -> dict:
        return {
            "gate_kind": self.gate_kind,
            "rotation_generator": self.rotation_generator,
            "schema": self.SCHEMA_ID,
            "site_ids": self.site_ids,
        }


@dataclass(frozen=True)
class CliffordLayer:
    layer_id: str
    gates: Tuple[CliffordGate, ...]
    execution_kind: str

    SCHEMA_ID = "mobility_toolkit.clifford_layer.v2"

    def __post_init__(self) -> None:
        if not self.layer_id or not self.execution_kind:
            raise ValueError("Clifford layer ID and execution kind must be nonempty")
        occupied = [site for gate in self.gates for site in gate.site_ids]
        if len(occupied) != len(set(occupied)):
            raise ValueError("gates in one certified parallel layer must be disjoint")

    def to_canonical_dict(self) -> dict:
        return {
            "execution_kind": self.execution_kind,
            "gates": self.gates,
            "layer_id": self.layer_id,
            "schema": self.SCHEMA_ID,
        }


def _single_generator(
    module: PauliModule, site_id: str, kind: str
) -> PauliOperator:
    return module.operator(
        (
            LocalPauliTerm.cyclic(
                site_id,
                x=1 if kind == "x" else 0,
                z=1 if kind == "z" else 0,
            ),
        )
    )


def _gate_image(
    module: PauliModule, gate: CliffordGate, site_id: str, kind: str
) -> PauliOperator:
    if gate.gate_kind in {"h", "s", "sdg"}:
        target = gate.site_ids[0]
        if site_id != target:
            return _single_generator(module, site_id, kind)
        if gate.gate_kind == "h":
            return _single_generator(module, site_id, "z" if kind == "x" else "x")
        if kind == "z":
            return _single_generator(module, site_id, "z")
        phase = 1 if gate.gate_kind == "s" else 3
        return module.operator(
            (LocalPauliTerm.cyclic(site_id, x=1, z=1),),
            phase=phase,
        )

    control, target = gate.site_ids
    if gate.gate_kind == "cnot":
        if site_id == control and kind == "x":
            return module.operator(
                (
                    LocalPauliTerm.cyclic(control, x=1),
                    LocalPauliTerm.cyclic(target, x=1),
                )
            )
        if site_id == target and kind == "z":
            return module.operator(
                (
                    LocalPauliTerm.cyclic(control, z=1),
                    LocalPauliTerm.cyclic(target, z=1),
                )
            )
        return _single_generator(module, site_id, kind)
    if gate.gate_kind == "cz":
        if site_id == control and kind == "x":
            return module.operator(
                (
                    LocalPauliTerm.cyclic(control, x=1),
                    LocalPauliTerm.cyclic(target, z=1),
                )
            )
        if site_id == target and kind == "x":
            return module.operator(
                (
                    LocalPauliTerm.cyclic(control, z=1),
                    LocalPauliTerm.cyclic(target, x=1),
                )
            )
        return _single_generator(module, site_id, kind)
    raise ArithmeticError("unreachable Clifford gate kind")


def conjugate_pauli_by_gate(
    operator: PauliOperator, gate: CliffordGate
) -> PauliOperator:
    module = operator.module
    if any(module.system(site_id).invariant_factors != (2,) for site_id in gate.site_ids):
        raise ValueError("implemented Clifford witnesses require qubit sites")
    if gate.gate_kind == "pauli_r":
        generator = gate.rotation_generator
        assert generator is not None
        if generator.module != module:
            raise ValueError("pauli_r generator belongs to a different module")
        if operator.commutes_with(generator):
            return operator
        # R(Q) P R(Q)^dagger = i P Q for R(Q)=exp(-i*pi*Q/4).
        product = operator * generator
        return product.with_phase(product.phase + 1)
    result = module.identity(operator.phase)
    term_map = {term.site_id: term for term in operator.terms}
    for system in module.local_systems:
        term = term_map.get(system.site_id)
        if term is None:
            continue
        if term.x_exponents[0]:
            result = result * _gate_image(module, gate, system.site_id, "x")
        if term.z_exponents[0]:
            result = result * _gate_image(module, gate, system.site_id, "z")
    return result


@dataclass(frozen=True)
class CliffordCircuit:
    circuit_id: str
    layers: Tuple[CliffordLayer, ...]
    depth_scaling: str
    provenance_kind: str
    source: str

    SCHEMA_ID = "mobility_toolkit.clifford_circuit.v2"

    def apply(self, operator: PauliOperator) -> PauliOperator:
        result = operator
        for layer in self.layers:
            for gate in layer.gates:
                result = conjugate_pauli_by_gate(result, gate)
        return result

    @property
    def depth(self) -> int:
        return len(self.layers)

    def to_canonical_dict(self) -> dict:
        return {
            "circuit_id": self.circuit_id,
            "depth": self.depth,
            "depth_scaling": self.depth_scaling,
            "layers": self.layers,
            "provenance_kind": self.provenance_kind,
            "schema": self.SCHEMA_ID,
            "source": self.source,
        }


@dataclass(frozen=True)
class CircuitReplayCertificate:
    source_terms_hash: str
    target_terms_hash: str
    circuit_hash: str
    exact_pauli_conjugation_verified: bool
    layer_disjointness_verified: bool
    hidden_sector_separated: bool
    endpoint_incidence_verified: bool
    ancilla_decoupling_verified: Optional[bool]
    coefficient_sector_codespace_dimension: Optional[int]
    fusion_degeneracy_matches_coefficient_shadow: Optional[bool]
    finite_depth_claim: bool
    sequential_linear_depth_claim: bool
    theorem_scope: str

    SCHEMA_ID = "mobility_toolkit.circuit_replay_certificate.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "circuit_hash": self.circuit_hash,
            "ancilla_decoupling_verified":
                self.ancilla_decoupling_verified,
            "coefficient_sector_codespace_dimension":
                self.coefficient_sector_codespace_dimension,
            "endpoint_incidence_verified": self.endpoint_incidence_verified,
            "exact_pauli_conjugation_verified":
                self.exact_pauli_conjugation_verified,
            "finite_depth_claim": self.finite_depth_claim,
            "hidden_sector_separated": self.hidden_sector_separated,
            "layer_disjointness_verified": self.layer_disjointness_verified,
            "fusion_degeneracy_matches_coefficient_shadow":
                self.fusion_degeneracy_matches_coefficient_shadow,
            "schema": self.SCHEMA_ID,
            "sequential_linear_depth_claim": self.sequential_linear_depth_claim,
            "source_terms_hash": self.source_terms_hash,
            "target_terms_hash": self.target_terms_hash,
            "theorem_scope": self.theorem_scope,
        }


@dataclass(frozen=True)
class Toric2DCircuitRealization:
    process: str
    left_species_id: str
    right_species_id: Optional[str]
    output_species_id: str
    coefficient: Optional[FusionCoefficient1D]
    pauli_module: PauliModule
    source_terms: Tuple[LatticeHamiltonianTerm, ...]
    target_terms: Tuple[LatticeHamiltonianTerm, ...]
    target_local_term_ids: Tuple[str, ...]
    hidden_sector_term_ids: Tuple[str, ...]
    coefficient_term_ids: Tuple[str, ...]
    circuit: CliffordCircuit
    evidence_status: EvidenceStatus
    certificate: CircuitReplayCertificate
    warnings: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.toric_2d_circuit_realization.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "circuit": self.circuit,
            "coefficient": self.coefficient,
            "coefficient_term_ids": self.coefficient_term_ids,
            "evidence_status": self.evidence_status,
            "hidden_sector_term_ids": self.hidden_sector_term_ids,
            "left_species_id": self.left_species_id,
            "output_species_id": self.output_species_id,
            "pauli_module": self.pauli_module,
            "process": self.process,
            "right_species_id": self.right_species_id,
            "schema": self.SCHEMA_ID,
            "source_terms": self.source_terms,
            "target_local_term_ids": self.target_local_term_ids,
            "target_terms": self.target_terms,
            "warnings": self.warnings,
        }


def _pauli_rotation_gate(generator: PauliOperator) -> CliffordGate:
    return CliffordGate(
        "pauli_r",
        tuple(term.site_id for term in generator.terms),
        generator,
    )


def _source_locked_condensate_creation_circuit(
    species_id: str,
    module: PauliModule,
    site_ids: Sequence[str],
) -> CliffordCircuit:
    """Replay Eqs. (2)/(12) in the exact effective charge/flux chain."""

    if species_id not in {"S_e", "S_m"}:
        raise ValueError("source-locked condensate circuit requires S_e or S_m")
    site_ids = tuple(site_ids)
    check_kind = "x" if species_id == "S_e" else "z"
    pair_kind = "z" if species_id == "S_e" else "x"
    layers = []
    for index in range(1, len(site_ids)):
        pair_generator = module.operator(
            (
                LocalPauliTerm.cyclic(
                    site_ids[index - 1],
                    x=1 if pair_kind == "x" else 0,
                    z=1 if pair_kind == "z" else 0,
                ),
                LocalPauliTerm.cyclic(
                    site_ids[index],
                    x=1 if pair_kind == "x" else 0,
                    z=1 if pair_kind == "z" else 0,
                ),
            )
        )
        check_generator = _single_generator(
            module, site_ids[index], check_kind
        )
        layers.extend(
            (
                CliffordLayer(
                    f"source-locked-{species_id}-pair-{index}",
                    (_pauli_rotation_gate(pair_generator),),
                    "sequential_pauli_rotation",
                ),
                CliffordLayer(
                    f"source-locked-{species_id}-check-{index}",
                    (_pauli_rotation_gate(check_generator),),
                    "sequential_pauli_rotation",
                ),
            )
        )
    equation = "Eq. (2)" if species_id == "S_e" else "Eq. (12)"
    return CliffordCircuit(
        "toric2d:create:" + species_id,
        tuple(layers),
        "linear_in_defect_length",
        "source_locked",
        (
            "Tantivasadakarn--Chen arXiv:2307.03180 "
            + equation
            + "; exact effective charge/flux-chain Pauli-rotation replay"
        ),
    )


def _derived_creation_circuit(
    species_id: str, site_ids: Sequence[str]
) -> CliffordCircuit:
    site_ids = tuple(site_ids)
    if species_id == "1":
        return CliffordCircuit(
            "toric2d:create:1",
            (),
            "constant_zero",
            "source_locked",
            "identity defect",
        )
    layers = [
        CliffordLayer(
            "seed-hadamard",
            (CliffordGate("h", (site_ids[0],)),),
            "sequential_seed",
        )
    ]
    for index in range(1, len(site_ids)):
        layers.append(
            CliffordLayer(
                f"head_to_tail_{index}",
                (
                    CliffordGate(
                        "cnot", (site_ids[index - 1], site_ids[index])
                    ),
                ),
                "sequential_head_to_tail",
            )
        )
    if species_id in {"S_m", "S_psi"}:
        layers.append(
            CliffordLayer(
                "duality-decoration",
                tuple(CliffordGate("h", (site,)) for site in site_ids),
                "parallel_duality_decoration",
            )
        )
    elif species_id in {"S_em", "S_me"}:
        gate_kind = "s" if species_id == "S_em" else "sdg"
        layers.append(
            CliffordLayer(
                "discrete-torsion-decoration",
                tuple(CliffordGate(gate_kind, (site,)) for site in site_ids),
                "parallel_discrete_torsion_decoration",
            )
        )
    return CliffordCircuit(
        "toric2d:create:" + species_id,
        tuple(layers),
        "linear_in_defect_length",
        "derived_from_source_generators",
        (
            "finite-chain Clifford composition inspired by the source "
            "generators; not identified with an individual paper diagram"
        ),
    )


def _parallel_swap_circuit(
    process: str, first: Sequence[str], second: Sequence[str]
) -> CliffordCircuit:
    first = tuple(first)
    second = tuple(second)
    layers = []
    for layer_index, (control_first, control_second) in enumerate(
        ((True, False), (False, True), (True, False))
    ):
        gates = []
        for left, right in zip(first, second):
            if control_first:
                gates.append(CliffordGate("cnot", (left, right)))
            elif control_second:
                gates.append(CliffordGate("cnot", (right, left)))
        layers.append(
            CliffordLayer(
                f"{process}:swap-layer-{layer_index}",
                tuple(gates),
                "parallel_disjoint",
            )
        )
    return CliffordCircuit(
        f"toric2d:{process}:parallel-swap",
        tuple(layers),
        "constant_depth_3",
        "derived_from_source_generators",
        "finite-depth Clifford deformation/motion template",
    )


def _fusion_circuit(
    first: Sequence[str], second: Sequence[str]
) -> CliffordCircuit:
    gates = tuple(
        CliffordGate("cnot", (left, right))
        for left, right in zip(first, second)
    )
    return CliffordCircuit(
        "toric2d:fusion:parallel-cnot",
        (
            CliffordLayer(
                "fusion-domain-wall-decoupling",
                gates,
                "parallel_disjoint",
            ),
        ),
        "constant_depth_1",
        "derived_from_source_generators",
        (
            "finite-chain CNOT representative derived from the "
            "Tantivasadakarn--Chen arXiv:2307.03180 fusion structure"
        ),
    )


def _source_terms_for_sites(
    module: PauliModule,
    site_ids: Sequence[str],
    prefix: str,
    kind: str = "z",
) -> Tuple[LatticeHamiltonianTerm, ...]:
    return tuple(
        LatticeHamiltonianTerm(
            f"{prefix}:{kind}:{index}",
            "circuit_source_stabilizer",
            _single_generator(module, site_id, kind),
        )
        for index, site_id in enumerate(site_ids)
    )


def _target_terms(
    source_terms: Sequence[LatticeHamiltonianTerm],
    circuit: CliffordCircuit,
) -> Tuple[LatticeHamiltonianTerm, ...]:
    return tuple(
        LatticeHamiltonianTerm(
            "image:" + item.term_id,
            "circuit_target_stabilizer",
            circuit.apply(item.operator),
        )
        for item in source_terms
    )


def _fusion_source_terms(
    module: PauliModule,
    first: Sequence[str],
    second: Sequence[str],
    circuit: CliffordCircuit,
    coefficient: FusionCoefficient1D,
) -> Tuple[LatticeHamiltonianTerm, ...]:
    """Return the inverse images of a separated fused chain and coefficient chain.

    The parallel CNOT layer is self-inverse.  Constructing the source terms as
    inverse images therefore makes the output split explicit: the ``a`` sites
    carry the fused defect, while the ``b`` sites carry a finite representative
    of the 1+1D fusion coefficient.
    """

    separated: list[LatticeHamiltonianTerm] = []
    for index, site_id in enumerate(first):
        target_operator = _single_generator(module, site_id, "z")
        separated.append(
            LatticeHamiltonianTerm(
                f"fusion:fused:z:{index}",
                "fusion_source_inverse_image",
                circuit.apply(target_operator),
            )
        )

    shadow = coefficient.partition_function_shadow_on_interval
    if shadow == 2:
        for index, (left, right) in enumerate(zip(second, second[1:])):
            target_operator = (
                _single_generator(module, left, "z")
                * _single_generator(module, right, "z")
            )
            separated.append(
                LatticeHamiltonianTerm(
                    f"fusion:coefficient:z2_bond:{index}",
                    "fusion_source_inverse_image",
                    circuit.apply(target_operator),
                )
            )
    elif shadow == 1:
        for index, site_id in enumerate(second):
            target_operator = _single_generator(module, site_id, "z")
            separated.append(
                LatticeHamiltonianTerm(
                    f"fusion:coefficient:trivial:{index}",
                    "fusion_source_inverse_image",
                    circuit.apply(target_operator),
                )
            )
    else:
        raise NotImplementedError(
            "the finite fusion-chain witness supports only interval shadows one and two"
        )
    return tuple(separated)


def _fusion_certificate_data(
    target_terms: Sequence[LatticeHamiltonianTerm],
    first: Sequence[str],
    second: Sequence[str],
    coefficient: FusionCoefficient1D,
) -> Tuple[Tuple[str, ...], bool, int, bool]:
    coefficient_terms = tuple(
        term for term in target_terms
        if term.term_id.startswith("image:fusion:coefficient:")
    )
    fused_terms = tuple(
        term for term in target_terms
        if term.term_id.startswith("image:fusion:fused:")
    )
    first_set = set(first)
    second_set = set(second)
    separated = (
        bool(fused_terms)
        and bool(coefficient_terms)
        and all(set(term.support_site_ids) <= first_set for term in fused_terms)
        and all(
            set(term.support_site_ids) <= second_set
            for term in coefficient_terms
        )
    )
    coefficient_dimension = (
        2
        if all(
            term.term_id.startswith("image:fusion:coefficient:z2_bond:")
            for term in coefficient_terms
        )
        and len(coefficient_terms) == len(second) - 1
        else 1
        if all(
            term.term_id.startswith("image:fusion:coefficient:trivial:")
            for term in coefficient_terms
        )
        and len(coefficient_terms) == len(second)
        else 0
    )
    matches = (
        coefficient_dimension
        == coefficient.partition_function_shadow_on_interval
    )
    return (
        tuple(term.term_id for term in coefficient_terms),
        separated,
        coefficient_dimension,
        matches,
    )


def verify_toric_2d_circuit(
    result: Toric2DCircuitRealization,
) -> bool:
    expected = _target_terms(result.source_terms, result.circuit)
    source_hash = canonical_hash(
        "mobility_toolkit.circuit_source_terms.v2", result.source_terms
    )
    target_hash = canonical_hash(
        "mobility_toolkit.circuit_target_terms.v2", result.target_terms
    )
    circuit_hash = canonical_hash(
        "mobility_toolkit.clifford_circuit_hash.v2", result.circuit
    )
    certificate = result.certificate
    fusion_fields_valid = True
    if result.process == "fusion":
        if result.coefficient is None:
            return False
        length = len(result.pauli_module.local_systems) // 2
        first = tuple(f"a{index}" for index in range(length))
        second = tuple(f"b{index}" for index in range(length))
        (
            coefficient_ids,
            separated,
            coefficient_dimension,
            coefficient_matches,
        ) = _fusion_certificate_data(
            result.target_terms,
            first,
            second,
            result.coefficient,
        )
        fusion_fields_valid = (
            result.coefficient_term_ids == coefficient_ids
            and certificate.ancilla_decoupling_verified == separated
            and certificate.coefficient_sector_codespace_dimension
            == coefficient_dimension
            and certificate.fusion_degeneracy_matches_coefficient_shadow
            == coefficient_matches
            and separated
            and coefficient_matches
        )
    else:
        fusion_fields_valid = (
            not result.coefficient_term_ids
            and certificate.ancilla_decoupling_verified is None
            and certificate.coefficient_sector_codespace_dimension is None
            and certificate.fusion_degeneracy_matches_coefficient_shadow is None
        )
    return (
        expected == result.target_terms
        and certificate.source_terms_hash == source_hash
        and certificate.target_terms_hash == target_hash
        and certificate.circuit_hash == circuit_hash
        and certificate.exact_pauli_conjugation_verified
        and certificate.layer_disjointness_verified
        and certificate.endpoint_incidence_verified
        and fusion_fields_valid
    )


def construct_toric_2d_circuit(
    process: str,
    left_species_id: str,
    line_length_lattice_steps: int,
    *,
    right_species_id: Optional[str] = None,
) -> Toric2DCircuitRealization:
    """Construct a replayable finite Clifford witness for one requested process."""

    if process not in {"creation", "deformation", "motion", "fusion"}:
        raise ValueError("process must be creation, deformation, motion, or fusion")
    if left_species_id not in TORIC_SPECIES_ORDER:
        raise ValueError("unknown toric species: " + left_species_id)
    if (
        isinstance(line_length_lattice_steps, bool)
        or not isinstance(line_length_lattice_steps, int)
        or line_length_lattice_steps < 2
    ):
        raise ValueError("circuit line length must be an integer at least two")
    length = line_length_lattice_steps

    coefficient = None
    coefficient_ids: Tuple[str, ...] = ()
    ancilla_decoupling: Optional[bool] = None
    coefficient_dimension: Optional[int] = None
    coefficient_matches: Optional[bool] = None
    output_species = left_species_id
    if process == "creation":
        site_ids = tuple(f"d{index}" for index in range(length + 1))
        module = PauliModule.from_dimensions((2,) * len(site_ids), site_ids)
        source_kind = "x" if left_species_id == "S_e" else "z"
        source = _source_terms_for_sites(
            module, site_ids, "creation", source_kind
        )
        circuit = (
            _source_locked_condensate_creation_circuit(
                left_species_id, module, site_ids
            )
            if left_species_id in {"S_e", "S_m"}
            else _derived_creation_circuit(left_species_id, site_ids)
        )
        target = _target_terms(source, circuit)
        hidden_ids = (target[0].term_id,) if left_species_id != "1" else ()
        local_ids = tuple(item.term_id for item in target if item.term_id not in hidden_ids)
        sequential = left_species_id != "1"
        finite_depth = left_species_id == "1"
    else:
        first = tuple(f"a{index}" for index in range(length))
        second = tuple(f"b{index}" for index in range(length))
        module = PauliModule.from_dimensions(
            (2,) * (2 * length), first + second
        )
        if process in {"deformation", "motion"}:
            source = _source_terms_for_sites(module, first + second, process)
            circuit = _parallel_swap_circuit(process, first, second)
        else:
            if right_species_id not in TORIC_SPECIES_ORDER:
                raise ValueError("fusion requires a known right_species_id")
            fusion = fuse_toric_2d_species(left_species_id, right_species_id)
            output_species = fusion.terms[0].output_species_id
            coefficient = fusion.terms[0].coefficient
            circuit = _fusion_circuit(first, second)
            source = _fusion_source_terms(
                module, first, second, circuit, coefficient
            )
        target = _target_terms(source, circuit)
        if process == "fusion":
            (
                coefficient_ids,
                ancilla_decoupling,
                coefficient_dimension,
                coefficient_matches,
            ) = _fusion_certificate_data(
                target, first, second, coefficient
            )
        hidden_ids = ()
        local_ids = tuple(item.term_id for item in target)
        sequential = False
        finite_depth = True

    source_hash = canonical_hash(
        "mobility_toolkit.circuit_source_terms.v2", source
    )
    target_hash = canonical_hash(
        "mobility_toolkit.circuit_target_terms.v2", target
    )
    circuit_hash = canonical_hash(
        "mobility_toolkit.clifford_circuit_hash.v2", circuit
    )
    theorem_scope = (
        "Exact phase-aware Pauli conjugation for the recorded finite defect-chain "
        "template. Sequential creation separates one global sector term from "
        "the local chain Hamiltonian. Bounded-depth deformation/motion/fusion "
        "is certified only for this template; no minimum-depth theorem or "
        "thermodynamic phase equivalence is inferred."
    )
    certificate = CircuitReplayCertificate(
        source_terms_hash=source_hash,
        target_terms_hash=target_hash,
        circuit_hash=circuit_hash,
        exact_pauli_conjugation_verified=True,
        layer_disjointness_verified=True,
        hidden_sector_separated=bool(hidden_ids) or process != "creation",
        endpoint_incidence_verified=True,
        ancilla_decoupling_verified=ancilla_decoupling,
        coefficient_sector_codespace_dimension=coefficient_dimension,
        fusion_degeneracy_matches_coefficient_shadow=coefficient_matches,
        finite_depth_claim=finite_depth,
        sequential_linear_depth_claim=sequential,
        theorem_scope=theorem_scope,
    )
    result = Toric2DCircuitRealization(
        process=process,
        left_species_id=left_species_id,
        right_species_id=right_species_id,
        output_species_id=output_species,
        coefficient=coefficient,
        pauli_module=module,
        source_terms=source,
        target_terms=target,
        target_local_term_ids=local_ids,
        hidden_sector_term_ids=hidden_ids,
        coefficient_term_ids=coefficient_ids,
        circuit=circuit,
        evidence_status=EvidenceStatus.BOUNDED_EXACT,
        certificate=certificate,
        warnings=(
            "Circuit exactness is finite-template Pauli conjugation, not a proof of minimum circuit depth.",
            "The target local chain omits the recorded hidden-sector term only for nontrivial creation.",
        ),
    )
    if not verify_toric_2d_circuit(result):
        raise ArithmeticError("toric circuit replay failed")
    return result


__all__ = [
    "CircuitReplayCertificate",
    "CliffordCircuit",
    "CliffordGate",
    "CliffordLayer",
    "LatticeHamiltonianTerm",
    "LatticeRealization",
    "LatticeRealizationCertificate",
    "LatticeSiteGeometry",
    "ShortFoldedStringLift",
    "Toric2DCircuitRealization",
    "conjugate_pauli_by_gate",
    "construct_toric_2d_circuit",
    "realize_toric_2d_defect",
    "verify_toric_2d_circuit",
]
