"""Commutation matrix construction helpers."""

from __future__ import annotations

import numpy as np

from mobility_toolkit.boundary_gauge.arithmetic.kernel import (
    extract_zero_syndrome_operators,
    modified_gaussian_elimination,
)
from mobility_toolkit.boundary_gauge.arithmetic.membership import _normalize_rows
from mobility_toolkit.boundary_gauge.arithmetic.row_generators import simplify_relations
from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D, GeneratorTerm3D, StabilizerDict
from mobility_toolkit.boundary_gauge.geometry.finite_embedding import (
    apply_stabilizers_on_lattice_2d,
    apply_stabilizers_on_lattice_3d,
)
from mobility_toolkit.boundary_gauge.geometry.lattice_coords import (
    generate_lattice_qudits_2d,
    generate_lattice_qudits_3d,
)


def construct_M1_matrix_2d(
    Lx: int,
    Ly: int,
    d: int,
    q: int,
    stabilizer_generators: list[list[GeneratorTerm2D]],
) -> tuple[np.ndarray, list[StabilizerDict]]:
    """Construct the 2D single-Pauli-vs-bulk commutation matrix."""
    qudits = generate_lattice_qudits_2d(Lx, Ly, q)
    num_qudits = len(qudits)
    qudit_to_index = {qudit: i for i, qudit in enumerate(qudits)}

    bulk_stabilizers = apply_stabilizers_on_lattice_2d(Lx, Ly, d, stabilizer_generators, qudit_to_index)
    num_stabs = len(bulk_stabilizers)

    print(f"Lattice Setup: {Lx}x{Ly} cells, {q} qudits/cell.")
    print(f"Total Qudits: {num_qudits}")
    print(f"Total Bulk Stabilizers retained: {num_stabs}")

    m1 = np.zeros((2 * num_qudits, num_stabs), dtype=int)
    for col, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            m1[2 * q_idx, col] = (-sz) % d
            m1[2 * q_idx + 1, col] = sx % d

    return m1, bulk_stabilizers


def construct_M1_matrix_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    d: int,
    q: int,
    stabilizer_generators: list[list[GeneratorTerm3D]],
) -> tuple[np.ndarray, list[StabilizerDict]]:
    """Construct the 3D single-Pauli-vs-bulk commutation matrix."""
    qudits = generate_lattice_qudits_3d(Lx, Ly, Lz, q)
    num_qudits = len(qudits)
    qudit_to_index = {qudit: i for i, qudit in enumerate(qudits)}

    bulk_stabilizers = apply_stabilizers_on_lattice_3d(Lx, Ly, Lz, d, stabilizer_generators, qudit_to_index)
    num_stabs = len(bulk_stabilizers)

    print(f"Lattice Setup: {Lx}x{Ly}x{Lz} cells, {q} qudits/cell.")
    print(f"Total Qudits: {num_qudits}")
    print(f"Total Bulk Stabilizers retained: {num_stabs}")

    m1 = np.zeros((2 * num_qudits, num_stabs), dtype=int)
    for col, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            m1[2 * q_idx, col] = (-sz) % d
            m1[2 * q_idx + 1, col] = sx % d

    return m1, bulk_stabilizers


def construct_M1_w_and_extract_O_w_2d(
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    bulk_stabilizers: list[StabilizerDict],
    patch_origin: tuple[int, int] = (0, 0),
) -> np.ndarray:
    x0, y0 = patch_origin
    if wx > Lx or wy > Ly:
        raise ValueError("The local search box must fit inside the finite lattice.")
    if not (0 <= y0 <= Ly - wy):
        raise ValueError("patch_origin[1] must satisfy 0 <= y0 <= Ly - wy for the open y direction.")

    qudits_full = generate_lattice_qudits_2d(Lx, Ly, q)
    qudit_to_index_full = {q_tuple: i for i, q_tuple in enumerate(qudits_full)}
    qudits_w = generate_lattice_qudits_2d(wx, wy, q)
    num_qudits_w = len(qudits_w)

    m1_w = np.zeros((2 * num_qudits_w, len(bulk_stabilizers)), dtype=int)
    for col, stab in enumerate(bulk_stabilizers):
        for w_idx, (x_local, y_local, s) in enumerate(qudits_w):
            full_q_tuple = ((x0 + x_local) % Lx, y0 + y_local, s)
            full_idx = qudit_to_index_full[full_q_tuple]
            if full_idx in stab:
                sx, sz = stab[full_idx]
                m1_w[2 * w_idx, col] = (-sz) % d
                m1_w[2 * w_idx + 1, col] = sx % d

    raw_r1_w = modified_gaussian_elimination(m1_w, d)
    r1_w = simplify_relations(raw_r1_w, d)

    v_w = np.eye(2 * num_qudits_w, dtype=int)
    o_w_sub = extract_zero_syndrome_operators(r1_w, v_w, d)
    o_w_sub = _normalize_rows(o_w_sub, d)

    o_w_full = np.zeros((o_w_sub.shape[0], 2 * len(qudits_full)), dtype=int)
    for i in range(o_w_sub.shape[0]):
        for w_idx, (x_local, y_local, s) in enumerate(qudits_w):
            full_q_tuple = ((x0 + x_local) % Lx, y0 + y_local, s)
            full_idx = qudit_to_index_full[full_q_tuple]
            o_w_full[i, 2 * full_idx] = o_w_sub[i, 2 * w_idx]
            o_w_full[i, 2 * full_idx + 1] = o_w_sub[i, 2 * w_idx + 1]

    return _normalize_rows(o_w_full, d)


def construct_M1_w_and_extract_O_w_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    wz: int,
    bulk_stabilizers: list[StabilizerDict],
    patch_origin: tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    x0, y0, z0 = patch_origin
    if wx > Lx or wy > Ly or wz > Lz:
        raise ValueError("The local search box must fit inside the finite lattice.")
    if not (0 <= z0 <= Lz - wz):
        raise ValueError("patch_origin[2] must satisfy 0 <= z0 <= Lz - wz for the open z direction.")

    qudits_full = generate_lattice_qudits_3d(Lx, Ly, Lz, q)
    qudit_to_index_full = {q_tuple: i for i, q_tuple in enumerate(qudits_full)}
    qudits_w = generate_lattice_qudits_3d(wx, wy, wz, q)
    num_qudits_w = len(qudits_w)

    m1_w = np.zeros((2 * num_qudits_w, len(bulk_stabilizers)), dtype=int)
    for col, stab in enumerate(bulk_stabilizers):
        for w_idx, (x_local, y_local, z_local, s) in enumerate(qudits_w):
            full_q_tuple = ((x0 + x_local) % Lx, (y0 + y_local) % Ly, z0 + z_local, s)
            full_idx = qudit_to_index_full[full_q_tuple]
            if full_idx in stab:
                sx, sz = stab[full_idx]
                m1_w[2 * w_idx, col] = (-sz) % d
                m1_w[2 * w_idx + 1, col] = sx % d

    raw_r1_w = modified_gaussian_elimination(m1_w, d)
    r1_w = simplify_relations(raw_r1_w, d)

    v_w = np.eye(2 * num_qudits_w, dtype=int)
    o_w_sub = extract_zero_syndrome_operators(r1_w, v_w, d)
    o_w_sub = _normalize_rows(o_w_sub, d)

    o_w_full = np.zeros((o_w_sub.shape[0], 2 * len(qudits_full)), dtype=int)
    for i in range(o_w_sub.shape[0]):
        for w_idx, (x_local, y_local, z_local, s) in enumerate(qudits_w):
            full_q_tuple = ((x0 + x_local) % Lx, (y0 + y_local) % Ly, z0 + z_local, s)
            full_idx = qudit_to_index_full[full_q_tuple]
            o_w_full[i, 2 * full_idx] = o_w_sub[i, 2 * w_idx]
            o_w_full[i, 2 * full_idx + 1] = o_w_sub[i, 2 * w_idx + 1]

    return _normalize_rows(o_w_full, d)


__all__ = [
    "construct_M1_matrix_2d",
    "construct_M1_matrix_3d",
    "construct_M1_w_and_extract_O_w_2d",
    "construct_M1_w_and_extract_O_w_3d",
]
