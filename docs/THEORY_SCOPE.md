# Theorem scope and conventions

This document states exactly which parts of Ruba and Yang, *Homological
Invariants of Pauli Stabilizer Codes*, are implemented by the homology path.
The implementation targets the uniform prime-qudit, free-Pauli-module case.
The paper itself is more general than this backend.

## Algebraic convention

Let

```text
R = F_p[x1^+-1, ..., xD^+-1]
P = R^(2q)
```

and let each input row be one stabilizer generator in the coordinate order

```text
[X1, ..., Xq, Z1, ..., Zq].
```

The translator transposes those rows to obtain the column map `sigma: F -> P`.
The Laurent antipode is `bar(x_i) = x_i^-1`; the adjoint is transpose followed
by this antipode. A physical stabilizer input is accepted only when `2q` is even
and

```text
sigma^dagger lambda sigma = 0.
```

Callers working with an arbitrary module presentation, rather than a physical
stabilizer code, must opt out explicitly with `validate_stabilizer=False`. Such a
result is labelled algebra-only and receives no stabilizer-code interpretation.

## Implemented invariant

For a validated stabilizer code, the homology command computes Definition 22:

```text
Q^i = Ext_R^(i+1)(bar(P/L), R),    L = image(sigma).
```

The bar is part of the computation, not only a display convention. Returned
annihilator generators therefore use the translation directions of `Q^i` in the
paper's convention.

The result also checks the universal parts of Proposition 25:

- `Q^i = 0` for `i >= D`;
- `dim Q^i <= D - 1 - i` for a nonzero module;
- when the caller independently supplies `saturated=True`, the stronger bound
  `dim Q^i <= D - 2 - i` is checked.

The zero module is represented by `krull_dimension = -1`, corresponding to the
paper's `-infinity` convention. It means only that this charge module vanishes;
it does not say that the whole code or phase is trivial.

## What Krull dimension proves about mobility

For `Q^0`, Proposition 36 and Corollary 37 prove that `dim Q^0 = 0` exactly when
all local point-charge classes are mobile in every noncompact lattice direction.
For `dim Q^0 > 0`, Krull dimension alone says that not all point-charge classes
are fully mobile. It does not identify an individual excitation as a planon,
lineon, or immobile fracton, and there is no theorem equating a mobility count
with `D - dim Q^0`.

For `Q^i` with `i > 0`, a direct mobility interpretation is not established by
the paper. The API therefore labels it conjectural/undetermined rather than
reusing the point-charge theorem.

Topological order is also not inferred from Krull dimension alone. That phrase
requires additional physical hypotheses (for example the relevant Lagrangian,
saturation, and absence-of-symmetry-breaking conditions) supplied and justified
outside the Ext calculation.

## Exact translation-lattice subproblem

For an individual charge with annihilator `J`, a lattice displacement `a` is
certified when `x^a - 1` belongs to `J`. The mobility helper implements the exact
rank of this translation lattice for Laurent binomial ideals. Forward and inverse
symbols such as `x1` and `t1` are one spatial axis, not independent variables.

Homology returns `Ann(Q^p)`, not the annihilator of a chosen element `q`. Feeding
that module annihilator to the helper computes translations common to every
charge class. An individual mobility claim requires the separately computed
element annihilator `Ann(q)`.

An arbitrary non-binomial generating set can hide additional binomials. Until a
general binomial-part algorithm is implemented, the helper reports
`inconclusive` for that case instead of claiming an exact physical answer.

## Backend limitations, not theory limitations

The current Ext backend supports a uniform prime qudit dimension and a free Pauli
module. Ruba and Yang work over `Z_n[Lambda]`, allow nonuniform qudit dimensions
and quasi-free modules, and include composite examples such as a `Z_4` toric-code
phase. Composite and nonuniform support is therefore an implementation gap.
`prime_bypass` can be useful to other toolkit paths, but it does not make the
Macaulay2 Ext path valid over a composite coefficient ring.

## Deliberately separate features

The GSD, finite-torus periodicity, annihilator-fusion, and boundary-gauge
algorithms have independent provenance. In particular, the existing fusion API
is not the paper's Cech-cocycle braiding construction. The toolkit currently does
not implement the paper's `S` and `Z` modules, coarse-graining theorem, Cech
representatives, higher-form symmetry construction, or braiding pairing.

Primary source:
[Ruba--Yang, arXiv:2204.06023v3](https://arxiv.org/abs/2204.06023).
