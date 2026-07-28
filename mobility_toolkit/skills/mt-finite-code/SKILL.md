---
name: mt-finite-code
description: "Use for finite generalized-Pauli and stabilizer-code arithmetic, especially composite or mixed local dimensions, phase-aware commutation, finite centralizers, logical groups, and GSD. Query the unified service capability contract before relying on a backend."
---

# mt-finite-code

Send a canonical service request through the bundled adapter:

```bash
python scripts/mt-finite-code.py < request.json
```

Start with the capability operation:

```json
{
  "operation": "finite.code.capabilities",
  "input_data": {},
  "requested_certificate_level": "standard",
  "assumptions": ["software capability declaration"]
}
```

Pass any further operation using the same versioned request shape. Preserve the
returned `mobility_toolkit.service_execution.v1` envelope; do not unwrap its
result or invent a stronger exactness level.

## Analyze an explicit finite code

Use `finite.code.analyze`. The semantic Pauli input is sparse, site-labelled,
and phase aware:

```json
{
  "operation": "finite.code.analyze",
  "input_data": {
    "sites": [
      {"site_id": "q2", "dimension": 2},
      {"site_id": "q4", "dimension": 4}
    ],
    "generators": [
      {
        "phase": 0,
        "terms": [
          {"site_id": "q2", "x": 0, "z": 1},
          {"site_id": "q4", "x": 0, "z": 2}
        ]
      }
    ]
  },
  "requested_certificate_level": "full"
}
```

Every generator must include its central `phase`, even when it is zero. Every
local term must include `site_id`, `x`, and `z`. Local dimensions may be mixed
and composite. Do not flatten these terms into blocked/interleaved vectors.
There is no `qudit_dim` or `prime_bypass` field.

## Current scope

- The capability contract covers finite Abelian groups, composite and mixed
  local dimensions, phase-aware Pauli arithmetic, and finite stabilizer
  analysis.
- `finite.code.analyze` returns the finite centralizer, logical paired
  quotient, codespace dimension, and scalar-relation validation certificate.
- The skill is a transport shim, not a second algorithm dispatcher. An
  unregistered operation must fail through the shared service layer.
- Exact code distance and thermodynamic/Laurent conclusions are outside this
  skill. Use an operation-specific service only when the catalog advertises it.
