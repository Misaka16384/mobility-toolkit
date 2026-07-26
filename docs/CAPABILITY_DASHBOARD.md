# Capability and benchmark dashboard

This dashboard is an operation-scoped research release view. `production`
does not mean that a whole model family or dimension is classified. It means
that the exact operation and limits in the row have correctness, literature,
cross-backend/formulation, and bounded-scale evidence in
`tests/research_gates/phase10_capabilities.json`.

The JSON source is authoritative for automation. Validate it with:

```text
python tools/phase10_verify_dashboard.py
```

List or execute the four bounded CI slices with:

```text
python tools/phase10_verify_dashboard.py --list
python tools/phase10_verify_dashboard.py --run-layer correctness
python tools/phase10_verify_dashboard.py --run-layer literature
python tools/phase10_verify_dashboard.py --run-layer cross_backend
python tools/phase10_verify_dashboard.py --run-layer scale
```

None of these bounded smoke commands requires Macaulay2. The full Laurent and
live-saturation suites remain separate external-backend gates.

## Four evidence layers

| Layer | Required meaning |
|---|---|
| correctness | Mathematical identities, adversarial certificate rejection, or exhaustive small-system comparison |
| literature | A named, source-locked model/operator convention or physical invariant |
| cross-backend | An independent backend, brute-force oracle, rank implementation, or finite-versus-symbolic formulation |
| scale | Explicit resource refusal, checkpoint/resume, semantic replay, or finite search-domain accounting |

Scale evidence never licenses thermodynamic extrapolation. A finite search can
be `bounded_exact` while the broader research operation remains experimental.

## Production operation slices

| Capability ID | Exact operation scope | Exactness | Important exclusions |
|---|---|---|---|
| `finite_mixed_stabilizer` | Explicit finite cyclic local systems inside the dense budget | `certified_exact` | no general exact distance search |
| `finite_boundary_e1` | Supplied finite support window and exhausted paired-FGA search | `certified_exact` | no half-space inference; equivalence must be selected |
| `bounded_periodic_e2` | Declared finite FGA, translation action, period, and support orbit | `bounded_exact` | no ancillas or Hamiltonian completion |
| `supplied_2d_local_completion` | Supplied metric group, lifts, finite Hamiltonian, and locality domain | `certified_exact` / `bounded_exact` | no automatic anyon extraction or gap theorem |
| `halfspace_primary_and_supplied_pairing` | Rational normal, primary compiler, supplied uniform-prime free pairing | `certified_exact` | no generic full boundary module or secondary closure |
| `static_toric_cheshire` | User-specified finite 3+1D Z2 toric segments/loops and two static representations | `certified_exact` / `bounded_exact` | no dynamic circuit or phase-equivalence claim |

## Experimental research slices

| Capability ID | What is actually enumerated or checked | Missing promotion work |
|---|---|---|
| `symbolic_3d_e3_seeds` | RREF seed presentations in a finite Laurent exponent/rank box | saturation, anomaly, completion, stable equivalences |
| `bounded_cheshire_synthesis` | Explicit toric candidate families over a finite tube-radius schedule | species completeness and dynamic equivalence |
| `static_cheshire_fusion` | Finite before/after logical data and junction provenance | fusion circuit and complete superselection data |
| `fracton_cheshire_reference` | One explicit finite axial X-cube reference | other orientations and general fracton classification |

## Structured unsupported capabilities

| Capability ID | Reason |
|---|---|
| `generic_full_halfspace_boundary_module` | No general certified full module/secondary closure constructor |
| `arbitrary_code_anyon_extraction` | No general saturation and period-certificate pipeline |
| `cheshire_dynamic_phase_and_circuits` | Static stabilizer quotients do not determine phase equivalence or minimum circuit depth |

## Promotion rule

A `production` row is rejected by the verifier unless it:

1. cites at least one executable evidence record in every layer;
2. names an explicit operation scope and at least one limitation;
3. advertises only `certified_exact` or `bounded_exact`;
4. avoids broad 3D, thermodynamic, phase-equivalence, and circuit-depth claims;
5. points to real pytest node IDs.

The dashboard deliberately distinguishes implementation status from research
generality. For example, E2 is production within its finite declared search
domain, while arbitrary 3D boundary classification remains unsupported.
