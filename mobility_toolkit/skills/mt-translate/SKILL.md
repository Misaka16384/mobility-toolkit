---
name: mt-translate
description: "Layer 1->2 (model -> algebra). Parse a Pauli stabilizer matrix into its Laurent-ring algebra: variables, ring definition, and Macaulay2 matrix definition. Use first, to set up or inspect the algebraic form of a stabilizer model. No Macaulay2 backend needed."
---

# mt-translate — stabilizer model → algebra (Layer 1→2)

Turns a **Layer 1** Pauli stabilizer matrix into the **Layer 2** algebraic objects
(ring, variables, matrix) the homology/mobility skills consume. Pure Python — no
Macaulay2 needed. This is the usual first step, or a way to inspect how a model maps
into the Laurent ring.

## Conventions (read first — these cause most errors)

- **`qudit_dim` must be prime** (ring is `ZZ/N`).
- **No parentheses** — fully expand polynomials: `y + z + x*y + x*z`, never `(1+x)*(y+z)`.
- Variables: spatial `x, y, z`; their Laurent inverses are `t, u, w` (`x*t = y*u = z*w = 1`).
  Write inverses as `x^-1` / `x**-1`; they are rewritten to `t`/`u`/`w`.
- A stabilizer matrix is a list of equal-length rows (lists of polynomial strings).

## Input
```json
{
  "stabilizer_matrix": [["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]],
  "qudit_dim": 2
}
```

## Output
```json
{ "status": "success",
  "variables": ["x", "t", "y", "u"],
  "ring_definition": "R = ZZ/2[...]",
  "matrix_definition": "{{...}}" }
```

## Example
```bash
echo '{"stabilizer_matrix": [["1 - x","1 - y","0","0"],["0","0","1 - y","1 - x"]], "qudit_dim": 2}' \
  | python scripts/mt-translate.py
```

## Next
Feed the same matrix to **mt-homology** (Ext + Krull dimension) or **mt-fusion**.
