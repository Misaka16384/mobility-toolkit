"""Z_d row-span membership helpers."""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np
import sympy as sp

from mobility_toolkit.boundary_gauge.arithmetic.smith_backend import smith_normal_decomp
from mobility_toolkit.boundary_gauge.arithmetic.utils import _normalize_rows


class ZdSpanTester:
    """Exact row-span membership tester over Z_d using Smith normal form."""

    _cache: Dict[Tuple[int, Tuple[int, int], bytes], Tuple[np.ndarray, List[int], int]] = {}

    def __init__(self, B_rows: np.ndarray, d: int):
        self.d = int(d)
        B = np.array(B_rows, dtype=np.int64)
        if B.ndim == 1:
            B = B.reshape(1, -1)
        B = _normalize_rows(B, d)
        self.B = B
        self.m, self.n = B.shape if B.size else (0, B.shape[1] if B.ndim == 2 else 0)

        if self.B.shape[0] == 0:
            self.U = None
            self.diag = []
            self.rows_D = self.n
            return

        key = (self.d, self.B.shape, self.B.tobytes())
        cached = self._cache.get(key)
        if cached is None:
            D, U, V = smith_normal_decomp(sp.Matrix((self.B.T % self.d).tolist()), domain=sp.ZZ)
            U_np = np.array(U.tolist(), dtype=object)
            diag = [int(D[i, i]) for i in range(min(D.rows, D.cols))]
            rows_D = D.rows
            cached = (U_np, diag, rows_D)
            self._cache[key] = cached

        self.U, self.diag, self.rows_D = cached

    def contains(self, v: np.ndarray) -> bool:
        vec = np.array(v, dtype=object).reshape(-1)
        if self.B.shape[0] == 0:
            return not np.any(np.array(vec, dtype=int) % self.d)
        u = self.U.dot(vec)
        for i, s in enumerate(self.diag):
            if s == 0:
                if int(u[i]) % self.d != 0:
                    return False
            else:
                if int(u[i]) % math.gcd(abs(int(s)), self.d) != 0:
                    return False
        for i in range(len(self.diag), self.rows_D):
            if int(u[i]) % self.d != 0:
                return False
        return True


__all__ = ["ZdSpanTester"]
