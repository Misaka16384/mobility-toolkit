# Validation and literature benchmarks

This document records the corrected validation suite for the Ruba--Yang charge
modules. The precise implementation boundary is in
[THEORY_SCOPE.md](THEORY_SCOPE.md).

## What is validated

For generator rows in `[X_1,...,X_q,Z_1,...,Z_q]` coordinates, the homology path
now verifies

```text
sigma^dagger lambda sigma = 0
```

and computes

```text
Q^p = Ext_R^(p+1)(bar(P/L), R).
```

The suite checks the Laurent antipode on the presentation and annihilator,
ambient `spatial_dim`, Proposition 25 bounds/vanishing, cache isolation by
invariant convention, and theorem-safe physical output.

## Reference results

| Model / case | Expected result | Checked result |
|---|---:|---:|
| 2D toric code, `Q^0` | Krull dimension `0` | `0` |
| Full X-Cube sigma, Ruba--Yang Eq. (98), `Q^0` | Krull dimension `1` | `1` |
| Full X-Cube, `Q^1` and `Q^2` | zero modules | `-1`, `-1` |
| Algebra-only `F_5[x^+-1]`, presentation `x-2` | barred annihilator at `x=3` | conjugated ideal returned |
| Same presentation embedded in `D=3` | unused axes remain in support | dimension reflects the 3D ring |
| Laurent annihilator `(xy-1)` | translation lattice rank `1`, direction `(1,1)` | rank `1`, basis `(1,1)` |
| Non-binomial Haah-style annihilator | no supported exact lattice algorithm | structured `inconclusive` |

The X-Cube benchmark uses the complete `6 x 3` map, represented by three input
rows of length six. The old reduced `4 x 2` toy matrix and the old `d1=1` seed
were removed. Section 7.7 states that the complete sigma is injective and `L` is
free, hence `Q^i=0` for every `i>0`.

The focused physics/cache/literature suite passes 25 tests, including 11 live
Macaulay2 benchmarks. Core antipode/validation tests and translation-lattice
tests are also part of the normal pytest suite.

## Correct physical reading

Ruba--Yang Corollary 37 gives a module-level statement for `Q^0`:

- dimension zero iff every local point-charge class is mobile in every
  noncompact direction;
- positive dimension means only that not every point-charge class is fully
  mobile.

It does not imply `mobility_dimension = D - Krull_dimension`, distinguish
planons/lineons/fractons, or classify individual charges from the support of the
whole module. Higher `Q^p` mobility is marked conjectural. Topological order is
only exposed when the caller independently supplies the required physical
assumptions.

## Composite coefficient rings

Failure of the current Ext implementation over `ZZ/4` or `ZZ/12` is a backend
limitation, not a limitation of the theory. Ruba--Yang work over
`Z_n[Lambda]`, include nonuniform qudits, and give a `Z_4` toric-phase example.
The homology API therefore raises an explicit `NotImplementedError` before
calling Macaulay2 for composite `qudit_dim`.

GSD and finite-torus periodicity are separate algorithms and continue to cover
composite examples such as the WCF/DCY seeds. Those checks do not validate the
Ruba--Yang Ext theorem.

## Sources

- [Ruba--Yang, arXiv:2204.06023v3](https://arxiv.org/abs/2204.06023)
- [Published version, Communications in Mathematical Physics](https://link.springer.com/article/10.1007/s00220-024-04991-y)
