---
name: mt-gapped-boundary-2d
description: "Enumerate exact Lagrangian condensates of an explicitly supplied finite Abelian metric group, inspect fusion/spin/braiding and folded interfaces, or machine-verify an explicitly supplied finite 2D generalized-Pauli boundary Hamiltonian with short-string lifts. Use for Z_d toric rough/smooth boundaries, double-semion/color/fish abstract metric benchmarks, anyon termination, finite boundary logicals/GSD, or structured capability refusal when automatic anyon extraction lacks a saturation certificate."
---

# mt-gapped-boundary-2d

Use the bundled script for the exact algebraic and finite-local parts of a 2D
Abelian boundary calculation.

## Choose the operation

- `metric`: report fusion SNF, spin, and braiding for a named or explicit
  finite metric group.
- `enumerate`: exhaust raw bosonic subgroups and identify all Lagrangians of
  that metric group. Read `exactness` and the search-domain certificate.
- `completion-benchmark`: verify the source-locked finite Z2/Z4 toric
  `rough` or `smooth` cut completion.
- `verify-completion`: verify caller-supplied uniform-prime or uniform-composite
  finite Pauli terms, short-string lifts, locality bounds, fusion relations,
  termination syndrome, finite GSD, and boundary logicals.
- `fold`: reverse the second metric form before treating an interface as a
  boundary.
- `capabilities`: report what is and is not implemented.

Run:

```bash
python scripts/mt-gapped-boundary-2d.py < input.json
```

Named models are `z2-toric`, `z4-toric`, `double-semion`, `color-code`, and
`fish-toric`. The latter three are abstract metric benchmarks unless separate
microscopic lifting data are supplied.

```json
{"operation":"enumerate","model":"z4-toric"}
```

```json
{
  "operation": "completion-benchmark",
  "model": "z4-toric",
  "boundary_kind": "rough"
}
```

For `verify-completion`, supply `metric`, uniform cyclic `sites`, named
`bulk_terms` and `boundary_terms`, `string_lifts`, and `locality`. Each Pauli
term uses `{"site_id":"q0","x":0,"z":1}`. Remote excitation IDs must name the
exact noncommuting bulk terms of that string; the verifier rejects a resealed
but false syndrome.

## Interpretation

- Abstract metric-group exhaustion is `certified_exact`.
- A verified local completion is `bounded_exact` in its recorded finite patch,
  depth, diameter, and support bounds.
- Lagrangianity plus a finite commuting completion does not by itself prove a
  thermodynamic spectral gap.
- Do not claim automatic anyon extraction from an arbitrary stabilizer code.
  Without explicit short-string/saturation data, return `unsupported`.
- Do not transfer this 2D Lagrangian criterion to 3D or fracton boundaries.
- Folding must negate both spin and braiding on the second side.

The script uses the `python-flint` finite backend and does not use Macaulay2.
