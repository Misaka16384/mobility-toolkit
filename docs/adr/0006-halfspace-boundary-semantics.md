# ADR 0006: Half-space boundary modules and bounded enumeration

Status: accepted

Date: 2026-07-26

## Context

A real-space boundary removes translations in one oriented normal direction.
It is therefore not represented by setting that translation to one.  For a
primitive normal \(n\), the relevant lattice objects are

\[
H_n=\{r\in\mathbb Z^D:n\cdot r\geq 0\},\qquad
\Lambda_\parallel=\ker(n:\mathbb Z^D\to\mathbb Z),
\]

and the one-sided coefficient object is

\[
A[n]=\mathbb F_p[\Lambda_\parallel][n].
\]

For a bulk stabilizer image \(L\subset P\), Ruba--Yang define

\[
L_H=L\cap P_H,\qquad
P_\partial=L_H^{\perp_H}/L_H.
\]

The projected bulk or primary submodule

\[
P_\partial^{\mathrm{pr}}=\pi_H(L)/L_H
\]

can be strictly smaller than \(P_\partial\).  The difference consists of
secondary boundary operators.  Any interface that conflates these two
objects can return the wrong boundary pairing and the wrong boundary charge
module.

## Decision

### Oriented geometry

- Every flat half-space is identified by a primitive integer normal and an
  affine offset.
- Opposite normals are different oriented half-spaces.
- An exact unimodular basis change exposes
  \(\Lambda_\parallel\oplus\mathbb Z n\).
- Normal depth remains one-sided.  No half-space operation may replace it by
  \(R/(n-1)\), evaluate the normal monomial at one, or silently wrap it
  periodically.

### Boundary-module layers

The public data model keeps the following layers separate:

1. \(L_H\), computed by normal clearing and saturation;
2. \(P_\partial^{\mathrm{pr}}\), compiled from every and only bulk translates
   whose support crosses the cut;
3. full \(P_\partial\), available only when a separate centralizer/secondary
   argument supplies it;
4. the quasi-symplectic pairing on a supplied boundary module;
5. its radical and boundary charge cokernel;
6. a boundary-to-bulk map, which is a separate model-dependent computation.

A result at one layer is not evidence that the next layer was computed.

### E2 finite-periodic completeness

An E2 request binds:

- one finite paired boundary algebra;
- explicit adapted tangent/depth coordinates for every finite-window site;
- pairing-preserving commuting tangent automorphisms;
- a unit-cell period;
- a local generator support envelope;
- coefficient, ancilla, completion, and candidate-family bounds.

For every allowed anchor support \(J\), the finite FGA compiler computes the
exact quotient image \(U_J\).  Its full finite orbit under the supplied
microscopic tangent actions is also compiled.  A candidate subgroup \(H\) is
support-generable exactly when

\[
H=\sum_{J,r}\left(H\cap T^r U_J\right),
\]

where the sum uses every distinct translated support image in the finite
realization.  Period compatibility is checked separately by
\(T_i^{p_i}H=H\).  This permits independent local seeds at different
sublattice offsets and does not accidentally replace period-\(p\) invariance
by period-one invariance.

`bounded_exact` means that E1 was exhausted and every E1 candidate was tested
against this recorded E2 domain.  It does not mean:

- completeness for a larger finite window;
- completeness after adding ancillas when the ancilla bound is unsupported;
- local-Hamiltonian completion when that candidate family is unsupported;
- E3 symbolic or thermodynamic boundary completeness.

Checkpoints chain both E1 and E2 output transcripts.  Resume validation
recomputes support, period, acceptance, and emitted-result decisions rather
than trusting a resealed hash.

## Current operation-specific capability

| Operation | Exactness / status |
|---|---|
| primitive normal, tangent lattice, orientation comparison | `certified_exact` |
| uniform-prime \(L_H\) contraction | `certified_exact` |
| uniform-prime primary subquotient | `certified_exact` |
| invariants of a caller-supplied free boundary pairing | `certified_exact` |
| E2 translation-compatible submodules, no ancillas | `bounded_exact` after exhaustion |
| E2 ancillary-site enumeration | `unsupported` |
| E2 local-Hamiltonian completions | `unsupported` |
| generic full \(P_\partial\) and secondary closure | `unsupported` |
| generic boundary-to-bulk map | `unsupported` |
| 2D toric \(y\geq0\) full module | model-specific `certified_exact` |
| 3D toric \(z\geq0\) primary module | model-specific `certified_exact` |
| Ruba--Yang Example 45 primary/secondary distinction | model-specific `certified_exact` |
| X-cube registered orientations | source-locked `experimental` oracle |

The supplied-free-pairing operation computes the radical kernel and the
pairing cokernel, annihilator, and Krull dimension.  It does not construct the
full boundary module that should be supplied to it.

## Physics validation

- The 2D \(\mathbb Z_2\) toric half-space has primary equals full boundary
  module, pairing \(1+x\), boundary charge group
  \(\mathbb Z_2\oplus\mathbb Z_2\), and an isomorphic boundary-to-bulk map.
- Ruba--Yang Example 45 has a proper secondary extension with
  \((1+x)e'_1=e_1\); the primary pairing has a nonzero charge cokernel while
  the full pairing is unimodular.
- The 3D \(\mathbb Z_2\) toric \(z\geq0\) primary pairing contains
  \(1+x\) and \(1+y\) electric--magnetic entries and agrees with independent
  finite periodic slab ranks.
- For X-cube, the axial normal \((0,0,1)\) and diagonal normal \((1,1,1)\)
  retain their distinct source-locked boundary-to-bulk behavior.  Other
  normals are not extrapolated.

Primary sources:

- B. Ruba and B. Yang,
  [Witt Groups and Bulk-Boundary Correspondence for Stabilizer States](https://arxiv.org/abs/2509.10418).
- Z. Liang, B. Yang, J. T. Iosue, and Y.-A. Chen,
  [Operator algebra and algorithmic construction of boundaries and defects in (2+1)D topological Pauli stabilizer codes](https://arxiv.org/abs/2410.11942).

## Consequences

- Generic primary computation can be stable while generic full boundary
  computation remains unavailable; capability reporting must say so.
- A finite radical is not automatically a thermodynamic boundary charge
  module.
- E2 certificates are meaningful only together with their finite algebra,
  coordinates, translated support images, actions, period, and candidate
  family.
- E3 algorithms may consume a full boundary pairing, but primary-only model
  fixtures must fail their preflight rather than being promoted implicitly.
