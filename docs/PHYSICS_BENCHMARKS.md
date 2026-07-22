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
