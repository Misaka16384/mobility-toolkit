---
name: mt-boundary-algebra
description: "Use for explicit finite boundary cuts, finite boundary paired groups, primary projections, E1 subgroup enumeration, or bounded-periodic E2 searches. Use this skill when the claim concerns a supplied finite code or an explicitly bounded search domain, not an infinite half-space."
---

# mt-boundary-algebra

Send a canonical service request through the bundled adapter:

```bash
python scripts/mt-boundary-algebra.py < request.json
```

Inspect the current finite-boundary contract first:

```json
{
  "operation": "boundary.finite.capabilities",
  "input_data": {},
  "requested_certificate_level": "standard",
  "assumptions": ["finite and thermodynamic scopes remain distinct"]
}
```

Preserve the returned `mobility_toolkit.service_execution.v1` envelope,
including exactness, assumptions, certificate, provenance, and warnings.

## Current scope

- Finite boundary algebra and primary projection are exact for the supplied
  finite code and cut.
- E1 is complete only for its declared finite paired group. E2 is bounded
  exact only for its declared support, period, depth, and ancilla domain.
- Automatic anyon extraction and thermodynamic completeness are unsupported.
  Do not upgrade a finite-window result to an infinite-boundary claim.
- Use `mt-halfspace` for one-sided Laurent half-spaces. Do not model a boundary
  by setting the normal translation variable to one.
