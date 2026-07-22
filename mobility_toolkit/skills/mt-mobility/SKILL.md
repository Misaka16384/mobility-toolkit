---
name: mt-mobility
description: "Use when an individual charge has a Laurent-binomial annihilator and you need the exact lattice H of charge-preserving translations. General non-binomial ideals are reported as inconclusive."
---

# mt-mobility — annihilator → charge-preserving translation lattice

For a charge `q` with annihilator ideal `J = Ann(q)`, this skill computes

```text
H = {a in Z^D | x^a - 1 belongs to J}.
```

Indeed, translation by `a` preserves the charge sector exactly when
`(x^a - 1)q = 0`. The physical mobility dimension returned here is `rank_Z H`.

## Exact scope

The implementation is exact when every nonzero generator is a **Laurent
binomial**. Dividing a binomial by a Laurent monomial gives a relation
`x^a = rho`. The algorithm computes the kernel lattice of this partial
character, including finite-index effects from `rho != 1`.

The preferred Python API is `compute_translation_lattice`. The older
`compute_true_mobility_dimension` name remains as a deprecated compatibility
alias, because it overstated the scope of the implementation.

It does **not** claim an exact answer for a general polynomial annihilator.
If any generator has three or more Laurent monomials after simplification, the
result has `status: "inconclusive"`, `conclusive: false`, and
`mobility_dimension: null`. In particular, this skill does not currently
decide Type-II examples whose annihilator is presented by non-binomial
polynomials.

## Laurent variables

- Legacy axes are `x,y,z`, with inverses `t,u,w`.
- Unified axes are `x1,x2,...`, with inverses `t1,t2,...`.
- An inverse variable is not an independent direction: `t = x^-1`,
  `u = y^-1`, etc. The result reports the reconstructed Laurent relations.
- Pass `all_vars` to declare spatial axes absent from the generators. Both
  `all_vars: ["x", "y"]` and `all_vars: ["x", "t", "y", "u"]`
  describe two spatial directions.
- Do not mix legacy and unified notation. Fully expand inputs; parentheses and
  division are unsupported.
- `qudit_dim` must be prime.

## Input

```json
{
  "generators": ["x*y - 1"],
  "qudit_dim": 5,
  "all_vars": ["x", "t", "y", "u"]
}
```

## Conclusive output

```json
{
  "status": "success",
  "conclusive": true,
  "guarantee": "exact_for_laurent_binomial_generators",
  "mobility_dimension": 1,
  "translation_lattice_rank": 1,
  "translation_lattice_basis": [[1, 1]],
  "kernel_basis": [[1, 1]],
  "variables": ["x", "y"],
  "laurent_relations": ["x*t - 1", "y*u - 1"]
}
```

Here `xy-1` permits the diagonal lattice `{(a,a) | a in Z}`; it does not
permit independent `x` and `y` translations. `kernel_basis` is retained as a
compatibility alias for `translation_lattice_basis`; it is no longer a
valuation-matrix nullspace.

## Inconclusive output

```json
{
  "status": "inconclusive",
  "conclusive": false,
  "mobility_dimension": null,
  "translation_lattice_basis": null,
  "reason": "At least one generator is not a Laurent binomial..."
}
```

An inconclusive result is not evidence of zero mobility.

## Example

```bash
echo '{"generators":["x*y - 1"],"qudit_dim":5,"all_vars":["x","y"]}' | python scripts/mt-mobility.py
```

The supported binomial computation is pure Python/SymPy and does not invoke
Macaulay2.
