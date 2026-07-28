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

## Explicit finite boundary window

`boundary.finite.analyze` uses the same phase-aware `sites` and `generators`
format as `finite.code.analyze`, plus a site-labelled support window:

```json
{
  "operation": "boundary.finite.analyze",
  "input_data": {
    "sites": [
      {"site_id": "bulk-q2", "dimension": 2},
      {"site_id": "edge-q4", "dimension": 4}
    ],
    "generators": [
      {
        "phase": 0,
        "terms": [{"site_id": "bulk-q2", "x": 0, "z": 1}]
      }
    ],
    "window": {
      "window_id": "edge-window",
      "site_ids": ["edge-q4"],
      "search_extent": [{"name": "depth", "value": 0}]
    }
  },
  "requested_certificate_level": "standard"
}
```

This computes `(S^perp intersect W)/(S intersect W)` exactly for that finite
window. It does not assert stabilization as the window grows.

Use `boundary.finite.enumerate_e1` with the same input and an optional
`budget` object. Treat E1 as complete only if
`result.certificate.certified_complete` is true. A checkpoint in a
resource-limited one-page response is evidence of incompleteness; the current
service input does not decode checkpoints for resumption.

`boundary.finite.e2.reference_z2_swap` is a source-locked two-site Z2
tangent-swap example. It demonstrates the bounded-periodic E2 certificate but
is not a general E2 JSON decoder and is not an automatically extracted toric
boundary. For generic E2, construct the public Python domain, quotient actions,
and site coordinates explicitly.

## Current scope

- Finite boundary algebra and primary projection are exact for the supplied
  finite code and cut.
- E1 is complete only for its declared finite paired group. E2 is bounded
  exact only for its declared support, period, depth, and ancilla domain.
- Automatic anyon extraction and thermodynamic completeness are unsupported.
  Do not upgrade a finite-window result to an infinite-boundary claim.
- Use `mt-halfspace` for one-sided Laurent half-spaces. Do not model a boundary
  by setting the normal translation variable to one.
