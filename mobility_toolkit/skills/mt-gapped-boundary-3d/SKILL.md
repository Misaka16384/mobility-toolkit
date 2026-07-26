---
name: mt-gapped-boundary-3d
description: "Use for bounded symbolic E3 boundary-submodule enumeration from a supplied full free tangent-Laurent pairing, or for honest orientation-aware toric/X-cube preflights. Use when exact bounded scope and unsupported thermodynamic claims must remain explicit."
---

# mt-gapped-boundary-3d

Send one canonical request through the bundled adapter:

```bash
python scripts/mt-gapped-boundary-3d.py < request.json
```

Registered operations:

- `boundary.symbolic3d.capabilities`
- `boundary.symbolic3d.enumerate`
- `boundary.symbolic3d.toric_primary_preflight`
- `boundary.symbolic3d.xcube_preflight`

Example:

```json
{
  "schema": "mobility_toolkit.service_request.v1",
  "schema_version": "1",
  "operation": "boundary.symbolic3d.enumerate",
  "input_data": {
    "full_boundary_module_supplied": true,
    "coefficient_modulus": 3,
    "normal": [0, 0, 1],
    "generator_labels": ["e", "m"],
    "pairing_matrix": [
      [[], [{"coefficient": 1, "exponents": [0, 0]}]],
      [[{"coefficient": 2, "exponents": [0, 0]}], []]
    ],
    "exponent_bounds": [[0, 0], [0, 0]],
    "max_generators": 2,
    "max_pages": 1
  },
  "requested_certificate_level": "full",
  "equivalence_relation": "raw_constant_generator_change"
}
```

The symbolic operation accepts only an explicitly asserted full free boundary
module. Its finite coefficient box, seed rank, page budget, and implemented
equivalence are part of the service input and certificate.

## Interpretation rules

- `bounded_exact` certifies only the recorded finite seed domain after complete
  exhaustion. A resumable prefix remains experimental.
- Primary-only data is insufficient for E3 enumeration.
- Projective Laurent isotropy is exact. Phase assignment is not
  machine-verified; at even prime a quadratic refinement is still required.
- Saturation, anomaly detection, local completion, residual boundary order,
  bulk termination, and thermodynamic classification are unsupported.
- Do not extrapolate X-cube conclusions across unregistered normals.
- The implemented algebraic seed equivalences are not local-Clifford, stable,
  stacking, or foliated equivalence.
