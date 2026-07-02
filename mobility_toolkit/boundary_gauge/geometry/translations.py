"""Translation duplicate maps."""

from __future__ import annotations

import numpy as np

from mobility_toolkit.boundary_gauge.geometry.lattice_coords import (
    lattice_coordinate_to_index_3d,
    lattice_index_to_coordinate_3d,
)


def translational_duplicate_map_2d(
    op_vector: np.ndarray,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    max_tx: int,
    max_ty: int,
    retain_full_ops: bool = True,
    retain_truncated_ops: bool = False,
) -> np.ndarray:
    support = []
    num_qudits = Lx * Ly * q
    for idx in range(num_qudits):
        if op_vector[2 * idx] != 0 or op_vector[2 * idx + 1] != 0:
            s = idx % q
            temp = idx // q
            x = temp % Lx
            y = temp // Lx
            support.append((x, y, s, op_vector[2 * idx], op_vector[2 * idx + 1]))

    if not support:
        return np.empty((0, len(op_vector)), dtype=int)

    full_ops = []
    truncated_ops = []

    for tx in range(-max_tx, max_tx + 1):
        for ty in range(-max_ty, max_ty + 1):
            new_op = np.zeros_like(op_vector)
            is_truncated = False
            is_empty = True

            for x, y, s, px, pz in support:
                nx = (x + tx) % Lx
                ny = y + ty

                if 0 <= ny < Ly:
                    n_idx = (ny * Lx + nx) * q + s
                    new_op[2 * n_idx] = px
                    new_op[2 * n_idx + 1] = pz
                    is_empty = False
                else:
                    is_truncated = True

            if is_empty:
                continue

            if is_truncated:
                truncated_ops.append(new_op)
            else:
                full_ops.append(new_op)

    results = []
    if retain_full_ops and len(full_ops) > 0:
        results.append(np.array(full_ops))
    if retain_truncated_ops and len(truncated_ops) > 0:
        results.append(np.array(truncated_ops))

    if len(results) > 0:
        final_mat = np.vstack(results)
        return np.unique(final_mat, axis=0)
    return np.empty((0, len(op_vector)), dtype=int)


def translational_duplicate_map_3d(
    op_vector: np.ndarray,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    max_tx: int,
    max_ty: int,
    max_tz: int,
    retain_full_ops: bool = True,
    retain_truncated_ops: bool = False,
) -> np.ndarray:
    support = []
    num_qudits = Lx * Ly * Lz * q
    for idx in range(num_qudits):
        exp_x = int(op_vector[2 * idx])
        exp_z = int(op_vector[2 * idx + 1])
        if exp_x == 0 and exp_z == 0:
            continue
        x, y, z, s = lattice_index_to_coordinate_3d(idx, Lx, Ly, Lz, q)
        support.append((x, y, z, s, exp_x, exp_z))

    if not support:
        return np.empty((0, len(op_vector)), dtype=int)

    full_ops: list[np.ndarray] = []
    truncated_ops: list[np.ndarray] = []

    for tx in range(-max_tx, max_tx + 1):
        for ty in range(-max_ty, max_ty + 1):
            for tz in range(-max_tz, max_tz + 1):
                new_op = np.zeros_like(op_vector)
                is_truncated = False
                is_empty = True

                for x, y, z, s, px, pz in support:
                    nx = (x + tx) % Lx
                    ny = (y + ty) % Ly
                    nz = z + tz

                    if 0 <= nz < Lz:
                        n_idx = lattice_coordinate_to_index_3d(nx, ny, nz, s, Lx, Ly, Lz, q)
                        new_op[2 * n_idx] = (new_op[2 * n_idx] + px) % d
                        new_op[2 * n_idx + 1] = (new_op[2 * n_idx + 1] + pz) % d
                        is_empty = False
                    else:
                        is_truncated = True

                if is_empty:
                    continue

                if is_truncated:
                    truncated_ops.append(new_op)
                else:
                    full_ops.append(new_op)

    results: list[np.ndarray] = []
    if retain_full_ops and full_ops:
        results.append(np.array(full_ops, dtype=int))
    if retain_truncated_ops and truncated_ops:
        results.append(np.array(truncated_ops, dtype=int))

    if not results:
        return np.empty((0, len(op_vector)), dtype=int)

    final_mat = np.vstack(results) % d
    return np.unique(final_mat, axis=0)


__all__ = [
    "translational_duplicate_map_2d",
    "translational_duplicate_map_3d",
]
