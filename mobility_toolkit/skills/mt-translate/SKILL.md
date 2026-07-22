---
name: mt-translate
description: "Use when you need to parse generator rows into a Laurent-ring stabilizer map, construct its antipode presentation, and validate sigma^dagger lambda sigma=0. No Macaulay2 needed."
---

# mt-translate — stabilizer generators → Laurent algebra

Each input row is one generator in coordinates
`[X_1,...,X_q,Z_1,...,Z_q]`. The translator transposes those rows into
`sigma:F->P`, constructs the antipode presentation used for `bar(P/L)`, and by
default verifies even Pauli rank and `sigma^dagger lambda sigma=0`.

```json
{
  "stabilizer_matrix": [
    ["1-t", "1-u", "0", "0"],
    ["0", "0", "y-1", "1-x"]
  ],
  "qudit_dim": 2,
  "spatial_dim": 2
}
```

The output includes `ring_definition`, `matrix_definition`,
`antipode_matrix_definition`, `variable_pairs`, `matrix_convention`, and
`stabilizer_validation`.

Use `validate_stabilizer=false` only when the input is intentionally an
arbitrary module presentation. Set `spatial_dim` explicitly when the ambient
lattice contains unused axes. Composite rings may be translated with
`prime_bypass=true`, but the current homology backend remains prime-field only.

Variables may use legacy pairs `x/t`, `y/u`, `z/w` or unified pairs
`x1/t1`, `x2/t2`, ...; each pair represents one Laurent axis.

```bash
python scripts/mt-translate.py < input.json
```
