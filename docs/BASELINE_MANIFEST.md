# Baseline and validation manifest

Baseline commit: `7279a28 refactor: align charge invariants with Ruba-Yang`
Recorded: 2026-07-22

This manifest distinguishes paper-level or theorem-scoped checks from legacy
output regression. Passing a regression test does not promote its physical
interpretation.

## Infrastructure baseline

Command:

```text
python -m mobility_toolkit doctor
```

Observed result:

- Windows strategy: WSL distro `Ubuntu`;
- Macaulay2 available, version 1.22;
- `2+2` smoke test passed;
- observed wall time: 6.6 seconds.

## Bulk literature/theorem baseline

Command:

```text
python -m pytest -q tests/test_ruba_yang_core.py
```

Observed result: `12 passed in 7.52s`.

This suite covers the corrected `bar(P/L)` presentation, Ext degree, toric-code
charge module, X-cube Eq. (98), Laurent antipode behavior, ambient spatial
dimension, and theorem-scope metadata. Authoritative interpretation remains in
`docs/THEORY_SCOPE.md` and `docs/VALIDATION.md`.

Classification: **literature/theorem correctness within the uniform-prime
free-Pauli-module backend scope**.

## Legacy finite-boundary baseline

Command:

```text
python -m pytest -q \
  tests/test_boundary_gauge_baselines.py \
  tests/test_boundary_gauge_examples.py
```

Observed result: `24 passed in 86.99s`.

These tests freeze current counts, shapes, supports, and representative weights
for the legacy Algorithm 1 implementation. The test modules explicitly state
that they are not paper-level correctness checks.

Classification: **compatibility regression only**.

They do not prove:

- boundary quotient invariant factors;
- induced pairing or radical;
- phase consistency;
- primary/secondary completeness;
- Lagrangian/maximality;
- known boundary GSD or anyon termination;
- half-space completeness;
- 2D or 3D boundary classification.

## Full suite baseline

Command:

```text
python -m pytest -q
```

Observed result: `247 passed, 1 skipped in 265.44s`.

An initial 124-second command limit expired before a summary; the repeated run
with a ten-minute limit completed successfully. The finite boundary subset
alone requires about 87 seconds and is a known Phase 2 performance baseline.

## Required new correctness groups

### Algebraic exhaustive oracle

- `d = 2,3,4,6,8,12`;
- mixed dimensions `[2,3]`, `[2,4]`, `[3,6]`;
- direct finite-group enumeration for kernel, quotient, centralizer, phase
  consistency, and logical invariant factors;
- invalid-certificate mutation tests.

### Finite-code physics

- repetition-code sanity cases;
- Z2 and Z4 toric/surface codes on torus, cylinder, disk, and annulus;
- known GSD/logical group under holes and mixed boundaries;
- CSS relative homology cross-checks.

### Boundary physics

- toric rough/smooth condensation and termination;
- fish toric secondary boundary operators;
- Z4 fusion/invariant factors;
- folded interfaces;
- 3D toric electric/magnetic boundary candidates;
- X-cube orientation dependence.

### Cheshire physics

- 3+1D toric closed charge-condensing loop;
- open segment with explicit endpoint strata;
- defect-local logical/degeneracy and charge termination;
- static results kept separate from circuit-depth statements.

## Test markers to introduce

```text
correctness      exact algebra/physics invariant
literature       directly sourced paper result
regression       current output compatibility only
backend_m2       requires Macaulay2
backend_native   requires optional native arithmetic backend
experimental     research capability, never a production gate by itself
slow             resource-heavy but deterministic
```
