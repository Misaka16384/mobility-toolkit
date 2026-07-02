"""Zero-syndrome kernel helpers."""

from __future__ import annotations

import numpy as np


def modified_gaussian_elimination(M_input: np.ndarray, d: int) -> np.ndarray:
    """Compute raw relation rows with the notebook's integer MGE routine."""
    A = M_input.copy().astype(int)
    n_rows_orig, n_cols = A.shape
    R = np.eye(n_rows_orig, dtype=int)

    current_row = 0
    current_col = 0

    while current_col < n_cols:
        modulus_row_A = np.zeros((1, n_cols), dtype=int)
        modulus_row_A[0, current_col] = d
        modulus_row_R = np.zeros((1, n_rows_orig), dtype=int)

        A = np.vstack([A, modulus_row_A])
        R = np.vstack([R, modulus_row_R])

        while True:
            col_slice = A[current_row:, current_col]
            nonzero_indices = np.where(col_slice != 0)[0] + current_row

            if len(nonzero_indices) == 0:
                break

            if len(nonzero_indices) == 1:
                pivot_idx = nonzero_indices[0]
                if pivot_idx != current_row:
                    A[[current_row, pivot_idx]] = A[[pivot_idx, current_row]]
                    R[[current_row, pivot_idx]] = R[[pivot_idx, current_row]]
                break

            values = A[nonzero_indices, current_col]
            abs_values = np.abs(values)
            min_idx_local = np.argmin(abs_values)
            idx_small = nonzero_indices[min_idx_local]
            val_small = A[idx_small, current_col]

            for idx_target in nonzero_indices:
                if idx_target == idx_small:
                    continue

                quotient = A[idx_target, current_col] // val_small
                if quotient != 0:
                    A[idx_target] -= quotient * A[idx_small]
                    R[idx_target] -= quotient * R[idx_small]

        if A[current_row, current_col] != 0:
            current_row += 1

        current_col += 1

    zero_rows_indices = np.where(~A.any(axis=1))[0]
    return R[zero_rows_indices]


def extract_zero_syndrome_operators(R_clean: np.ndarray, V: np.ndarray, d: int) -> np.ndarray:
    return (R_clean @ V) % d


__all__ = [
    "extract_zero_syndrome_operators",
    "modified_gaussian_elimination",
]
