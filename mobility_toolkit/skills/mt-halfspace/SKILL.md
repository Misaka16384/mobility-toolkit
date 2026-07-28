---
name: mt-halfspace
description: "Use for rational flat lattice half-spaces: primitive-normal geometry, exact uniform-prime one-sided contraction, primary boundary subquotients, supplied free pairing invariants, or source-locked toric/X-cube benchmarks. Use when the normal coordinate must remain one-sided rather than periodic."
---

# mt-halfspace

Send one canonical `mobility_toolkit.service_request.v1` through the bundled
adapter:

```bash
python scripts/mt-halfspace.py < request.json
```

Choose a registered operation:

- `boundary.halfspace.capabilities`
- `boundary.halfspace.geometry`
- `boundary.halfspace.compare_orientations`
- `boundary.halfspace.contract`
- `boundary.halfspace.primary`
- `boundary.halfspace.free_pairing`
- `boundary.halfspace.toric2d`
- `boundary.halfspace.toric3d_primary`
- `boundary.halfspace.secondary_example`
- `boundary.halfspace.xcube_orientation`

Example:

```json
{
  "schema": "mobility_toolkit.service_request.v1",
  "schema_version": "1",
  "operation": "boundary.halfspace.geometry",
  "input_data": {"normal": [1, 1, 0], "boundary_offset": 0},
  "requested_certificate_level": "standard",
  "assumptions": ["flat rational lattice half-space"]
}
```

For `contract` and `primary`, put `coefficient_modulus`, `normal`,
`ambient_rank`, and `generator_columns` under `input_data.bulk`. Each Laurent
term has `coefficient`, `tangent_exponents`, and integer `depth`.
`free_pairing` accepts an explicitly supplied free tangent-Laurent pairing
matrix and requires a uniform prime coefficient field.

## Interpretation rules

- Never replace a half-space by `R/(n-1)` or set the normal variable to one.
- Keep the primary subquotient distinct from the full boundary module. Use
  `secondary_example` for the source-locked strict-inclusion counterexample.
- Treat Macaulay2 contraction and free-pairing claims only within their
  cataloged prime/free-module constraints.
- Do not extrapolate X-cube results across normals.
- Preserve the returned service envelope, exactness, theorem scope, warnings,
  and certificate. Report `unsupported` instead of substituting a heuristic.
