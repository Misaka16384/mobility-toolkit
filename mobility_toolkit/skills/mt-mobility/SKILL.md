---
name: mt-mobility
description: "Layer 2->3 (algebra -> physics). Compute the TRUE physical mobility dimension of an excitation from its annihilator-ideal generators, resolving the Krull-vs-mobility gap for Type-II fractons. Use when you have annihilator generators (e.g. from mt-homology) and need the exact number of free directions, not just the coarse class. Needs Macaulay2."
---

# mt-mobility — annihilator generators → true mobility dimension (Layer 2→3)

Computes the **exact** number of free directions of an excitation from the **Layer 2**
annihilator-ideal generators, via prime divisors and valuations. This is the precise
counterpart to **mt-classify**: where Krull dimension gives a generic upper bound,
this gives the true mobility — which is strictly lower for **Type-II fractons**.

## Conventions

- **`qudit_dim` must be prime.**
- `generators` are the annihilator-ideal generators (strings), e.g. the
  `annihilator_generators` field returned by **mt-homology**.
- Variables are single lowercase letters; pass `all_vars` to fix the ring explicitly
  (otherwise the variables are inferred from the generators).

## Input
```json
{
  "generators": ["x*y - 1", "x^2 - 1"],
  "qudit_dim": 2,
  "all_vars": ["x", "y"]
}
```
`all_vars` is optional.

## Output
```json
{ "status": "success",
  "mobility_dimension": 1,
  "valuation_matrix": [[...]],
  "divisors": ["..."],
  "kernel_basis": [[...]],
  "variables": ["x", "y"] }
```
`mobility_dimension` is the true number of free directions (0 = immobile fracton).

## Example
```bash
# Typically: run mt-homology, take its annihilator_generators, then:
echo '{"generators": ["x - 1", "y - 1"], "qudit_dim": 2}' | python scripts/mt-mobility.py
```

## Backend
Needs Macaulay2. If a run errors, check it with the **mt-doctor** skill first.
