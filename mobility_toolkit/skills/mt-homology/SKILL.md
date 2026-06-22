---
name: mt-homology
description: "Layer 1->2 (model -> algebra), with the Layer 3 reading attached. Compute the Ext^{p_ext+1} charge module, its Krull dimension, and the annihilator generators for a stabilizer code, then label the physical mobility class. Use to decide whether a code is topological or fracton straight from its stabilizers. Needs Macaulay2."
---

# mt-homology — Ext module + Krull dimension + class (Layer 1→2, with L3 label)

Computes the **Layer 2** algebraic invariant — the `Ext^{p_ext+1}(coker M, R)` charge
module, its **Krull dimension**, and the **annihilator generators** — and attaches the
**Layer 3** mobility class (`classify_mobility`). This is the one-shot "stabilizers →
mobility classification."

> **Criterion** (validated, see `docs/VALIDATION.md`): Krull dimension **0 ⟺ mobile**
> (topological order); **> 0 ⟺ restricted** (fracton order).

## Conventions (read first — these cause most errors)

- **`qudit_dim` must be prime** (ring is `ZZ/N`; Ext needs a field). For composite N the
  homology path is unavailable — use **mt-gsd** instead (see VALIDATION Finding 2).
- **No parentheses** — fully expand: `y + z + x*y + x*z`, never `(1+x)*(y+z)`.
- Variables: spatial `x, y, z`; Laurent inverses `t, u, w` (`x*t = y*u = z*w = 1`).
- **`p_ext`**: use `0` for point (0-dimensional) charges; higher `p` for higher-form charges.

## Input
```json
{
  "stabilizer_matrix": [["1 - x", "1 - y", "1 - z", "0"], ["0", "1 - y", "1 - z", "1 - x"]],
  "qudit_dim": 2,
  "p_ext": 0,
  "spatial_dim": 3         // optional; inferred from the variables present if omitted
}
```

## Output
```json
{ "status": "success",
  "krull_dimension": 2,
  "ext_modules": ["cokernel | ... |"],
  "annihilator_generators": ["...", "..."],
  "order": "fracton", "mobility_class": "lineon",
  "is_topological": false, "is_fracton": true,
  "generic_mobility_dimension": 1, "spatial_dim": 3, "note": "..." }
```

## Examples
```bash
# Toric code: Krull 0 -> fully-mobile anyons (topological)
echo '{"stabilizer_matrix": [["1 - x","1 - y","0","0"],["0","0","1 - y","1 - x"]], "qudit_dim": 2, "p_ext": 0}' \
  | python scripts/mt-homology.py

# X-Cube: Krull 2 -> restricted (fracton order)
echo '{"stabilizer_matrix": [["1 - x","1 - y","1 - z","0"],["0","1 - y","1 - z","1 - x"]], "qudit_dim": 2, "p_ext": 0}' \
  | python scripts/mt-homology.py
```

## Next
- Pass `krull_dimension` to **mt-classify** to re-interpret under a different `spatial_dim`.
- Pass `annihilator_generators` to **mt-mobility** for the *exact* free-direction count
  (needed for Type-II fractons, where Krull overestimates mobility).

## Backend
Needs Macaulay2. If a run errors, check it with the **mt-doctor** skill first.
