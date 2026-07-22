# Backend capability matrix

This file records intended ownership and the current production boundary of
each mathematical backend. `production` means covered by correctness tests for
the stated domain; it does not mean every operation is fast.

## Current baseline at commit `7279a28`

| Backend | Domain | Current reliable operations | Current status |
|---|---|---|---|
| Internal Laurent parser | Uniform `Z/p`, prime | Parse/antipode/commutation validation | Production for current homology input contract |
| Macaulay2 | Uniform prime Laurent free Pauli module | Ext, annihilator, Krull dimension | Production within `docs/THEORY_SCOPE.md` |
| NumPy field backend | Finite uniform prime | Row span and finite boundary helper operations | Legacy regression only |
| Custom `Z/d` backend | Finite uniform composite | Span membership/generator reduction | Experimental; depends on uncertified custom SNF |
| Custom Smith backend | Integer matrices | Attempted SNF transforms | Not trusted: fixed iteration breaks and no verifier |
| SymPy | Small integer/finite calculations | Utility/reference operations | Development fallback, not a general certified kernel |

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

## Implemented production capabilities after Phase 3

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
| Boundary synthesis/enumeration | not yet implemented | Unsupported until Phase 5A |
| Half-space symbolic boundary | not yet implemented | Unsupported until Phase 6 |

The FLINT adapter refuses a single dense materialization above 2,000,000
entries by default. See `docs/FINITE_BACKEND.md`.

The Phase 4 Cheshire workflow is finite and static. It does not provide
automatic condensation discovery, Cheshire-species enumeration, circuit
depth, dynamic deformation/fusion, or thermodynamic phase equivalence.

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
