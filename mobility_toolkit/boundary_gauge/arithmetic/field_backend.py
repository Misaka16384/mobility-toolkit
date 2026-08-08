"""Finite-field row-span helpers."""

from __future__ import annotations

from typing import List

import numpy as np


def _row_basis_field(mat: np.ndarray, p: int) -> tuple[np.ndarray, list[int]]:
    """Return an exact reduced row basis over the finite field F_p."""
    arr = np.array(mat, dtype=int) % p
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.size == 0 or arr.shape[0] == 0:
        ncols = arr.shape[1] if arr.ndim == 2 else 0
        return np.empty((0, ncols), dtype=int), []

    m, n = arr.shape
    row = 0
    pivots: List[int] = []
    for col in range(n):
        pivot = None
        for r in range(row, m):
            if arr[r, col] % p != 0:
                pivot = r
                break
        if pivot is None:
            continue

        if pivot != row:
            arr[[row, pivot]] = arr[[pivot, row]]

        inv = pow(int(arr[row, col]) % p, -1, p)
        arr[row] = (inv * arr[row]) % p

        # ⚡ Bolt: Vectorize row elimination over finite field to avoid Python loop overhead
        factors = arr[:, col] % p
        factors[row] = 0
        mask = factors != 0
        if np.any(mask):
            arr[mask] = (arr[mask] - factors[mask, np.newaxis] * arr[row]) % p

        pivots.append(col)
        row += 1
        if row == m:
            break

    basis = arr[:row] % p
    basis = basis[np.any(basis != 0, axis=1)] if basis.shape[0] > 0 else basis
    return basis, pivots


class FieldSpanTester:
    """Exact row-span membership tester over a prime finite field."""

    def __init__(self, B_rows: np.ndarray, p: int):
        self.p = int(p)
        self.basis, self.pivots = _row_basis_field(B_rows, p)

    def contains(self, v: np.ndarray) -> bool:
        vec = np.array(v, dtype=int).reshape(-1) % self.p
        if self.basis.shape[0] == 0:
            return not np.any(vec)
        w = vec.copy()
        for row_idx, col in enumerate(self.pivots):
            if w[col] % self.p != 0:
                factor = int(w[col]) % self.p
                w = (w - factor * self.basis[row_idx]) % self.p
        return not np.any(w % self.p)


__all__ = ["FieldSpanTester", "_row_basis_field"]
