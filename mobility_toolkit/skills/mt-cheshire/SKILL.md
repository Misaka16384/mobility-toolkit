---
name: mt-cheshire
description: "Use to analyze, synthesize, finitely enumerate, or statically fuse Cheshire line defects: certified finite 3+1D Z2 toric open/closed defects, supplied-radius tube shrinking, explicit endpoint/junction networks, or the experimental axial X-cube reference."
---

# mt-cheshire

Send one canonical request through the bundled adapter:

```bash
python scripts/mt-cheshire.py < request.json
```

Registered operations:

- `defects.cheshire.capabilities`
- `defects.cheshire.static_toric`
- `defects.cheshire.synthesize_toric`
- `defects.cheshire.enumerate_toric`
- `defects.cheshire.fuse_toric_static`
- `defects.cheshire.xcube_axial_reference`

Example:

```json
{
  "schema": "mobility_toolkit.service_request.v1",
  "schema_version": "1",
  "operation": "defects.cheshire.synthesize_toric",
  "input_data": {
    "shape": [2, 1, 1],
    "periodic_axes": [],
    "candidate_id": "open-electric",
    "radii": [1, 0],
    "defects": [{
      "defect_id": "gamma",
      "topology": "open_segment",
      "cube_bases": [[0, 0, 0], [1, 0, 0]]
    }]
  },
  "requested_certificate_level": "full"
}
```

For bounded species enumeration, replace `defects` by an explicit
`candidate_sets` list. For static fusion, supply `fusion_id`,
`before_defects`, and `after_defects`. Optional `before_network` and
`after_network` objects contain nodes, edges, endpoint bindings, strata, and
provenance; their certificate covers incidence and strata only unless the
Hamiltonian itself includes a junction-local completion.

## Interpretation rules

- Finite stabilizer, commutation, logical, pairing, and syndrome certificates
  are exact only in their recorded cellulation.
- Tube shrinking compares only supplied finite radii and declared invariants.
  It does not construct a finite-depth circuit or prove phase equivalence.
- Static fusion is not a thermodynamic fusion rule.
- Species enumeration is complete only over the supplied finite candidate list.
- The X-cube axial reference is experimental even where finite linear algebra
  is exact. Other normals return structured unsupported results.
