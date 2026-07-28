---
name: mt-relative-homology
description: "Use for exact relative cellular homology on explicit finite pairs, such as CSS codes whose logical chains may end on a selected boundary subcomplex. Supports arbitrary chain dimension and prime or composite Z/N coefficients through the unified topology.relative_homology service."
---

# mt-relative-homology

Send a canonical service request through the bundled adapter:

```bash
python scripts/mt-relative-homology.py < request.json
```

Use the intended service operation:

```json
{
  "operation": "topology.relative_homology",
  "input_data": {
    "ambient": {
      "cell_ids_by_dimension": [["v0", "v1"], ["e01"]],
      "boundary_maps": [
        {"nrows": 0, "ncols": 2, "entries": []},
        {"nrows": 2, "ncols": 1, "entries": [[0, 0, -1], [1, 0, 1]]}
      ],
      "assumptions": ["oriented interval"]
    },
    "subcomplex_cell_ids_by_dimension": [["v0", "v1"], []],
    "degree": 1,
    "coefficient_modulus": 4
  },
  "requested_certificate_level": "full",
  "assumptions": ["explicit finite cellular pair"]
}
```

Each sparse boundary entry is `[row, column, coefficient]`. The service checks
that the selected cells form a boundary-closed subcomplex, constructs the
canonical quotient \(C_*(X)/C_*(A)\), and returns exact finite-group invariants
with replayable relative-chain and homology certificates.

Preserve the full `mobility_toolkit.service_execution.v1` envelope. Relative
homology here concerns an explicit finite pair \(A\subseteq X\); it is not
`Ext_R(M,R/I)` and does not represent a one-sided Laurent half-space.
