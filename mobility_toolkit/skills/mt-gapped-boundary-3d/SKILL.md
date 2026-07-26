---
name: mt-gapped-boundary-3d
description: "Use for E1 finite, E2 bounded-periodic, or E3 bounded symbolic candidate enumeration at a three-dimensional generalized-Pauli boundary. The skill exposes exact search domains, orientation-aware toric/X-cube preflights, and explicit unsupported results instead of claiming a general fracton boundary classification."
---

# mt-gapped-boundary-3d

Choose the enumeration level before interpreting the output:

- E1 exhausts isotropic/Lagrangian subgroups of one supplied finite paired
  boundary algebra. Use the Python API `enumerate_e1_subgroups`.
- E2 exhausts translation-compatible subgroups inside one recorded finite
  algebra, microscopic translation action, unit-cell period, and local support
  domain. Use the Python API `enumerate_e2_bounded_periodic`.
- E3 `symbolic` enumerates finite-rank seed presentations over a two-variable
  tangent Laurent ring inside explicit coefficient-support and seed-rank
  bounds.

The bundled adapter supports E3 and source-locked preflights:

```bash
python scripts/mt-gapped-boundary-3d.py < input.json
```

Example:

```json
{
  "operation": "symbolic",
  "full_boundary_module_supplied": true,
  "coefficient_modulus": 3,
  "normal": [0, 0, 1],
  "generator_labels": ["e", "m"],
  "pairing_matrix": [
    [[], [{"coefficient": 1, "exponents": [0, 0]}]],
    [[{"coefficient": 2, "exponents": [0, 0]}], []]
  ],
  "exponent_bounds": [[0, 0], [0, 0]],
  "max_generators": 2
}
```

Operations:

- `symbolic`: bounded E3 RREF seed enumeration.
- `toric3d-primary-preflight`: verify the frozen primary pairing and refuse to
  pass it off as a full boundary module.
- `xcube-preflight`: preserve the registered axial/diagonal orientation
  result and refuse E3 when full \(P_\partial\) is unavailable.
- `capabilities`: report implemented and unsupported analyses.

## Interpretation rules

- `bounded_exact` proves exhaustion only of the recorded finite seed domain.
  It is not an E3 thermodynamic completeness theorem.
- The symbolic operation requires an explicit
  `full_boundary_module_supplied: true` assertion. Primary-only data is not
  accepted as full \(P_\partial\).
- Projective Laurent isotropy is machine-verified. Odd-prime phase lifting is
  only marked available by a canonical convention; no phase assignment
  witness is claimed.
- Saturation, anomaly detection, local Hamiltonian completion, residual
  boundary topological order, and bulk termination remain `unsupported` in
  E3 candidates.
- X-cube conclusions are locked to exact registered normals. Do not
  extrapolate them.
- Raw and common-translation quotients are algebraic seed-presentation
  equivalences, not local-Clifford, stable-ancilla, stacking, or foliated
  equivalence.

For resumable long E3 searches, call the Python API and pass the returned
`Symbolic3DCheckpoint` back unchanged. The JSON adapter can run several pages
inside one invocation but does not deserialize an externally edited
checkpoint.
