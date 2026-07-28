# Physics correctness benchmark manifest

Status: active

Evidence labels:

- `LIT_DIRECT`: operator placement or conclusion stated in a primary source;
- `DERIVED_HOMOLOGY`: derived independently from a signed cellular chain
  complex and finite-coefficient homology;
- `EXHAUSTIVE_SMALL`: checked against dense Hilbert-space or complete Pauli
  enumeration;
- `DERIVED_GF2_RANK`: independently recomputed from a bit-packed binary
  stabilizer matrix rather than the production FGA quotient;
- `CELLULAR_NO_SOLUTION`: complete finite syndrome-image rank plus the signed
  cellular `boundary^2=0` identity;
- `COMPATIBILITY_ONLY`: legacy output retained only to detect accidental API
  drift and never used as a mathematical oracle.

## Phase 2 generalized stabilizers

| Fixture | Expected result | Evidence |
|---|---|---|
| one ququart, raw `XZ` | scalar obstruction `(XZ)^4=-I`; reject | `EXHAUSTIVE_SMALL` |
| one ququart, phase-lifted `zeta*XZ` | `K=1` | `EXHAUSTIVE_SMALL` |
| d=4 `X^2` | `K=2`, logical factors `(2,2)` | `EXHAUSTIVE_SMALL` |
| d=6 `X^2` / `X^3` | `K=2` / `K=3` | `EXHAUSTIVE_SMALL` |
| d=12 `X^4` | `K=4` | `EXHAUSTIVE_SMALL` |
| mixed `[2,3]`, `[2,4]`, `[3,6]` | direct dense fixed-space dimensions | `EXHAUSTIVE_SMALL` |

These tests use NumPy Weyl matrices or complete projective-Pauli enumeration,
not the FGA implementation as its own oracle.

## Phase 3 cellular models

For an oriented finite complex

```text
C_(p+1) --d_(p+1)--> C_p --d_p--> C_(p-1),
```

the benchmark places a `Z_N` qudit on every p-cell, X checks from rows of
`d_p`, and Z checks from columns of `d_(p+1)`. The compiler validates signed
incidence, including negative exponents for `N=3,4`.

The expected ground-space dimension is `|H_p(X; Z_N)|`. It is computed by a
finite group homology quotient that is independent of the stabilizer
centralizer calculation.

| Geometry | p | Expected K | Tests/evidence |
|---|---:|---:|---|
| open rectangle/disk | 1 | 1 | `DERIVED_HOMOLOGY`, small Pauli cross-check |
| 3x3 center-hole annulus | 1 | N | `DERIVED_HOMOLOGY`, small Pauli cross-check |
| planar mask with two holes | 1 | N^2 | `DERIVED_HOMOLOGY` |
| cylinder | 1 | N | `DERIVED_HOMOLOGY` |
| 2-torus | 1 | N^2 | `DERIVED_HOMOLOGY`, periodic-template Pauli cross-check |
| 3-ball | 1 or 2 | 1 | `DERIVED_HOMOLOGY`, Pauli cross-check |
| solid torus | 1 / 2 | N / 1 | `DERIVED_HOMOLOGY` |
| 3-torus | 1 or 2 | N^3 | `DERIVED_HOMOLOGY`, small Pauli cross-check |
| shell homotopy-equivalent to S^2 | 1 / 2 | 1 / N | `DERIVED_HOMOLOGY`, minimal-CW Pauli cross-check |

The 2D qudits-on-edges, vertex/face stabilizers, alternating boundary types,
and relative-homology logical interpretation originate in Bravyi and Kitaev,
[Quantum codes on a lattice with boundary](https://arxiv.org/abs/quant-ph/9811052).

The p=2 plaquette-qudit convention is retained because the Cheshire reference
model uses plaquette qubits, cube charge terms, and edge flux terms; see
Tantivasadakarn and Chen,
[String operators for Cheshire strings in topological phases](https://arxiv.org/abs/2307.03180).

## Geometry and gluing

| Fixture | Exact check | Evidence |
|---|---|---|
| open box | cell counts, Euler characteristic, `boundary^2=0` | `DERIVED_HOMOLOGY` |
| annulus/two holes | published cell counts in test, H1 and boundary components | `DERIVED_HOMOLOGY` |
| disconnected mask | H0 and additive Euler characteristic | `DERIVED_HOMOLOGY` |
| diagonal-touch mask | closure H0 plus explicit pinched-junction diagnostic | exact combinatorial |
| sheared torus | H1 = `Z_N^2` | `DERIVED_HOMOLOGY` |
| Möbius vs cylinder | same H1, one vs two boundary components | `DERIVED_HOMOLOGY` |
| Klein bottle | `H1(Z_N)=Z_N + Z_gcd(N,2)` | `DERIVED_HOMOLOGY` |
| Fourier-twisted d=4 seam | central phase and inverse frame | `EXHAUSTIVE_SMALL` |

Non-orientable surface fixtures are topology/compiler checks. Their relation
to parity-twisted topological phases is contextualized by Chan, Teo, and Ryu,
[Topological Phases on Non-orientable Surfaces](https://arxiv.org/abs/1509.03920);
the numerical homology expectations in this repository are independently
derived from the stored signed CW boundary maps.

## Phase 4 static Cheshire benchmarks

The first reference family is the 3+1D Z2 plaquette-qubit toric code:

- open Cheshire segment in a finite ball;
- closed Cheshire loop;
- two disjoint components on T3;
- charge termination succeeds while magnetic termination fails;
- local stabilizers alone retain the defect logical qubit; adding the
  nonlocal charge-sector operator removes it.

The implemented reference uses `FOURIER_DUAL`: cube checks are X-type and edge
checks are Z-type, exactly as in the cited model.

| Fixture | Bulk K | Local-only K | Fixed-sector K | Evidence |
|---|---:|---:|---:|---|
| two-cube open segment in a ball | 1 | 2 | 1 | `LIT_DIRECT` operator rewrite; `DERIVED_GF2_RANK` finite GSD |
| four-cube contractible closed loop in a ball | 1 | 2 | 1 | static closed extension; `DERIVED_GF2_RANK` |
| two disjoint open segments on T3 | 8 | 16 | 8 | `DERIVED_GF2_RANK`; certified FGA agrees |
| one noncontractible loop on T3 | 8 | 4 | not used as a sector-restoration gate | `DERIVED_GF2_RANK` adversarial guard |

For two open T3 segments only one relative total-charge constraint is
independent: adding the first `Q_gamma` changes 16 to 8 and the second is
redundant. The noncontractible-loop row prevents any implementation from
hard-coding a component-count-only degeneracy formula.

Additional certified checks:

- Eq. (8) product and commutation identities, including phase lift;
- open segment has two endpoint strata; closed loop has none;
- charge termination has a positive syndrome witness;
- magnetic nontermination uses `CELLULAR_NO_SOLUTION`, not a failed probe;
- direct line rewrite and deleted-tube cellular representation have identical
  phase-aware generator sets after exact elimination of pinned condensate
  plaquettes;
- defect-local quotient retains the induced pairing radical;
- length and support-window radius samples are exact finite points only.

Static degeneracy, termination, and representation fields remain separate
from circuit depth, finite-depth phase equivalence, dynamic deformation, and
fusion claims.

## Phase 5 finite boundary algebra and E1/E2 enumeration

| Fixture | Expected result | Evidence |
|---|---|---|
| literal left-square cut of a 2-by-1 Z2/Z4 toric patch | every crossing check is covered modulo bulk-trivial operators | exact finite FGA plus cut-provenance witness |
| electric Z string at rough cut | two parent endpoints become one retained bulk endpoint | finite commutation syndrome / relative-homology interpretation |
| magnetic X string at smooth cut | two parent endpoints become one retained bulk endpoint | finite commutation syndrome / relative-homology interpretation |
| canonical Z2 fish-toric `5x2` periodic parent, three-column finite cut | paper templates equal the recorded two-monomial CNOT shear of the canonical toric differential; boundary algebra `(Z2)^16`, zero radical, primary order `2^14` inside full order `2^16`; a `Z_h` segment has two parent endpoints and one retained endpoint | `LIT_DIRECT` Eqs. (12)--(13), Fig. 4 and Sec. 5.2 of [Liang--Yang--Iosue--Chen](https://arxiv.org/abs/2410.11942), plus canonical compiler and exact finite FGA |
| small paired FGA E1 | every isotropic subgroup once | exhaustive subgroup BFS and brute-force cross-check |
| E2 period-two qutrit Fourier action | `T^2 H = H`, `T H != H`, fundamental period 2 | exact finite automorphism and subgroup membership |
| E2 support bound | single-site translation orbit accepted; intrinsically two-site seed rejected at `max_sites=1` | exact translated support-image intersections |

E1 transcript checkpoints bind the finite paired algebra and complete output
prefix. E2 additionally binds adapted site coordinates, the microscopic
translation actions, anchor and translated support-image hashes, period,
coefficient domain, candidate family, and resource accounting. These are
finite-domain completeness statements only.

The fish fixture is independent of the former legacy `GeneratorTerm` rows: it
starts from source-locked `OperatorTemplate` objects and checks the paper's
stated finite-depth-Clifford equivalence explicitly.  In Laurent notation its
X shear is
`U = [[1,0],[y^-2(1+x),1]]`; the inverse-antipode Z action is replayed as
well.  The order-four full/primary quotient is a finite witness for two
independent secondary classes, but the benchmark does not identify its
chosen quotient basis with the paper's diagram labels 5 and 6.  The endpoint
count is for the explicit raw cut.  It does not certify topological-order
completion, a gapped fish boundary, or a thermodynamic boundary
classification.

## Phase 6 half-space benchmarks

| Fixture | Expected result | Evidence |
|---|---|---|
| 2D Z2 toric, `y >= 0` | primary equals full; pairing `1+x`; boundary charges `Z2 + Z2`; boundary-to-bulk isomorphism | analytic module identities plus periodic strips |
| Ruba--Yang Example 45 | proper secondary generator with `(1+x)e1' = e1`; primary charge nonzero, full pairing unimodular | `LIT_DIRECT` equations (114)--(118) plus finite periods |
| 3D Z2 toric, `z >= 0` | primary generators `e_X,e_Zx,e_Zy`; pairings `1+x` and `1+y` | source-frozen cellular rows, live saturation and finite slabs |
| X-cube axial `(0,0,1)` | boundary-to-bulk map not surjective, obstruction family `[<x^m y^n z>]` | source-locked Example 54 oracle |
| X-cube diagonal `(1,1,1)` | source equation (144) records an isomorphism | source-locked Example 54 oracle |

The X-cube rows, adapted lattice basis, and registered orientation are
machine-checked, but the analytic boundary-to-bulk conclusion is not
independently re-derived. Those results therefore remain `experimental`.
Unregistered and opposite normals return `unsupported`.

## Phase 7 2D metric condensation and local completion

| Fixture | Raw Lagrangians / finite result | Evidence |
|---|---:|---|
| Z2 toric metric | 2 | exhaustive finite subgroup enumeration |
| Z4 toric metric | 3 | exhaustive finite subgroup enumeration |
| double semion metric | 1 | exhaustive spin/braiding test |
| color-code metric (`D(Z2)` squared) | 6 | exhaustive raw subgroup enumeration |
| fish-toric abstract `D(Z2)` metric | 2 | abstract metric equivalence only |
| Z2/Z3/Z4 toric rough and smooth finite cuts | `K=1`, no residual logical factors, exact one-endpoint string syndrome | phase-aware FGA completion |
| folded Z4 toric diagonal | Lagrangian `Z4 + Z4` after reversing the second form | exact folded metric pairing |

The fish, color, and double-semion entries do not claim microscopic
short-string extraction. The finite toric completions verify one supplied
Hamiltonian and locality domain; they do not prove a thermodynamic gap.

## Phase 8 bounded 3D symbolic research enumeration

The E3 research fixture exhausts canonical finite-field RREF seed
presentations within an explicit two-variable Laurent exponent box and seed
rank. It checks Laurent-polynomial isotropy exactly and supports resumable
semantic transcript replay.

| Fixture | Expected result | Evidence |
|---|---|---|
| constant rank-two symplectic form over F3 | four nonzero isotropic seed subspaces among five nonzero/all seed presentations in the recorded rank bound | complete RREF search |
| common monomial translation quotient | translated seed presentations share the explicit algebraic equivalence key | exact Laurent support translation |
| 3D toric primary preflight | electric/magnetic primary isotropic sectors visible; E3 search on the model rejected | primary/full distinction |
| X-cube E3 preflight | axial/diagonal orientation difference retained; both searches rejected without full `P_boundary` | source-lock and capability check |

`bounded_exact` applies only to the recorded RREF seed domain. Saturation,
anomaly detection, local Hamiltonian completion, residual boundary order,
bulk termination, local-Clifford/stable-ancilla equivalence, stacking, and
foliated equivalence remain unsupported.

## Phase 9 finite Cheshire synthesis and static fusion

The toric operational slice starts from the same source-locked 3+1D
\(\mathbb Z_2\) plaquette-qubit Hamiltonian used in Phase 4; see
Tantivasadakarn and Chen,
[String operators for Cheshire strings in topological phases](https://arxiv.org/abs/2307.03180).
The new certificates validate supplied finite candidates. They do not derive
the condensation pattern from boundary algebra.

| Fixture | Expected finite result | Evidence |
|---|---|---|
| supplied toric open segment and closed loop candidates at radius zero | both accepted; phase/commutation, logical, pairing/radical and charge/magnetic termination certificates verify | source-locked Phase 4 Hamiltonian plus exact finite FGA |
| supplied open-segment family at radii `(1,0)` | declared static invariants agree at both recorded radii | semantic replay of both finite Hamiltonians; `bounded_exact` only for these samples |
| declared list containing a valid and a false magnetic-termination candidate | valid candidate accepted and false claim rejected; every declared list item receives a decision | complete transcript over the supplied finite list |
| two open toric segments to one open segment | local codespace ratio after/before is `1/2`; local/fixed Hamiltonian deltas stay on declared defect strata | exact finite stabilizer counting and replayable static-fusion certificate |
| noncontractible-loop topology guard | exact finite logical counts refute a component-count-only rule | Phase 4 finite-rank values reused as an adversarial guard |
| three-leg network | all physical endpoints are bound exactly once and edge/node incidence validates | exact combinatorial schema check only |

The three-leg fixture does not include a junction-local Hamiltonian or a
junction completion. Likewise, “fusion” above denotes a supplied finite
before/after static construction; no finite-depth circuit, dynamical fusion
process, superselection fusion law, phase equivalence, or thermodynamic
completeness is inferred.

The fracton reference uses the \(\mathbb Z_2\) X-cube stabilizer presentation
recorded in Ruba and Yang,
[Homological invariants of Pauli stabilizer codes](https://arxiv.org/abs/2204.06023),
Eq. (140). This citation fixes the bulk presentation only; it is not used as
literature proof that the supplied deletion is a Cheshire defect.

| Fixture | Expected finite result | Evidence |
|---|---|---|
| axial `(0,0,1)` X-cube candidate on a `2x2x2` slab, periodic in x/y and open in z | supplied local cube-X deletion absorbs a probe with two bulk syndrome entries; defect-window quotient has factors `(2,2)`, pairing rank zero and radical `(2,2)` | exact finite compilation, GF(2) syndrome and paired linear algebra |
| axial translation scan | records both terminating and nonterminating translated finite probes | exhaustive scan of translations in the supplied finite slab |
| axial length-one scaling sample | 24 qubits; bulk/defect codespace dimensions `2048/4096`; two removed instances | exact finite GF(2) stabilizer ranks |
| diagonal `(1,1,1)` request | structured `unsupported` | registered-orientation capability guard |

All X-cube Pauli-algebra fields above are exact for the supplied finite code,
but the overall result remains `experimental`: there is no certified fracton
condensation criterion, gapped completion, circuit, asymptotic mobility,
thermodynamic Cheshire classification, or completeness beyond this axial
candidate.
