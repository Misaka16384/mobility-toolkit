# Cheshire classification service API v2

This document is the implementation contract for `mt-cheshire`. It supersedes
the older supplied-candidate “species enumeration” wording. The public service
request envelope remains `mobility_toolkit.service_request.v1`; Cheshire
domain objects, operation schemas, and the service catalog are version 2.
There is no old-operation compatibility shim.

Primary sources:

- Roumpedakis--Seifnashri--Shao,
  [Higher Gauging and Non-invertible Condensation Defects](https://arxiv.org/abs/2204.02407),
  especially Eqs. (6.34)--(6.42).
- Tantivasadakarn--Chen,
  [String operators for Cheshire strings in topological phases](https://arxiv.org/abs/2307.03180),
  especially Eqs. (2), (5), (12), and Appendix A.
- Liang--Yang--Iosue--Chen,
  [arXiv:2410.11942](https://arxiv.org/abs/2410.11942), for finite Abelian
  boundary/interface enumeration benchmarks and the microscopic completion
  direction.

## Public operations

| Operation | Implemented result | Exact boundary |
|---|---|---|
| `defects.cheshire.capabilities` | model/layer/evidence capability contract | software declaration |
| `defects.cheshire.classify_abelian` | fold left/right finite metric groups and exhaust Lagrangian interfaces | complete only when the certificate says so |
| `defects.cheshire.toric2d_reference` | six defects, direct algebras, orientation, anyon action, ordered fusion | complete Z2 toric reference |
| `defects.cheshire.fuse` | ordered six-species toric fusion with TQFT coefficients | other models return structured unsupported |
| `defects.cheshire.realize_toric2d` | finite square-cellular slit Hamiltonian and support-derived diagrams | finite commuting-Pauli patch |
| `defects.cheshire.circuit_toric2d` | creation/deformation/motion/fusion Clifford witnesses | exact finite-template replay |
| `defects.cheshire.toric3d_finite_reference` | retained plaquette-qubit 3+1D toric static reference | explicit finite cellulation |
| `defects.cheshire.xcube_candidates` | three-axis mobility-enriched support catalog | not a species classification |

Removed names are not aliases:

- `defects.cheshire.static_toric`;
- `defects.cheshire.synthesize_toric`;
- `defects.cheshire.enumerate_toric`;
- `defects.cheshire.fuse_toric_static`;
- `defects.cheshire.xcube_axial_reference`.

The old finite Python research modules remain available internally for
regression and for the renamed 3+1D reference. They are not alternate service
APIs.

## Evidence and object semantics

`EvidenceStatus` has the values `source_theorem`, `computed_exact`,
`bounded_exact`, `conditional`, `conjectural`, and `unsupported`.

The common object graph is:

```text
DefectSpeciesRecord
  -> folded support
  -> optional AlgebraObjectRecord
  -> orientation reverse and Morita class
  -> bulk-sector action

ordered pair of DefectSpeciesRecord
  -> FusionResult
  -> FusionTerm
  -> FusionCoefficient1D

DefectSpeciesRecord + finite geometry
  -> LatticeRealization
  -> Hamiltonian delta + operator support + diagrams
  -> optional Toric2DCircuitRealization
```

The finite pointed cochain checker validates the full finite fusion table,
group laws, normalized associator, pentagon, support closure, normalized
multiplication cochain, `d(mu)=omega`, and an explicitly supplied coboundary
gauge transformation. Missing cochain data remains an obligation; metric data
alone does not determine a direct multiplication.

## 2D Z2 toric facts

The six species are not a fixture count. The executor folds
`C_TC` with its orientation reverse and exhausts the Lagrangian subgroups. It
then attaches the source labels

```text
1, S_e, S_m, S_psi, S_em, S_me.
```

The direct supports are

```text
1
1 + e
1 + m
1 + psi
(1 + e + m + psi, mu_0)
(1 + e + m + psi, mu_1).
```

`S_e` and `S_m` are strict Cheshire condensates. `S_psi` is the invertible
electromagnetic-duality descendant. `S_em` and `S_me` are oriented mixed
non-invertible condensation defects. Orientation reversal exchanges
`S_em <-> S_me` and fixes the other four.

All 36 ordered products are emitted. In particular,

```text
S_psi * S_psi = 1
S_em * S_me = (Z2) S_e
S_me * S_em = (Z2) S_m.
```

Here `(Z2)` is the 1+1D Z2 gauge TQFT. The recorded interval degeneracy shadow
is two, but `numeric_scalar=false` prevents changing the categorical
coefficient into an integer fusion multiplicity.

The finite lattice realization records retained, removed, truncated, and
added defect terms; in the current slit templates the truncated list is empty
and checks touching the chosen seam sites are removed explicitly. TikZ and
JSON are generated from the same `PauliOperator` supports used in the
Hamiltonian check.

For creation, `S_e` and `S_m` use exact Pauli rotations representing
Tantivasadakarn--Chen Eqs. (2) and (12) in the effective charge/flux chain.
Other finite chain witnesses are marked `derived_from_source_generators`.
Every circuit result is replayed term by term. This does not establish the
minimum possible depth or a thermodynamic spectral gap.

## Finite pointed/Abelian classification facts

The general executor first reverses the right metric orientation and folds.
For diagonal coordinate presentations it explores only the finite closure
graph of isotropic subgroups, and independently verifies each target-order
output with the exact condensation and orthogonal-complement certificate.
Other presentations retain the general resumable raw-subgroup enumerator.

Current exact literature regressions are:

| Input self-interface | Folded Lagrangians |
|---|---:|
| Z2 toric | 6 |
| Z4 toric | 22 |
| double semion | 2 |
| two toric copies / color-code metric sector | 270 |
| three-fermion | 6 |

The single two-toric/color-code metric phase separately has six raw
Lagrangian boundaries, as tested by the 2D boundary algebra layer.

Default classification scope is `oriented_morita`. The service also reports
`unoriented_morita` and `raw_folded_lagrangian`. A complete folded-support
classification is not a microscopic Hamiltonian construction. Generic ordered
fusion returns `unsupported` until direct algebra and bimodule-composition
data are supplied.

## X-cube facts and non-facts

For a fixed `z` axis the support slice is

```text
M_z = <ell_z> + <e_x,m_x> + <e_y,m_y>
q = e_x m_x + e_y m_y.
```

The same construction is rotated to `x` and `y`. Exact finite GF(2)
enumeration gives:

- 58 nonzero totally singular subgroups per fixed axis;
- 174 raw labels when all three oriented coordinate axes are retained;
- 41 support orbits under cubic rotations including the transverse swap;
- 15 planon-generated supports and 43 supports with nonzero intrinsic-lineon
  coordinate projection;
- among all 58 supports, only 4 have exclusively two-dimensionally mobile
  nontrivial constituents, 34 have exclusively line-mobile constituents, and
  20 mix the two mobility dimensions;
- one nontrivial algebraic image after quotienting all planons.

The last bullet is only a support projection. A physical foliated-equivalence
count remains unsupported without planon attachment circuits. Orientation
reversal fixes the Z2 support labels but does not certify an orientation-aware
algebra.

“Planon-generated” is deliberately not called “pure planon”: products of
planons from transverse planes can be one-dimensionally mobile.  The four
all-planon-mobile supports are the elementary single-generator supports
`<e_x>`, `<m_x>`, `<e_y>`, and `<m_y>` for a `z`-oriented line, with cyclic
axis relabeling for the other orientations.

Every default record is `support_candidate`. Optionally attaching the retained
finite source-locked `+z`-axis reference upgrades only `<ell_z>` to
`static_cheshire_candidate`.  This reference now uses the correct Eq. (140)
microscopic charge map: a consecutive `X(edge_x)` string transports q2
z-lineons, so the local Hamiltonian adds those hopping/condensation terms and
deletes precisely the anticommuting `cross_zx` checks.  In the certified finite
slab the condensate-chain local quotient is trivial, the rank deficit is one,
and the product of all replaced checks is the independent hidden-charge
operator.  The older `Z(edge_z)`/cube-X deletion probes the fracton sector and
is not an `ell_z` construction.

Neither tier is a certified Cheshire. Promotion requires:

1. associative multiplication/cochain;
2. endpoint and junction spaces;
3. mobility-enriched Morita equivalence;
4. sequential creation;
5. finite-depth deformation and ordered fusion;
6. controlled scaling and thermodynamic evidence.

The diagnostics 134 and 4590 are emitted only with `conditional` status and
the literal warning “not an X-cube Cheshire species count.”

The finite reference is not reused for the reverse orientation.  A request
combining `orientation="-"` with `include_finite_static_reference=true` is
rejected until an explicit `-z` replay certificate exists.

The default physical bookkeeping choice is always displayed:

```text
fixed oriented axis + finite-depth equivalence + retained planon dressing.
```

Orientation reversal, cubic symmetry, and planon/foliated quotients are
reported separately so this choice cannot disappear into an unlabeled count.

The shared fracton geometry IR is not axis-locked:
`PrimitiveRationalDirection` validates arbitrary primitive integer direction
vectors, `StratifiedTubeRecord` carries tube strata, endpoints, and junction
incidence, and `FractonClassificationScope` names the microscopic,
finite-depth, foliated, orientation, cubic-symmetry, and planon-dressing
choices separately.  This is representation support, not an arbitrary-direction
classification executor.  Until charge sectors, multiplication, junction
spaces, circuits, and equivalence searches are supplied and exhausted, a
slanted-line request remains `unsupported`.

## Explicitly not implemented

- a complete non-Abelian algebra-object/F-symbol solver;
- automatic direct multiplication from metric data alone;
- arbitrary algebraic-number fields for F-symbols;
- a universal thermodynamic gap proof;
- slanted X-cube lines;
- ordinary UMTC/Morita assumptions silently transplanted to fracton data;
- a total species number when object, multiplication, or equivalence searches
  lack exhaustion certificates.

Unsupported requests and missing promotion obligations remain structured
data. They must not be filled by a heuristic species count.
