# Exact finite backend contract

Status: Phase 2 production contract (2026-07-22)

## Representation and algorithms

- Public finite objects remain canonical sparse integer presentations.
- Vectors are columns; relation matrices present `Z^n / image(R)`.
- Subgroups are full-rank preimage lattices between `R Z^n` and `Z^n`.
- FLINT supplies HNF transformations, SNF invariants, determinants and exact
  lattice solves. Every returned HNF/kernel certificate is independently
  verified; SNF invariants are cross-checked with SymPy.
- Howell form over `Z/m` is the reduction of the row-HNF of
  `rowspan_Z(A) + m Z^n`; its retained integer preimage is the completeness
  certificate.
- Prime-field kernels use modular RREF. GF(2) selects a bit-packed path, but
  returns the same `SparseIntMatrix` and canonical `FiniteSubgroup` contracts.
- Composite groups may be decomposed by certified CRT idempotents. Direct
  integer-presentation results remain the reference result.

## Dense materialization policy

The canonical IR is sparse, but python-flint's current matrix normal forms are
dense. `FlintIntegerBackend` therefore refuses any individual dense
materialization above `max_dense_entries` (default `2,000,000`). This is an
explicit structured failure, never a heuristic fallback. Callers must split a
problem, choose a future sparse backend, or deliberately construct a backend
with a different budget.

The independent SymPy certificate verifier is intentionally enabled on every
Phase 2 result. It is a correctness cost, not a performance oracle. Future
large-scale services may cache verified certificates, but may not silently
skip requested verification.

## Reproducible baseline

Run from the repository root:

```powershell
python tools/benchmark_finite.py
```

The JSON records backend/version, materialization budget, dimensions,
algorithms, exact output sizes and wall times. It is a regression baseline,
not a universal performance claim; hardware and Python/FLINT versions must be
kept with any comparison.

## Deliberate exclusions

- No exact minimum-distance search.
- No custom SNF loop with iteration cutoffs.
- No field-rank substitution for a composite coefficient ring.
- No conversion of arbitrary large sparse inputs to dense form without the
  explicit budget check.
