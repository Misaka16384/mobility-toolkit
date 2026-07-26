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

## Current scope

- The capability contract covers finite Abelian groups, composite and mixed
  local dimensions, phase-aware Pauli arithmetic, and finite stabilizer
  analysis.
- The skill is a transport shim, not a second algorithm dispatcher. An
  unregistered operation must fail through the shared service layer.
- Exact code distance and thermodynamic/Laurent conclusions are outside this
  skill. Use an operation-specific service only when the catalog advertises it.
