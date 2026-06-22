---
name: mt-fusion
description: "Layer 1->3 (model -> physics, via the Layer 2 annihilator). Test whether relative translation shift vectors cause a dimension drop in the point-excitation annihilator variety (fusion interference). A drop means the composite excitation at that shift is more constrained. Use to probe how fusing/shifting excitations changes their mobility. Needs Macaulay2."
---

# mt-fusion — fusion interference under shifts (Layer 1→3)

Builds the **Layer 2** point-excitation annihilator ideal (`Ext^1`) and checks whether each
relative translation **shift** causes its dimension to drop — a **Layer 3** signature that
the composite excitation at that shift is more constrained (rigid-to-flexible fusion).

## Conventions

- **`qudit_dim` must be prime.**
- **No parentheses**; fully expand. Spatial `x, y, z`; inverses `t, u, w`.
- `shifts` is a list of integer vectors `[dx, dy, dz]` (relative translations); negative
  entries use the inverse direction.

## Input
```json
{
  "stabilizer_matrix": [["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]],
  "qudit_dim": 2,
  "shifts": [[1, -1, 0]]
}
```

## Output
```json
{ "status": "success", "annihilator_dimension": 0, "dimension_drop": false }
```

## Examples
```bash
# Toric code, shift (1,-1): no dimension drop (mobile anyons)
echo '{"stabilizer_matrix": [["1 - x","1 - y","0","0"],["0","0","1 - y","1 - x"]], "qudit_dim": 2, "shifts": [[1,-1,0]]}' \
  | python scripts/mt-fusion.py

# 2D lineon (mobile along y): a shift along the constrained x-axis drops the dimension
echo '{"stabilizer_matrix": [["1 - x","0"]], "qudit_dim": 2, "shifts": [[1,0,0]]}' \
  | python scripts/mt-fusion.py
```

## Backend
Needs Macaulay2. If a run errors, check it with the **mt-doctor** skill first.
