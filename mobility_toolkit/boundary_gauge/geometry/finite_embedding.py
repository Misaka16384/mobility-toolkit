"""Finite-lattice stabilizer embedding helpers."""

from __future__ import annotations

from typing import Dict

import numpy as np

from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D, GeneratorTerm3D, QuditCoord3D, StabilizerDict


def apply_stabilizers_on_lattice_2d(
    Lx: int,
    Ly: int,
    d: int,
    generators: list[list[GeneratorTerm2D]],
    qudit_to_index: dict[tuple[int, int, int], int],
) -> list[StabilizerDict]:
    valid_stabilizers = []

    for ty in range(Ly):
        for tx in range(Lx):
            for gen_poly in generators:
                current_stab_op = {}
                is_fully_supported = True

                for coeff, dx, dy, s, p_type in gen_poly:
                    qx = (tx + dx) % Lx
                    qy = ty + dy
                    qs = s

                    if not (0 <= qy < Ly):
                        is_fully_supported = False
                        break

                    q_idx = qudit_to_index[(qx, qy, qs)]
                    if q_idx not in current_stab_op:
                        current_stab_op[q_idx] = [0, 0]

                    current_stab_op[q_idx][p_type] = (current_stab_op[q_idx][p_type] + coeff) % d

                if is_fully_supported:
                    valid_stabilizers.append(current_stab_op)

    return valid_stabilizers


def apply_stabilizers_on_lattice_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    d: int,
    generators: list[list[GeneratorTerm3D]],
    qudit_to_index: dict[QuditCoord3D, int],
) -> list[StabilizerDict]:
    valid_stabilizers: list[StabilizerDict] = []

    for tz in range(Lz):
        for ty in range(Ly):
            for tx in range(Lx):
                for gen_poly in generators:
                    current_stab_op: Dict[int, list[int]] = {}
                    is_fully_supported = True

                    for coeff, dx, dy, dz, s, p_type in gen_poly:
                        qx = (tx + dx) % Lx
                        qy = (ty + dy) % Ly
                        qz = tz + dz

                        if not (0 <= qz < Lz):
                            is_fully_supported = False
                            break

                        q_idx = qudit_to_index[(qx, qy, qz, s)]
                        if q_idx not in current_stab_op:
                            current_stab_op[q_idx] = [0, 0]

                        current_stab_op[q_idx][p_type] = (current_stab_op[q_idx][p_type] + coeff) % d

                    if not is_fully_supported:
                        continue

                    cleaned_stab: StabilizerDict = {}
                    for q_idx, (pow_x, pow_z) in current_stab_op.items():
                        px = pow_x % d
                        pz = pow_z % d
                        if px != 0 or pz != 0:
                            cleaned_stab[q_idx] = (px, pz)

                    if cleaned_stab:
                        valid_stabilizers.append(cleaned_stab)

    return valid_stabilizers


def construct_M1_matrix_2d(*args, **kwargs) -> tuple[np.ndarray, list[StabilizerDict]]:
    from mobility_toolkit.boundary_gauge.algebra.commutation import construct_M1_matrix_2d as _construct

    return _construct(*args, **kwargs)


def construct_M1_matrix_3d(*args, **kwargs) -> tuple[np.ndarray, list[StabilizerDict]]:
    from mobility_toolkit.boundary_gauge.algebra.commutation import construct_M1_matrix_3d as _construct

    return _construct(*args, **kwargs)


__all__ = [
    "apply_stabilizers_on_lattice_2d",
    "apply_stabilizers_on_lattice_3d",
    "construct_M1_matrix_2d",
    "construct_M1_matrix_3d",
]
