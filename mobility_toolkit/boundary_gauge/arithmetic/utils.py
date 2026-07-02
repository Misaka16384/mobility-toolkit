"""Small arithmetic utilities shared by finite-field and Z_d backends."""

from __future__ import annotations

import numpy as np


def is_prime_int(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    factor = 3
    while factor * factor <= n:
        if n % factor == 0:
            return False
        factor += 2
    return True


def _normalize_rows(mat: np.ndarray, d: int) -> np.ndarray:
    arr = np.array(mat, dtype=int)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.size == 0:
        ncols = arr.shape[1] if arr.ndim == 2 else 0
        return np.empty((0, ncols), dtype=int)
    arr = arr % d
    if arr.shape[0] == 0:
        return arr
    keep = np.any(arr != 0, axis=1)
    arr = arr[keep]
    if arr.shape[0] == 0:
        return np.empty((0, arr.shape[1]), dtype=int)
    return np.unique(arr, axis=0)


__all__ = ["_normalize_rows", "is_prime_int"]
