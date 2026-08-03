# Theorem and research scope

This document separates theorem-backed bulk invariants, exact finite algebra,
bounded searches, and research-only boundary/defect conclusions. Exactness is
owned by each service operation; it is not a package-wide label.

## Public representation

The public periodic representation is a canonical quasi-free Pauli-module
presentation. It contains:

- a finitely generated translation group;
- structured Laurent terms rather than polynomial text;
- Pauli basis elements with explicit species, component, axis, and local order;
- local-order relations;
- phase-aware stabilizer-image columns;
- a coefficient and phase modulus.

The public finite representation is phase-aware, site-labelled sparse
generalized-Pauli data over explicit local cyclic factors. Geometry,
identifications, restriction policy, and strata are separate canonical data.

Legacy row matrices and free-form polynomial strings may remain only inside
private regression fixtures. They are not accepted as canonical service input.

## Ruba--Yang charge-module invariant

For the supported uniform-prime, free-translation execution domain, the
periodic charge-module operation implements the convention of Ruba and Yang,
*Homological Invariants of Pauli Stabilizer Codes*. With

```text
R = F_p[x1^+-1, ..., xD^+-1]
P = R^(2q)
L = image(sigma)
```

the implemented invariant is

```text
Q^i = Ext_R^(i+1)(bar(P/L), R).
```

The Laurent antipode is part of the computation. A physical stabilizer request
is validated against the appropriate phase/commutation condition before it is
given a stabilizer-code interpretation. An explicitly algebraic module request
does not inherit that interpretation.

The implementation checks the universal consequences used from Proposition
25:

- `Q^i = 0` for `i >= D`;
- `dim Q^i <= D - 1 - i` for a nonzero module;
- the stronger bound `dim Q^i <= D - 2 - i` only when saturation is supplied
  independently.

The zero module uses `krull_dimension = -1`, representing the paper's
`-infinity` convention. This says that the particular charge module vanishes;
it does not say that the whole phase is trivial.

## What Krull dimension proves

For `Q^0`, Proposition 36 and Corollary 37 show that `dim Q^0 = 0` exactly when
all local point-charge classes are mobile in every noncompact lattice
direction. If `dim Q^0 > 0`, not every point-charge class is fully mobile.

Krull dimension alone does not:

- classify an individual excitation as a planon, lineon, or fracton;
- prove a formula equating a mobility count with `D - dim Q^0`;
- establish a mobility interpretation for `Q^i`, `i > 0`;
- establish topological order without the additional physical hypotheses.

An exact individual translation lattice requires an element annihilator. The
annihilator of the whole module instead describes translations common to every
charge class. General non-binomial annihilators remain inconclusive unless an
operation supplies a certified binomial-part calculation.

## Coefficient-domain scope

The canonical periodic IR represents uniform prime, uniform composite, and
nonuniform local orders. Representation support is not execution support.

The production Macaulay2 Ext execution path currently covers the
uniform-prime/free-translation domain declared by its capability response.
Composite and nonuniform requests are never coerced into that domain. Each
operation returns its own structured experimental or unsupported result when a
validated backend is unavailable.

Ruba and Yang's theory is broader: it works over `Z_n[Lambda]`, permits
nonuniform local dimensions and quasi-free modules, and contains composite
examples. Missing executable support is therefore an implementation limit, not
a limitation of the paper.

## Exact finite and relative calculations

Finite generalized-Pauli computations use finite abelian-group presentations
and explicit phase conventions. Within the declared dense/resource budget,
centralizers, quotients, logical groups, pairings, and GSD can be certified
exactly. Their certificates concern the supplied finite code only.

For an explicit finite cellular pair `(X, A)`, the relative-homology service
computes the homology of

```text
C_*(X, A) = C_*(X) / C_*(A).
```

That is exact relative homology of the supplied pair. It is not the same object
as a Laurent half-space boundary module, and it does not by itself classify an
infinite gapped boundary. Cross-representation tests compare CSS interval
relative homology with an independently constructed finite symplectic logical
quotient.

## Boundary and half-space scope

A real-space half-space is represented by a primitive rational normal and a
one-sided support condition. It is not modeled by simply quotienting a Laurent
ring by a normal-direction equation.

Current production slices include finite primary boundary algebra, supplied
pairing invariants, orientation-aware half-space compilers, and source-locked
benchmarks. The following remain unsupported as general operations:

- a certified full boundary module for arbitrary codes;
- generic secondary closure and a general boundary-to-bulk map;
- arbitrary-code anyon extraction and saturation;
- a thermodynamic gap theorem from finite local completion.

The 2D completion service is exact or bounded-exact only for the supplied
metric group, lifts, Hamiltonian, locality domain, and finite search. It is not
automatic all-boundary classification.

## 3D enumeration scope

The three enumeration levels are deliberately distinct:

- E1 exhausts a supplied finite boundary algebra;
- E2 exhausts an explicitly bounded periodic family, support/depth window, and
  equivalence relation;
- E3 enumerates symbolic seeds inside a finite exponent/rank box and remains
  experimental without saturation, anomaly, and completion proofs.

No E1/E2/E3 result is a general classification of 3D topological or fracton
boundaries. Local-Clifford, trivial-ancilla, stacking, and foliated
equivalences are not silently assumed.

## Defect and Cheshire scope

Stratified finite geometry can represent boundary components, tubes, line
cores, open-segment endpoints, and junction incidence. Cheshire service API v2
separates abstract species, direct algebra, categorical fusion, finite lattice
realization, circuit replay, and fracton evidence tier.

For 2D Z2 toric code, the generic folded metric-group executor exhausts exactly
six Lagrangians. A source-locked crosswalk attaches the six direct algebras,
orientation reversal, ordered fusion of Eq. (6.37), and anyon action of
Eq. (6.38). The `Z2` fusion coefficient is represented as a 1+1D TQFT, not the
number two. Finite pointed/Abelian inputs can be classified after the recorded
folded search is exhausted; supplied pointed fusion/associator/cochain data can
be checked exactly for normalization, pentagon, associativity, and an explicit
coboundary gauge transformation.

The finite 2D lattice operation emits bulk, removed, truncated, and added
Hamiltonian terms plus operator-support-derived TikZ/JSON. Circuit results
replay phase-aware Pauli conjugation. `S_e` and `S_m` creation use the
source-locked Pauli-rotation sequences; composed templates say so explicitly.
The prior 3+1D toric static operation is retained under the unambiguous
`toric3d_finite_reference` name.

Fracton records use the ladder `support_candidate`,
`static_cheshire_candidate`, `mobility_enriched_algebra`, and
`circuit_certified_cheshire`. Only the fourth is an unqualified certified
Cheshire. The X-cube executor exhausts 58 nonzero totally singular support
subgroups for each fixed coordinate axis and reports orientation, cubic, and
planon-projection summaries. Every catalog remains
`classification_complete=false`; the conditional 134 and 4590 diagnostics are
not species counts.

These results do not prove:

- minimum sequential or finite circuit depth;
- phase equivalence under an unrecorded tube/planon deformation;
- a gapped thermodynamic completion from a finite patch;
- a generic non-Abelian algebra-object classification;
- a physical foliated-equivalence quotient or a general fracton Cheshire
  classification.

See [Cheshire classification API v2](CHESHIRE_CLASSIFICATION_V2.md).

## Independent provenance

Finite GSD, relative homology, half-space boundary algebra, bounded
enumeration, 2D condensation, and Cheshire operations have independent
mathematical and literature provenance. They must not be described as direct
consequences of the bulk Ext invariant merely because they share a canonical
service transport.

Primary bulk source:
[Ruba--Yang, arXiv:2204.06023v3](https://arxiv.org/abs/2204.06023).

The source-locked boundary and defect references are listed in the
[roadmap](BOUNDARY_DEFECT_ROADMAP.md) and benchmark manifests.
