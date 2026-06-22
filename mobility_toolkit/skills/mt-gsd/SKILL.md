---
name: mt-gsd
description: "Layer 1->3 (model -> physics). Compute ground-state degeneracy (GSD) and anyon periodicities on an Lx x Ly torus for a 2D stabilizer code, via Groebner bases. Works for any qudit dimension N (prime or composite). Use to get the GSD / topological order of a 2D code directly from its stabilizers. Needs Macaulay2."
---

# mt-gsd — GSD + anyon periodicities on a torus (Layer 1→3)

Computes the **Layer 3** ground-state degeneracy and anyon periodicities of a **2D**
stabilizer code on an `Lx × Ly` torus, plus the fusion-rule group. Unlike the homology
path, this works for **any N** (the Z_N toric code gives GSD = N²).

## Conventions (GSD-specific — differ from the homology skills!)

- **2D only.** Variables are `x, y` and their Laurent inverses `t, u` (`x*t = 1`,
  `y*u = 1`). Write entries using `x, t, y, u` directly — **no `z`/`w`**.
- **No parentheses**; fully expand.
- `Lx`, `Ly` are positive integers (torus size). `qudit_dim` may be prime or composite.

## Input
```json
{
  "stabilizer_matrix": [["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]],
  "Lx": 3, "Ly": 3, "qudit_dim": 2
}
```

## Output
```json
{ "status": "success",
  "gsd": 4,
  "periodicities": {"l_x": 1, "l_y": 1},
  "fusion_rules": "Z_2^2" }
```

## Examples
```bash
# Z_2 toric code on a 3x3 torus: GSD = N^2 = 4
echo '{"stabilizer_matrix": [["1 - x","1 - y","0","0"],["0","0","1 - y","1 - x"]], "Lx": 3, "Ly": 3, "qudit_dim": 2}' \
  | python scripts/mt-gsd.py

# WCF bivariate-bicycle code (N=12) on a 2x2 torus: GSD = 144
echo '{"stabilizer_matrix": [["t - 5","u - 5","0","0"],["0","0","y - 5","5 - x"]], "Lx": 2, "Ly": 2, "qudit_dim": 12}' \
  | python scripts/mt-gsd.py
```

## Backend
Needs Macaulay2. If a run errors, check it with the **mt-doctor** skill first.
