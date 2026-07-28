"""Deterministic Phase-2 finite-backend microbenchmarks (JSON to stdout)."""

from __future__ import annotations

import json
import random
import time

from mobility_toolkit.core import LocalPauliTerm, PauliModule, SparseIntMatrix
from mobility_toolkit.finite import (
    FlintIntegerBackend,
    analyze_finite_stabilizer,
    howell_form,
    prime_field_kernel,
)


def _timed(operation):
    started = time.perf_counter()
    value = operation()
    return value, time.perf_counter() - started


def _sparse_random_matrix(rows, columns, entries_per_row, modulus, seed):
    randomizer = random.Random(seed)
    entries = []
    for row in range(rows):
        selected = randomizer.sample(range(columns), entries_per_row)
        for column in selected:
            entries.append((row, column, randomizer.randrange(1, modulus)))
    return SparseIntMatrix(rows, columns, tuple(entries))


def main():
    backend = FlintIntegerBackend()
    report = {
        "backend": backend.name,
        "backend_version": backend.version,
        "max_dense_entries": backend.max_dense_entries,
        "schema": "mobility_toolkit.finite_benchmark.v1",
    }

    binary_matrix = _sparse_random_matrix(128, 256, 8, 2, 1729)
    binary, elapsed = _timed(lambda: prime_field_kernel(binary_matrix, 2))
    report["binary_kernel_128x256"] = {
        "algorithm": binary.rref_certificate.algorithm,
        "nullity": binary.basis.ncols,
        "seconds": elapsed,
    }

    howell_matrix = _sparse_random_matrix(12, 16, 4, 12, 2718)
    howell, elapsed = _timed(lambda: howell_form(howell_matrix, 12, backend))
    report["howell_z12_12x16"] = {
        "output_rows": howell.form.nrows,
        "seconds": elapsed,
    }

    module = PauliModule.from_dimensions((4,) * 16)
    generators = tuple(
        module.operator((LocalPauliTerm.cyclic(f"q{index}", z=2),))
        for index in range(8)
    )
    stabilizer, elapsed = _timed(
        lambda: analyze_finite_stabilizer(module, generators, backend)
    )
    report["ququart_stabilizer_16_sites_8_terms"] = {
        "codespace_dimension": stabilizer.codespace_dimension,
        "logical_order": stabilizer.logical_projective_order,
        "seconds": elapsed,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
