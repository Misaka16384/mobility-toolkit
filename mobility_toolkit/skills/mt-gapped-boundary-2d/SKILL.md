---
name: mt-gapped-boundary-2d
description: "Use to inspect or enumerate a supplied finite Abelian metric group, fold an interface, verify source-locked Z_d toric cuts, or verify an explicit finite phase-aware 2D boundary Hamiltonian and short-string lifts."
---

# mt-gapped-boundary-2d

Send one canonical request through the bundled adapter:

```bash
python scripts/mt-gapped-boundary-2d.py < request.json
```

Registered operations:

- `boundary.completion2d.capabilities`
- `boundary.completion2d.metric`
- `boundary.completion2d.enumerate`
- `boundary.completion2d.fold`
- `boundary.completion2d.toric_cut`
- `boundary.completion2d.verify`

Example:

```json
{
  "schema": "mobility_toolkit.service_request.v1",
  "schema_version": "1",
  "operation": "boundary.completion2d.enumerate",
  "input_data": {
    "model": "z4-toric",
    "max_pages": 1000,
    "budget": {"max_work_units": 500000}
  },
  "requested_certificate_level": "full"
}
```

Named metric models are `z2-toric`, `z4-toric`, `double-semion`,
`color-code`, and `fish-toric`. For an explicit metric, supply `orders`,
`phase_modulus`, `braiding_rows`, and `generator_spins` under
`input_data.metric`. For `fold`, put metric specifications under `left` and
`right`.

Use `toric_cut` with `modulus` and `boundary_kind` (`rough` or `smooth`).
Use `verify` only with explicit uniform-cyclic sites, named bulk and boundary
terms, short-string lifts, locality bounds, and a source scope.

## Interpretation rules

- Read enumeration completeness from the returned certificate. A truncated
  page is experimental, not a negative existence result.
- Abstract Lagrangian enumeration does not construct a microscopic boundary.
- A finite verified completion is bounded to its recorded patch and locality
  window; it does not prove a thermodynamic gap.
- Automatic anyon extraction from an arbitrary stabilizer code is unsupported.
- Folding reverses both spin and braiding on the second side.
