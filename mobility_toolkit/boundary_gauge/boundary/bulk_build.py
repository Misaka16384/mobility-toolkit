"""Bulk stabilizer matrix construction helpers."""

from __future__ import annotations

import numpy as np

from mobility_toolkit.boundary_gauge.algebra.commutation import (
    construct_M1_matrix_2d,
    construct_M1_matrix_3d,
)
from mobility_toolkit.boundary_gauge.algebra.pauli_vectors import (
    convert_bulk_to_S_mat_2d,
    convert_bulk_to_S_mat_3d,
    convert_bulk_to_physical_rows_3d,
)
from mobility_toolkit.boundary_gauge.core.types import StabilizerDict


def convert_bulk_to_physical_rows_2d(
    bulk_stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    q: int,
    d: int,
) -> np.ndarray:
    """Return one dense row per actual finite-lattice 2D bulk stabilizer.

    This intentionally does not row-reduce the result. Local support reduction
    needs actual physical stabilizer moves, not a compressed span basis.
    """
    num_qudits = Lx * Ly * q
    rows = np.zeros((len(bulk_stabilizers), 2 * num_qudits), dtype=int)
    for row, stab in enumerate(bulk_stabilizers):
        for q_idx, (sx, sz) in stab.items():
            rows[row, 2 * q_idx] = sx % d
            rows[row, 2 * q_idx + 1] = sz % d
    return rows % d


__all__ = [
    "convert_bulk_to_S_mat_2d",
    "convert_bulk_to_S_mat_3d",
    "convert_bulk_to_physical_rows_2d",
    "convert_bulk_to_physical_rows_3d",
    "construct_M1_matrix_2d",
    "construct_M1_matrix_3d",
]
