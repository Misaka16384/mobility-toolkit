"""3D reporting helpers for boundary operators."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from mobility_toolkit.boundary_gauge.algebra.support import get_support_weight
from mobility_toolkit.boundary_gauge.algebra.pauli_vectors import operator_terms_3d


def print_boundary_operators_3d(
    title: str,
    ops: np.ndarray,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    max_ops: int | None = None,
) -> None:
    print("\n" + title)
    print("-" * len(title))
    print(f"operator matrix shape = {ops.shape}")
    if ops.shape[0] == 0:
        print("No nontrivial boundary gauge operator generators found in this search patch.")
        return

    n_ops = ops.shape[0] if max_ops is None else min(max_ops, ops.shape[0])
    for i in range(n_ops):
        terms = operator_terms_3d(ops[i], Lx, Ly, Lz, q, d, qudit_positions)
        print(f"G[{i}] weight={get_support_weight(ops[i])}: " + " * ".join(terms))

    if max_ops is not None and ops.shape[0] > max_ops:
        print(f"... {ops.shape[0] - max_ops} additional generators omitted by max_ops.")

__all__ = [
    "operator_terms_3d",
    "print_boundary_operators_3d",
]
