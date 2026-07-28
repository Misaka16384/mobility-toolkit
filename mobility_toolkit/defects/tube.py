"""Deleted-tube cellular representation and exact line-rewrite comparison."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.codes import StabilizerCodeSpec
from mobility_toolkit.defects.projection import PinnedSubsystemProjection
from mobility_toolkit.finite.stabilizer import FiniteStabilizerAnalysis
from mobility_toolkit.geometry.cell_complex import (
    CellularCode,
    CellularPauliConvention,
    CubicalComplex,
    FiniteCellComplex,
    cellular_stabilizer_code,
)


@dataclass(frozen=True)
class LineTubeRepresentationCertificate:
    removed_cube_cell_ids: Tuple[str, ...]
    removed_internal_plaquette_ids: Tuple[str, ...]
    retained_tube_wall_plaquette_ids: Tuple[str, ...]
    boundary_squared_zero_verified: bool
    pauli_modules_identical: bool
    local_phase_aware_generator_sets_identical: bool
    fixed_sector_phase_aware_generator_sets_identical: bool
    equivalence_scope: str

    SCHEMA_ID = "mobility_toolkit.line_tube_representation_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.boundary_squared_zero_verified
            and self.pauli_modules_identical
            and self.local_phase_aware_generator_sets_identical
            and self.fixed_sector_phase_aware_generator_sets_identical
        )

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_squared_zero_verified": self.boundary_squared_zero_verified,
            "equivalence_scope": self.equivalence_scope,
            "fixed_sector_phase_aware_generator_sets_identical": self.fixed_sector_phase_aware_generator_sets_identical,
            "local_phase_aware_generator_sets_identical": self.local_phase_aware_generator_sets_identical,
            "pauli_modules_identical": self.pauli_modules_identical,
            "removed_cube_cell_ids": self.removed_cube_cell_ids,
            "removed_internal_plaquette_ids": self.removed_internal_plaquette_ids,
            "retained_tube_wall_plaquette_ids": self.retained_tube_wall_plaquette_ids,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class TubularDeletedRepresentation:
    tube_cell_complex: FiniteCellComplex
    local_cellular_code: CellularCode
    fixed_sector_code: StabilizerCodeSpec
    local_analysis: FiniteStabilizerAnalysis
    fixed_sector_analysis: FiniteStabilizerAnalysis
    certificate: LineTubeRepresentationCertificate

    SCHEMA_ID = "mobility_toolkit.tubular_deleted_representation.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "fixed_sector_analysis": self.fixed_sector_analysis,
            "fixed_sector_code": self.fixed_sector_code,
            "local_analysis": self.local_analysis,
            "local_cellular_code": self.local_cellular_code,
            "schema": self.SCHEMA_ID,
            "tube_cell_complex": self.tube_cell_complex,
        }


def compile_deleted_tube_representation(
    complex_: CubicalComplex,
    line_defects: Sequence[object],
    local_pinned_elimination: PinnedSubsystemProjection,
    fixed_sector_pinned_elimination: PinnedSubsystemProjection,
) -> TubularDeletedRepresentation:
    """Delete tube-volume 3-cells while retaining explicit wall/cap 2-cells.

    The internal plaquettes fixed by the direct line rewrite are removed.  All
    other plaquettes incident to a deleted cube remain as an explicit tube wall
    or endpoint cap.  For the reference construction this yields exactly the
    phase-aware generator set obtained by eliminating the pinned condensate
    qubits from the direct line representation.
    """

    chain = complex_.chain_complex
    removed_cubes = tuple(
        sorted(
            {
                cube_id
                for line in line_defects
                for cube_id in line.cube_cell_ids
            }
        )
    )
    removed_faces = tuple(
        sorted(
            {
                face_id
                for line in line_defects
                for face_id in line.condensate_plaquette_ids
            }
        )
    )
    cube_ids = chain.cell_ids_by_dimension[3]
    face_ids = chain.cell_ids_by_dimension[2]
    cube_index = {cell_id: index for index, cell_id in enumerate(cube_ids)}
    face_index = {cell_id: index for index, cell_id in enumerate(face_ids)}
    if not set(removed_cubes).issubset(cube_index) or not set(removed_faces).issubset(
        face_index
    ):
        raise ValueError("deleted tube cells are absent from the host cell complex")
    removed_cube_indices = {cube_index[cell_id] for cell_id in removed_cubes}
    removed_face_indices = {face_index[cell_id] for cell_id in removed_faces}
    for row, column, coefficient in chain.boundary_maps[3].entries:
        if row in removed_face_indices and coefficient % 2 and column not in removed_cube_indices:
            raise ValueError(
                "a condensate plaquette touches a retained cube and is not an internal tube face"
            )

    kept_face_indices = tuple(
        index for index in range(len(face_ids)) if index not in removed_face_indices
    )
    kept_cube_indices = tuple(
        index for index in range(len(cube_ids)) if index not in removed_cube_indices
    )
    maps = (
        chain.boundary_maps[0],
        chain.boundary_maps[1],
        chain.boundary_maps[2].select_columns(kept_face_indices),
        chain.boundary_maps[3]
        .select_rows(kept_face_indices)
        .select_columns(kept_cube_indices),
    )
    tube_chain = FiniteCellComplex(
        (
            chain.cell_ids_by_dimension[0],
            chain.cell_ids_by_dimension[1],
            tuple(face_ids[index] for index in kept_face_indices),
            tuple(cube_ids[index] for index in kept_cube_indices),
        ),
        maps,
        tuple(chain.assumptions)
        + (
            "tube-volume 3-cells deleted",
            "condensate internal 2-cells deleted",
            "tube wall and endpoint-cap 2-cells retained",
        ),
    )
    local_cellular = cellular_stabilizer_code(
        tube_chain,
        2,
        2,
        convention=CellularPauliConvention.FOURIER_DUAL,
    )
    nontrivial_records = tuple(
        record for record in local_cellular.check_records if not record.operator.is_identity
    )
    if len(nontrivial_records) != len(local_cellular.check_records):
        normalized_code = StabilizerCodeSpec(
            local_cellular.code.pauli_module,
            tuple(record.operator for record in nontrivial_records),
            tuple(local_cellular.code.assumptions)
            + ("identity checks created by tube deletion omitted",),
        )
        local_cellular = CellularCode(
            local_cellular.chain_complex,
            local_cellular.qudit_degree,
            local_cellular.coefficient_modulus,
            normalized_code,
            local_cellular.convention,
            nontrivial_records,
            tuple(
                record.cell_id
                for record in nontrivial_records
                if record.pauli_kind == "x"
            ),
            tuple(
                record.cell_id
                for record in nontrivial_records
                if record.pauli_kind == "z"
            ),
        )
    projected_local = local_pinned_elimination.projected_code
    projected_fixed = fixed_sector_pinned_elimination.projected_code
    sector_operators = tuple(
        term.operator
        for term in fixed_sector_pinned_elimination.projected_terms
        if term.term_id.startswith("sector:q-gamma:")
    )
    fixed_code = StabilizerCodeSpec(
        local_cellular.code.pauli_module,
        local_cellular.code.generators + sector_operators,
        (
            "deleted tubular cellular representation with fixed Cheshire charge sectors",
        ),
    )

    removed_cube_set = set(removed_cubes)
    removed_face_set = set(removed_faces)
    faces_incident_to_removed = set()
    for row, column, coefficient in chain.boundary_maps[3].entries:
        if coefficient % 2 and cube_ids[column] in removed_cube_set:
            faces_incident_to_removed.add(face_ids[row])
    wall_faces = tuple(sorted(faces_incident_to_removed - removed_face_set))
    certificate = LineTubeRepresentationCertificate(
        removed_cubes,
        removed_faces,
        wall_faces,
        not maps[1].matmul(maps[2]).entries
        and not maps[2].matmul(maps[3]).entries,
        local_cellular.code.pauli_module == projected_local.pauli_module
        == projected_fixed.pauli_module,
        local_cellular.code.generators == projected_local.generators,
        fixed_code.generators == projected_fixed.generators,
        "Exact identity of phase-aware finite stabilizer generator sets after "
        "direct-line condensate pins are eliminated; the deleted-cell model retains "
        "explicit tube-wall and endpoint-cap plaquettes. No tube-radius shrinking or "
        "finite-depth phase-equivalence statement is made.",
    )
    if not certificate.verified:
        raise ArithmeticError(
            "direct line rewrite and deleted-tube cellular representation disagree"
        )
    return TubularDeletedRepresentation(
        tube_chain,
        local_cellular,
        fixed_code,
        local_pinned_elimination.projected_analysis,
        fixed_sector_pinned_elimination.projected_analysis,
        certificate,
    )


__all__ = [
    "LineTubeRepresentationCertificate",
    "TubularDeletedRepresentation",
    "compile_deleted_tube_representation",
]
