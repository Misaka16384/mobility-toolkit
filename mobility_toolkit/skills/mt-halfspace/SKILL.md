---
name: mt-halfspace
description: "Use for rational flat lattice half-spaces: primitive normals and tangent lattices, exact uniform-prime L_H contraction, primary boundary subquotients, supplied free boundary-pairing invariants, bounded-periodic E2 enumeration, and the built-in toric/X-cube literature benchmarks. Use when a boundary must retain a one-sided normal coordinate rather than imposing periodicity."
---

# mt-halfspace — bulk Laurent code → oriented half-space data

Choose an operation by the claim you need:

- `geometry`: primitive normal, adapted unimodular basis, tangent lattice, and
  orientation comparison. Internal exact arithmetic only.
- `contract`: compute \(L_H=L\cap A[n]^m\) by normal clearing followed by
  Macaulay2 saturation. Uniform prime coefficients only.
- `primary`: run `contract`, then construct the exact subquotient
  \(P_\partial^{pr}=\pi_HL/L_H\). This is not the full boundary module.
- `free-pairing`: for an already supplied free \(A\)-module pairing, compute
  its radical and \(E_P=\operatorname{coker}\Omega\), annihilator, and Krull
  dimension with Macaulay2.
- `toric2d`, `toric3d`, `secondary-example`, or `xcube`: run the corresponding
  source-locked physics benchmark.
- `capabilities`: report implemented and unsupported operations.

Run the bundled adapter:

```bash
python scripts/mt-halfspace.py < input.json
```

For `contract` and `primary`, encode the bulk module as:

```json
{
  "operation": "primary",
  "bulk": {
    "coefficient_modulus": 2,
    "normal": [0, 1],
    "ambient_rank": 2,
    "generator_columns": [
      [
        [
          {"coefficient": 1, "tangent_exponents": [0], "depth": -1},
          {"coefficient": 1, "tangent_exponents": [0], "depth": 0}
        ],
        []
      ]
    ]
  }
}
```

For `free-pairing`, each matrix entry is a list of tangent Laurent terms:

```json
{
  "operation": "free-pairing",
  "coefficient_modulus": 2,
  "tangent_rank": 1,
  "generator_labels": ["a", "b"],
  "pairing_matrix": [
    [[], [{"coefficient": 1, "exponents": [0]}]],
    [[{"coefficient": 1, "exponents": [0]}], []]
  ]
}
```

## Non-negotiable interpretation rules

- Never model a half-space by \(R/(n-1)\) or by setting the normal variable to
  one. That produces a periodic/restricted direction, not a boundary.
- Treat `primary` and full \(P_\partial\) as different objects. Secondary
  operators can make the inclusion strict; `secondary-example` freezes the
  published Ruba--Yang Example 45 counterexample.
- Treat finite E1/E2 results as exact only for their recorded finite
  window/search domain. They do not prove E3 thermodynamic completeness.
- Do not infer a boundary charge module from a finite-window pairing radical.
  Use `free-pairing` only after a valid free boundary module is supplied.
- Do not extrapolate X-cube conclusions across orientations. Only the exact
  registered normals return a literature result.
- If an operation returns `unsupported`, report the missing capability instead
  of substituting a heuristic answer.

For E2, use the Python API
`mobility_toolkit.boundary.enumerate_e2_bounded_periodic`; its certificate
records the precompiled finite algebra, tangent actions, period, support
envelope, ancilla bound, termination, and unenumerated scope.
