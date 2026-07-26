# Research release checklist

This checklist is required for a boundary/defect research release. A green
ordinary unit-test run is necessary but does not by itself promote an
experimental operation.

## 1. Freeze the release input

- [ ] The worktree is clean and the intended checkpoint commit is recorded.
- [ ] `mobility_toolkit.__version__` is the only version source.
- [ ] Canonical schema changes have an ADR or explicit schema-version bump.
- [ ] Capability claims are operation-scoped; coefficient domain, geometry,
      search domain, and resource bounds are visible.
- [ ] No runtime compatibility layer was reintroduced for deleted tuple,
      polynomial-string, blocked/interleaved, or `prime_bypass` semantics.

## 2. Verify the machine-readable dashboard

- [ ] Install development dependencies, including `python-flint`.
- [ ] Run `python tools/phase10_verify_dashboard.py`.
- [ ] Review `docs/CAPABILITY_DASHBOARD.md` against
      `docs/BACKEND_CAPABILITIES.md` and
      `docs/PHYSICS_BENCHMARKS.md`.
- [ ] Every new production claim has correctness, literature,
      cross-backend/formulation, and scale evidence.
- [ ] Every experimental or unsupported field remains machine-readable in
      Python, CLI, MCP, and skill results.

## 3. Run the four bounded release layers

- [ ] `python tools/phase10_verify_dashboard.py --run-layer correctness`
- [ ] `python tools/phase10_verify_dashboard.py --run-layer literature`
- [ ] `python tools/phase10_verify_dashboard.py --run-layer cross_backend`
- [ ] `python tools/phase10_verify_dashboard.py --run-layer scale`

These smoke gates intentionally do not require Macaulay2. Skips caused by a
missing declared development dependency are release failures, not passes.

## 4. External and full-suite gates

- [ ] Run the full pytest suite with the supported Python versions.
- [ ] Run `mobility-toolkit doctor`; record Macaulay2 version and invocation.
- [ ] Run live uniform-prime Laurent/Ext and half-space saturation tests.
- [ ] Confirm an unavailable backend returns structured `unsupported` or an
      explicit skip in non-release CI, never a fabricated exact result.
- [ ] Confirm cache keys bind canonical input, operation, backend fingerprint,
      assumptions, and requested certificate level.

## 5. Enumeration and resource safety

- [ ] E1 exhausted results say `certified_exact`; partial pages do not.
- [ ] E2 results say `bounded_exact` only for the serialized support/period
      domain and supported candidate family.
- [ ] E3 results identify the exponent box, seed rank, coefficient field, and
      equivalence subset.
- [ ] Checkpoint replay rejects cursor, prefix, transcript, and semantic
      decision tampering.
- [ ] Resume produces the same candidate order and terminal certificate as a
      one-shot run.
- [ ] Dense materialization, work units, result count, and wall-time limits
      fail or truncate explicitly.

## 6. Physics claim audit

- [ ] Literature fixtures name a primary source and freeze the convention used.
- [ ] Compatibility/golden outputs are not used as correctness or literature
      evidence.
- [ ] Finite exact, bounded exact, empirical stabilization, experimental, and
      unsupported are not conflated.
- [ ] A supplied boundary pairing is not reported as a generic constructed full
      boundary module.
- [ ] A finite local completion is not reported as a thermodynamic gap proof.
- [ ] A bounded 3D enumeration is not reported as a general fracton boundary
      classification.
- [ ] Cheshire static degeneracy/fusion data is separated from circuit depth,
      finite-depth phase equivalence, and dynamic creation claims.
- [ ] Unregistered X-cube/fracton orientations return structured unsupported
      results.

## 7. Transport and packaging

- [ ] The same canonical request reaches one versioned service operation from
      Python, CLI, MCP, and each relevant skill.
- [ ] All transports serialize the same result schema and capability fields.
- [ ] Skills contain no copied algorithm dispatcher or divergent validation.
- [ ] The skill structure validator passes for every bundled skill.
- [ ] Wheel package data contains each skill's Markdown, Python, JSON, and YAML
      assets.
- [ ] Installation tests confirm the exact supported skill inventory.

## 8. Final release record

- [ ] Archive the dashboard verifier output and four layer summaries.
- [ ] Record full-suite totals, skips, external backend versions, and duration.
- [ ] Record known experimental/unsupported capabilities in release notes.
- [ ] Bump through `python tools/release.py`; do not edit `pyproject.toml`
      version metadata manually.
- [ ] Inspect the release commit and tag before any push.
