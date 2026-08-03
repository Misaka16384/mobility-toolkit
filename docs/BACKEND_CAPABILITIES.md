# Backend capability matrix

This file records intended ownership and the current production boundary of
each mathematical backend. `production` means covered by correctness tests for
the stated domain; it does not mean every operation is fast.

## Current backend status

| Backend | Domain | Current reliable operations | Current status |
|---|---|---|---|
| Canonical Laurent AST | Uniform prime production; composite/nonuniform presentation research | Structured rings, modules, antipode and commutation | Production for validated uniform-prime operations |
| Macaulay2 | Uniform-prime Laurent and free tangent-Laurent modules | Ext, annihilator, Krull dimension, saturation, kernels/cokernels | Production operation-by-operation within `docs/THEORY_SCOPE.md` |
| python-flint FGA backend | Prime, composite and mixed finite local systems | HNF/SNF/Howell, kernel/image/intersection/quotient, centralizer and logicals | Production within the declared dense budget |
| Internal finite-field paths | Uniform prime finite modules | RREF, GF(2) bit-packed rank, exhaustive E1/E2 helpers | Production with FGA canonicalization/cross-checks |
| SymPy | Small integer and rational calculations | Independent checks and exact utility operations | Development/check backend, not the production FGA kernel |

## Target ownership

| Capability | Primary backend | Optional/check backend | Required certificate |
|---|---|---|---|
| F2 finite elimination | Internal bit-packed | brute force on small cases | kernel/rank identities |
| Prime finite elimination | Internal modular sparse/dense | Sage/independent implementation | kernel/image presentation |
| Integer HNF/SNF | FLINT candidate or verified internal adapter | Sage/SymPy small matrices | normal-form identities; transforms when requested |
| `Z/n` Howell form | FLINT candidate | independent integer presentation | canonical row-module certificate |
| Mixed-dimension FGA operations | Integer presentation + CRT | brute force/Sage | relation, kernel, quotient witnesses |
| Finite Pauli centralizer/logicals | FGA core | direct Pauli enumeration | stabilizer/logical/GSD identities |
| Laurent Gröbner/syzygy/Ext | Macaulay2 | paper examples/independent identities | ring/presentation/resolution provenance |
| Composite Laurent Ext | Macaulay2 feature probe or future backend | literature benchmarks | Experimental until operation-specific validation |
| Half-space modules | Semigroup/Toeplitz + Laurent backend | finite exhaustion | support/module/saturation certificates |
| Finite boundary enumeration E1 | FGA core | brute-force subgroup enumeration | exhaustive finite-domain certificate |
| Bounded periodic enumeration E2 | FGA + translation action | independent rerun | finite search-domain certificate |
| Symbolic 3D enumeration E3 | Laurent/half-space research backend | E1/E2 exhaustion | Experimental unless module completeness is proved |

## Implemented operation-specific capabilities

| Capability | Backend/representation | Status |
|---|---|---|
| Integer kernel and column lattice | python-flint HNF transform + independent verifier | Production within dense budget |
| SNF invariant factors | python-flint + SymPy cross-check | Production within dense budget |
| Howell form over `Z/n` | certified integer preimage HNF | Production |
| CRT primary decomposition | exact idempotent projectors + subgroup/order checks | Production |
| Prime-field kernel | modular RREF; bit-packed GF(2) fast path | Production |
| Mixed finite Pauli stabilizers | phase-aware FGA centralizer/logical quotient | Production |
| Finite cell complexes | signed integer incidence with `boundary^2=0` validation | Production |
| Oriented finite quotients | signed cell gluings with boundary-compatibility check | Production |
| Periodic-to-finite compilation | explicit crossing/alias policies and full provenance | Production for explicit finite inputs |
| Site/frame twists | phase-aware local Pauli automorphisms with inverse/path checks | Production |
| Finite defect-local algebra | integer preimage intersections and paired quotient `(C∩W)/(S∩W)` | Production within dense budget |
| Static Z2 Cheshire lines | phase-aware finite stabilizers, pinned elimination, deleted-tube compiler | Production for user-specified 3D cubical paths |
| Finite charge termination | explicit syndrome witness | Production |
| Finite magnetic nontermination | complete mod-2 cellular syndrome-image rank plus `boundary^2=0` | Production for the plaquette-qubit reference |
| Finite boundary algebra | exact `(C intersect P_W)/(S intersect P_W)` paired FGA | Production within the finite dense budget |
| E1 finite subgroup enumeration | exhaustive finite-group BFS, phase lifts, orbit reduction, semantic resume transcript | `certified_exact` after exhaustion |
| Half-space lattice geometry | primitive normal, unimodular adapted basis, tangent lattice and one-sided support | Production |
| Uniform-prime `L_H` contraction | normal clearing plus live Macaulay2 saturation | `certified_exact` |
| Uniform-prime primary subquotient | complete crossing-shift compilation of `pi_H(L)/L_H` | `certified_exact` |
| Supplied free boundary pairing | radical kernel, pairing cokernel, annihilator and Krull dimension | `certified_exact` for uniform prime |
| Generic full `P_boundary` / secondary closure | no general certified constructor | Unsupported; model-specific examples only |
| E2 bounded-periodic submodules | finite FGA support-image translation orbit plus period invariance | `bounded_exact` after exhaustion; no ancillas/completions |
| 2D finite metric-group condensation | exact spin/braiding and Lagrangian subgroup enumeration | `certified_exact` |
| 2D supplied local completion | phase-aware finite Hamiltonian, fusion lifting, locality and endpoint syndrome | `bounded_exact` for the supplied finite patch |
| Arbitrary-code 2D anyon extraction | no saturation/period certificate pipeline | Unsupported |
| E3 bounded symbolic seeds | finite-field RREF seed presentations in a Laurent exponent box | `bounded_exact` for that box; research layer |
| E3 saturation/anomaly/local completion | not implemented | Unsupported |
| 3D toric half-space | source-frozen bulk and certified primary pairing; finite slab alignment | Primary-only, operation-specific |
| X-cube orientations | source-locked axial/diagonal conclusions | Experimental oracle; no full boundary module |
| 2D Z2 toric Cheshire classification | isotropic-pruned folded Lagrangian exhaustion plus source direct-algebra/action/fusion crosswalk | `certified_exact`; six oriented species and 36 ordered products |
| General finite pointed/Abelian interfaces | folded metric groups; optimized diagonal Lagrangian closure graph with general raw-subgroup fallback | exact after exhaustion; generic direct algebra/fusion needs cochain data |
| Pointed algebra cochains | finite fusion table, normalized associator, pentagon, `d(mu)=omega`, explicit coboundary gauge | exact for supplied finite data |
| Toric 2D lattice/circuit realization | finite cellular Pauli Hamiltonian plus exact Clifford/Pauli-rotation conjugation replay | `bounded_exact`; no gap or optimal-depth claim |
| Cheshire junction/network schema | endpoint binding and incidence coverage | Schema-validated incidence only; junction-local Hamiltonian completion unsupported |
| X-cube axial support catalog | exact GF(2) enumeration of 58 totally singular supports per axis and support-level quotients | all records remain graded candidates; classification incomplete |
| X-cube axial finite line candidate | Eq. (140) periodic-x/y open-z compilation; add local `X(edge_x)` q2 lineon-condensate terms, delete anticommuting `cross_zx`, and certify the rank-one hidden-charge sector with GF(2) syndrome/local-algebra/rank/translation scans | optional static upgrade for `ell_z`; exact finite commuting completion, but no thermodynamic classification or circuit claim |

The FLINT adapter refuses a single dense materialization above 2,000,000
entries by default. See `docs/FINITE_BACKEND.md`.

Cheshire API v2 removes the old supplied-list classification semantics. The
2D Z2 toric reference is complete at the categorical level, and the general
finite pointed/Abelian executor is complete only when its folded search is
exhausted. Finite lattice/circuit outputs certify the emitted patch and Pauli
mapping, not a thermodynamic gap or minimum depth. The retained 3+1D static
reference is explicitly named as such. Junction support remains incidence
validation unless a junction-local Hamiltonian is supplied.

The X-cube support executor rotates the five-generator slice across all three
coordinate axes. Its 58-per-axis and 41-cubic-orbit results are exact support
counts, not species. The optional Eq. (140) finite deletion/probe reference
upgrades only `ell_z` to a static candidate. No ordinary 2D anyon Lagrangian
criterion, mobility-enriched multiplication/Morita theorem, slanted
orientation, physical foliated quotient, or thermodynamic conclusion is
supplied.

The Phase 7 local-completion path starts from a supplied finite metric group
and supplied short-string lifts. Its exact finite verification must not be
reported as automatic anyon extraction or a thermodynamic gap theorem.

The Phase 8 symbolic path exhausts seed presentations, not all Laurent
submodules up to arbitrary polynomial generator changes. Its resumable
certificate replays the canonical RREF prefix and remains distinct from E2
finite-periodic completeness.

## Selection rules

1. The caller requests an operation and exactness level, not a preferred matrix
   trick.
2. `supports()` checks coefficient domain, local invariant factors, translation
   group, representation size, witness requirements, and resource budget.
3. The selector may use a faster exact backend but may not lower exactness.
4. Unsupported composite Laurent operations return structured `unsupported`;
   `prime_bypass` is not a capability.
5. Full transforms are computed only when representatives or downstream maps
   require them.
6. Every native/CAS backend has a pure verifier path for standard certificates.

## Promotion gate

A backend operation moves from experimental to production only after:

1. small random property tests against exhaustive enumeration;
2. cross-backend agreement on adversarial composite and mixed-dimension cases;
3. injected invalid certificates are rejected;
4. at least one literature model tests a physical invariant derived through
   the operation;
5. timeout/truncated output is surfaced as failure or incomplete status.
