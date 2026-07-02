"""Boundary support reduction helpers."""

from __future__ import annotations

import numpy as np

from mobility_toolkit.boundary_gauge.algebra.support import get_support_weight
from mobility_toolkit.boundary_gauge.geometry.translations import (
    translational_duplicate_map_2d,
    translational_duplicate_map_3d,
)


def simplify_boundary_gauge_ops_2d(
    raw_ops: np.ndarray,
    physical_bulk_rows: np.ndarray,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
) -> np.ndarray:
    """Greedily lower 2D boundary-generator support using local physical moves."""
    if raw_ops.shape[0] == 0:
        return raw_ops.copy()

    ops = raw_ops.copy() % d
    phys_rows = np.array(physical_bulk_rows, dtype=int) % d
    num_ops = ops.shape[0]

    for i in range(num_ops):
        improved = True
        while improved:
            improved = False
            current_weight = get_support_weight(ops[i])

            for stabilizer in phys_rows:
                if not np.any(stabilizer):
                    continue
                for coeff in range(1, d):
                    test_op = (ops[i] + coeff * stabilizer) % d
                    test_weight = get_support_weight(test_op)
                    if test_weight < current_weight:
                        ops[i] = test_op
                        current_weight = test_weight
                        improved = True
                        break
                if improved:
                    break

    global_improved = True
    while global_improved:
        global_improved = False

        for i in range(num_ops):
            local_improved = True
            while local_improved:
                local_improved = False
                current_weight = get_support_weight(ops[i])

                for j in range(num_ops):
                    if i == j:
                        continue

                    translated_ops_j = translational_duplicate_map_2d(
                        ops[j],
                        Lx,
                        Ly,
                        q,
                        d,
                        max_tx=Lx,
                        max_ty=0,
                        retain_full_ops=True,
                        retain_truncated_ops=False,
                    )

                    for translated_op in translated_ops_j:
                        for coeff in range(1, d):
                            test_op = (ops[i] + coeff * translated_op) % d
                            test_weight = get_support_weight(test_op)
                            if test_weight < current_weight:
                                ops[i] = test_op
                                current_weight = test_weight
                                local_improved = True
                                global_improved = True
                                break
                        if local_improved:
                            break
                    if local_improved:
                        break

    final_ops = [op % d for op in ops if np.any(op)]
    if not final_ops:
        return np.empty((0, ops.shape[1]), dtype=int)
    return np.unique(np.array(final_ops, dtype=int), axis=0)


def simplify_boundary_gauge_ops_3d(
    raw_ops: np.ndarray,
    physical_bulk_rows: np.ndarray,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
) -> np.ndarray:
    """Greedily lower 3D boundary-generator support using local physical moves."""
    if raw_ops.shape[0] == 0:
        return raw_ops.copy()

    ops = raw_ops.copy() % d
    phys_rows = np.array(physical_bulk_rows, dtype=int) % d
    num_ops = ops.shape[0]

    for i in range(num_ops):
        improved = True
        while improved:
            improved = False
            current_weight = get_support_weight(ops[i])

            for stabilizer in phys_rows:
                if not np.any(stabilizer):
                    continue
                for coeff in range(1, d):
                    test_op = (ops[i] + coeff * stabilizer) % d
                    test_weight = get_support_weight(test_op)
                    if test_weight < current_weight:
                        ops[i] = test_op
                        current_weight = test_weight
                        improved = True
                        break
                if improved:
                    break

    global_improved = True
    while global_improved:
        global_improved = False

        for i in range(num_ops):
            local_improved = True
            while local_improved:
                local_improved = False
                current_weight = get_support_weight(ops[i])

                for j in range(num_ops):
                    if i == j:
                        continue

                    translated_ops_j = translational_duplicate_map_3d(
                        ops[j],
                        Lx,
                        Ly,
                        Lz,
                        q,
                        d,
                        max_tx=Lx,
                        max_ty=Ly,
                        max_tz=0,
                        retain_full_ops=True,
                        retain_truncated_ops=False,
                    )

                    for translated_op in translated_ops_j:
                        for coeff in range(1, d):
                            test_op = (ops[i] + coeff * translated_op) % d
                            test_weight = get_support_weight(test_op)
                            if test_weight < current_weight:
                                ops[i] = test_op
                                current_weight = test_weight
                                local_improved = True
                                global_improved = True
                                break
                        if local_improved:
                            break
                    if local_improved:
                        break

    final_ops = [op % d for op in ops if np.any(op)]
    if not final_ops:
        return np.empty((0, ops.shape[1]), dtype=int)
    return np.unique(np.array(final_ops, dtype=int), axis=0)

__all__ = [
    "simplify_boundary_gauge_ops_2d",
    "simplify_boundary_gauge_ops_3d",
]
