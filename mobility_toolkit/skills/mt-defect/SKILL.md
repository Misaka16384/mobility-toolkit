---
name: mt-defect
description: "Use for finite stratified boundaries, line or tubular defects, endpoints, junction incidence, and Cheshire capability discovery. Query the unified defects service when deciding which static, synthesis, fusion, or fracton-reference claims are implemented."
---

# mt-defect

Send a canonical service request through the bundled adapter:

```bash
python scripts/mt-defect.py < request.json
```

Inspect the defect capability contract first:

```json
{
  "operation": "defects.capabilities",
  "input_data": {},
  "requested_certificate_level": "standard",
  "assumptions": ["finite static defect analysis"]
}
```

Preserve the returned `mobility_toolkit.service_execution.v1` envelope and its
operation-specific exactness. Use `mt-cheshire` after the catalog identifies a
supported Cheshire operation.

## Current scope

- Finite toric open/closed static data, supplied-radius tube-to-line checks,
  supplied-candidate enumeration, and finite before/after static fusion have
  bounded operational slices.
- Junction support is incidence and strata validation, not an automatic
  junction-local gapped completion.
- The X-cube axial reference is experimental even where its finite Pauli data
  are exact.
- Finite-depth circuits, phase equivalence, condensation discovery, and
  thermodynamic completeness are unsupported.
