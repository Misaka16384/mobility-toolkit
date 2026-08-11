# Changelog

Notable changes to `mobility_toolkit`. The version is the single source of
truth in `mobility_toolkit/__init__.py`; releases are cut with
`python tools/release.py`.

This project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
loosely and [Semantic Versioning](https://semver.org/).

## [0.4.0] — 2026-08-10

A correctness audit of the scientific and implementation layers, the fixes it
produced, and the resolution of the whole open pull-request queue.

The audit found **no error in the computed mathematics**. The charge module,
the finite Pauli algebra, the ground-state degeneracy path and the Cheshire
support enumeration all reproduce the literature. Everything below is metadata,
provenance, tooling, or performance.

### Removed

- **Dropped Python 3.9.** `requires-python` is now `>=3.10`. The package has
  called `int.bit_count()` — a 3.10 builtin — since the fracton and Cheshire
  work landed (`defects/cheshire_fracton_v2.py`, `defects/fracton_cheshire.py`),
  so the declared 3.9 floor was never real: pip would install the package on
  3.9 and it would then raise `AttributeError` at runtime rather than refusing
  to install. 3.10 is the honest floor. Added the matching version classifiers.

### Fixed

- **`is_topological` in the seeded model registry now states its provenance.**
  The column recorded a conclusion the toolkit is deliberately unable to
  derive: `physics.classify_mobility` returns `None` for topological order
  unless the caller supplies `lagrangian`, `saturated` and `no_ssb`, because a
  Krull dimension alone does not establish it. The seeded values are correct as
  *literature facts about the models*, so they are kept and a new
  `topological_claim_basis` column names the citation for each. Rows synced
  from a discovery file without that field are recorded as `unattributed`
  rather than silently promoted. Existing databases are migrated in place by
  `_ensure_models_columns`.

- **Backend absence now skips instead of failing, as documented.** The README
  requires that a missing Macaulay2 "produce structured unsupported behavior or
  an explicit non-release skip; it must never fabricate an exact result", and
  `docs/DEVELOPMENT.md` claimed M2-backed tests "skip automatically without a
  backend". Neither was true: on a machine with no Macaulay2 the suite reported
  **71 failed, 679 passed, 27 skipped** — only 27 tests carried a `skipif`
  guard, and the other 71 reached the backend through unguarded call paths and
  errored. Two complementary fixes:

  - `conftest.py` rewrites *backend-absent* failures into skips, matched on the
    engine's own sentinel. Scope is deliberately narrow — a Macaulay2 error with
    any other message still fails, a wrong invariant still fails, and a test
    that asserts the absent-backend error still passes. This covers 56 tests.
  - The remaining 15 are direct bridge/engine integration tests that assert on
    the exit code (`assert 127 == 0`), so their messages carry no sentinel.
    They now carry explicit `skipif` guards in `test_bridge.py`,
    `test_engine.py`, `test_cross_interactions.py` and `test_utils.py`.

  Without a backend the suite is now **679 passed, 98 skipped, 0 failed**; with
  one it is unchanged at **776 passed, 1 skipped**. The false claim is corrected
  in `docs/DEVELOPMENT.md` and `AGENTS.md`, which now state plainly that a green
  run without a backend leaves the Ext, GSD and fusion paths uncovered rather
  than verified.

  This was found by the new CI on its first run, not by the audit.

### Added

- **Continuous integration** (`.github/workflows/ci.yml`) — there was none.
  Runs the suite on Python 3.10 and 3.13, the operation-scoped research-release
  dashboard, and a best-effort `vermin` syntax-floor net. The 3.10 job is what
  actually enforces `requires-python`; its lower bound must stay pinned to it.
  `mobility-toolkit doctor` runs non-fatally so the log records that Macaulay2
  is absent on the runner and the Ext paths are therefore skipped, not covered.

### Changed

- **`AGENTS.md` rewritten against the current tree.** Corrected the stale
  do-not-commit list, replaced the partial CLI description with the full
  surface split by purpose, documented the `periodic.*` operation family
  (registered and supported, but named by no `mt-*` skill row), and added
  repository-architecture and contributor sections so one file covers both
  using and changing the toolkit. This repository has no `CLAUDE.md`; `AGENTS.md`
  is the single agent-facing document.

### Performance

- **Memoised the axial X-cube support enumeration.** `_all_subspaces` closes
  over every subspace of F₂⁵ by repeated spanning and depends on nothing, but
  was recomputed on every call — about 21 ms, dominating
  `_totally_singular_subspaces` and therefore `defects.cheshire.xcube_candidates`.
  Both are now `lru_cache`d; repeat calls cost ~0.1 µs. Both are pure nullary
  functions returning immutable tuples of frozensets, so sharing the result is
  safe, and the enumeration still returns its asserted 58 subgroups.

### Merged pull requests

Thirteen automated "Bolt" performance patches were open, in five clusters of
near-duplicate submissions. Four merged, nine closed.

| PR | Change | Verification |
|---|---|---|
| #26 | O(N) cubical-mask adjacency via offset lookup, replacing the O(N²) pairwise scan; drops an unused `import math` | Equivalent to the previous code over 5,875 randomized masks — adjacency sets and `pinched` tuples byte-identical |
| #20 | Bit-packed GF(2) matrix multiply; explicit loop in `toric3d._dot` | Arithmetic exact over 4,000 random matrices including negative and >1 entries |
| #24 | `reduce(mul, X, 1)` → `math.prod` in `core/pauli.py` and `finite/crt.py` | Equivalent including the empty-sequence case; `math.prod` is 3.8+ |
| #16 | Unrolled `any()` guard and cached bounds lookup in `count_quotient_size` | Semantically identical to the generator form |

Closed as superseded or misdirected: #15, #17, #18, #19, #21, #22, #23, #25,
#27. #22's `cheshire_fracton_v2` rewrites were correct but optimised the cheap
half of that path — the memoisation above addresses the same goal properly —
and it bundled unused-import removal across 35 files, which belongs in its own
review.

### Verification

Reproduced against a live Macaulay2 1.22 backend, not asserted from source:

| Check | Result |
|---|---|
| Charge module `dim Q⁰` vs literature | 2D toric 0, 3D toric 0, X-cube 1, Chamon 1, Haah cubic code 1 → 1 — all five correct |
| X-cube annihilator structure | every generator of the form `(a−1)(b−1)`, encoding the lineon axes |
| Ground-state degeneracy | toric = 4 on three tori; WCF = 144; DCY = 104,976 |
| Pauli group law | 4,000 randomized trials over ten prime, prime-power and mixed local-dimension sets; associativity, inverse, commutator phase = projective pairing, antisymmetry — zero failures |
| X-cube support count | 58 independently re-derived as 19 + 33 + 6 by dimension |
| Mobility refusal | X-cube and Haah correctly return `inconclusive`; only the binomial case resolves |
| Suite | 776 passed, 1 skipped |

The 3D toric code and Haah's cubic code are not in the repository's reference
set; both were constructed for the audit and both came out right. They are the
pair that justifies the conservative reading of Krull dimension: they give the
same `dim Q⁰ = 1` while one has lineons and the other has no mobile excitation
at all, so the dimension cannot be read as a count of free directions.

## [0.3.0] and earlier

Not retrospectively documented. See `git log` and the release tags.
