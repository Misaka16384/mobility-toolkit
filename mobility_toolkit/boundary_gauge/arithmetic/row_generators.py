"""Row-generator simplification over finite fields and Z_d."""

from __future__ import annotations

from typing import Optional

import numpy as np

from mobility_toolkit.boundary_gauge.arithmetic.field_backend import _row_basis_field
from mobility_toolkit.boundary_gauge.arithmetic.utils import _normalize_rows, is_prime_int
from mobility_toolkit.boundary_gauge.arithmetic.zd_backend import ZdSpanTester


def simplify_relations(relations: np.ndarray, d: int) -> np.ndarray:
    """Return a reduced generating set for the row span over Z_d.

    For prime ``d`` this is ordinary reduced row basis over F_d. For composite
    ``d`` this greedily keeps rows not already in the exact Z_d span.
    """
    arr = _normalize_rows(relations, d)
    if arr.size == 0 or arr.shape[0] == 0:
        ncols = arr.shape[1] if arr.ndim == 2 else 0
        return np.empty((0, ncols), dtype=int)

    if is_prime_int(d):
        basis, _ = _row_basis_field(arr, d)
        return basis % d

    basis_rows: list[np.ndarray] = []
    tester: Optional[ZdSpanTester] = None
    for row in arr:
        if tester is None or not tester.contains(row):
            basis_rows.append(np.array(row, dtype=int) % d)
            tester = ZdSpanTester(np.array(basis_rows, dtype=int), d)
    if not basis_rows:
        return np.empty((0, arr.shape[1]), dtype=int)
    return np.array(basis_rows, dtype=int) % d


__all__ = ["simplify_relations"]
