"""Dense Pauli-vector conversion and formatting helpers."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from mobility_toolkit.boundary_gauge.arithmetic.membership import _normalize_rows, is_prime_int
from mobility_toolkit.boundary_gauge.arithmetic.row_generators import simplify_relations
from mobility_toolkit.boundary_gauge.core.types import StabilizerDict
from mobility_toolkit.boundary_gauge.geometry.lattice_coords import (
    lattice_index_to_coordinate_2d,
    lattice_index_to_coordinate_3d,
)


def convert_bulk_to_S_mat_2d(
    bulk_stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    q: int,
    d: int,
) -> np.ndarray:
    num_qudits = Lx * Ly * q
    s_mat = np.zeros((len(bulk_stabilizers), 2 * num_qudits), dtype=int)
    for row, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            s_mat[row, 2 * q_idx] = sx % d
            s_mat[row, 2 * q_idx + 1] = sz % d
    if is_prime_int(d):
        return simplify_relations(s_mat, d)
    return _normalize_rows(s_mat, d)


def convert_bulk_to_S_mat_3d(
    bulk_stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
) -> np.ndarray:
    num_qudits = Lx * Ly * Lz * q
    s_mat = np.zeros((len(bulk_stabilizers), 2 * num_qudits), dtype=int)
    for row, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            s_mat[row, 2 * q_idx] = sx % d
            s_mat[row, 2 * q_idx + 1] = sz % d
    if is_prime_int(d):
        return simplify_relations(s_mat, d)
    return _normalize_rows(s_mat, d)


def convert_bulk_to_physical_rows_3d(
    bulk_stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
) -> np.ndarray:
    """Return one dense row per actual finite-lattice 3D bulk stabilizer."""
    num_qudits = Lx * Ly * Lz * q
    rows = np.zeros((len(bulk_stabilizers), 2 * num_qudits), dtype=int)
    for row, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            rows[row, 2 * q_idx] = sx % d
            rows[row, 2 * q_idx + 1] = sz % d
    return rows % d


def _format_pauli(px: int, pz: int) -> str:
    parts = []
    if px != 0:
        parts.append("X" if px == 1 else f"X^{px}")
    if pz != 0:
        parts.append("Z" if pz == 1 else f"Z^{pz}")
    return "".join(parts) if parts else "I"


def _format_pauli_label(exp_x: int, exp_z: int) -> str:
    return _format_pauli(exp_x, exp_z)


def _format_pauli_math(exp_x: int, exp_z: int) -> str:
    parts = []
    if exp_x != 0:
        parts.append("X" if exp_x == 1 else f"X^{exp_x}")
    if exp_z != 0:
        parts.append("Z" if exp_z == 1 else f"Z^{exp_z}")
    return "$" + "".join(parts) + "$" if parts else ""


def operator_terms_2d(
    op_vector: np.ndarray,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
) -> list[str]:
    terms: list[str] = []
    for idx in range(Lx * Ly * q):
        px = int(op_vector[2 * idx]) % d
        pz = int(op_vector[2 * idx + 1]) % d
        if px == 0 and pz == 0:
            continue
        x, y, s = lattice_index_to_coordinate_2d(idx, Lx, Ly, q)
        pos = (x + qudit_positions[s][0], y + qudit_positions[s][1])
        terms.append(f"{_format_pauli(px, pz)}@(cell=({x},{y}), s={s}, pos=({pos[0]:g},{pos[1]:g}))")
    return terms


def operator_terms_3d(
    op_vector: np.ndarray,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
) -> list[str]:
    terms: list[str] = []
    for idx in range(Lx * Ly * Lz * q):
        px = int(op_vector[2 * idx]) % d
        pz = int(op_vector[2 * idx + 1]) % d
        if px == 0 and pz == 0:
            continue
        x, y, z, s = lattice_index_to_coordinate_3d(idx, Lx, Ly, Lz, q)
        pos = (x + qudit_positions[s][0], y + qudit_positions[s][1], z + qudit_positions[s][2])
        terms.append(f"{_format_pauli(px, pz)}@(cell=({x},{y},{z}), s={s}, pos=({pos[0]:g},{pos[1]:g},{pos[2]:g}))")
    return terms


__all__ = [
    "_format_pauli",
    "_format_pauli_label",
    "_format_pauli_math",
    "convert_bulk_to_S_mat_2d",
    "convert_bulk_to_S_mat_3d",
    "convert_bulk_to_physical_rows_3d",
    "operator_terms_2d",
    "operator_terms_3d",
]
