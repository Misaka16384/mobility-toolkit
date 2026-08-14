"""Boundary truncation helpers."""

from __future__ import annotations

import numpy as np

from mobility_toolkit.boundary_gauge.geometry.lattice_coords import lattice_index_to_coordinate_3d


def truncate_operator_2d(
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    matrix_to_be_dealed: np.ndarray,
    truncation: bool,
) -> np.ndarray:
    if Lx - wx < 2 or Ly - wy < 2:
        print("Warning: the truncation box is close to the full lattice size; some operators may be missed.")

    result = []
    num_qudits = Lx * Ly * q

    for op in matrix_to_be_dealed:
        is_fully_supported = True
        truncated_op = np.zeros_like(op)

        for idx in range(num_qudits):
            idx % q
            temp = idx // q
            x = temp % Lx
            y = temp // Lx

            px = op[2 * idx]
            pz = op[2 * idx + 1]

            if px != 0 or pz != 0:
                if x < wx and y < wy:
                    truncated_op[2 * idx] = px
                    truncated_op[2 * idx + 1] = pz
                else:
                    is_fully_supported = False

        if truncation:
            if not is_fully_supported and np.any(truncated_op):
                result.append(truncated_op)
        else:
            if is_fully_supported and np.any(op):
                result.append(op)

    return np.array(result) if len(result) > 0 else np.empty((0, matrix_to_be_dealed.shape[1]), dtype=int)


def truncate_operator_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    wz: int,
    matrix_to_be_dealed: np.ndarray,
    truncation: bool,
) -> np.ndarray:
    if Lx - wx < 2 or Ly - wy < 2 or Lz - wz < 2:
        print("Warning: the truncation box is close to the full lattice size; some operators may be missed.")

    result: list[np.ndarray] = []
    num_qudits = Lx * Ly * Lz * q

    for op in matrix_to_be_dealed:
        is_fully_supported = True
        truncated_op = np.zeros_like(op)

        for idx in range(num_qudits):
            x, y, z, s = lattice_index_to_coordinate_3d(idx, Lx, Ly, Lz, q)
            px = op[2 * idx]
            pz = op[2 * idx + 1]

            if px == 0 and pz == 0:
                continue

            if x < wx and y < wy and z < wz:
                truncated_op[2 * idx] = px % d
                truncated_op[2 * idx + 1] = pz % d
            else:
                is_fully_supported = False

        if truncation:
            if (not is_fully_supported) and np.any(truncated_op):
                result.append(truncated_op)
        else:
            if is_fully_supported and np.any(op):
                result.append(op % d)

    if not result:
        return np.empty((0, matrix_to_be_dealed.shape[1]), dtype=int)
    return np.array(result, dtype=int)


__all__ = [
    "truncate_operator_2d",
    "truncate_operator_3d",
]
