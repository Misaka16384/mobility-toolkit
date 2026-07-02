"""Support helpers for dense Pauli vectors."""

from __future__ import annotations

import numpy as np


def get_support_weight(op_vector: np.ndarray) -> int:
    """Count qudits with a non-identity Pauli action.

    Dense Pauli vectors use the layout ``[X0, Z0, X1, Z1, ...]``.
    """
    op = np.asarray(op_vector)
    x_parts = op[0::2]
    z_parts = op[1::2]
    return int(np.sum((x_parts != 0) | (z_parts != 0)))


__all__ = ["get_support_weight"]
