---
name: mt-classify
description: "Layer 2->3 (algebra -> physics). Map a Krull dimension to a physical mobility class (fully-mobile / planon / lineon / fracton; topological vs fracton). Use to interpret a Krull dimension you already have, or to re-read one under a different spatial dimension, without re-running Macaulay2. Pure, no backend."
---

# mt-classify — Krull dimension → mobility class (Layer 2→3)

The pure interpretation step. Given a **Layer 2** Krull dimension, return the **Layer 3**
physics. Use it to re-read a dimension you already computed (e.g. from **mt-homology**)
without touching Macaulay2, or to test how the class changes with `spatial_dim`.

> **Criterion**: Krull **0 ⟺ mobile** (topological); **> 0 ⟺ restricted** (fracton).
> The *generic* free-direction count is `spatial_dim - krull_dim` (an upper bound; Type-II
> fractons are lower — use **mt-mobility** for the exact value). A negative Krull dimension
> means the charge module is zero (no excitation of this type).

## Input
```json
{ "krull_dimension": 2, "spatial_dim": 3 }
```
`spatial_dim` is optional (default 3).

## Output
```json
{ "status": "success",
  "krull_dimension": 2, "spatial_dim": 3,
  "order": "fracton", "mobility_class": "lineon",
  "is_topological": false, "is_fracton": true,
  "generic_mobility_dimension": 1, "note": "..." }
```

## Examples
```bash
echo '{"krull_dimension": 0, "spatial_dim": 2}' | python scripts/mt-classify.py   # fully-mobile anyon
echo '{"krull_dimension": 2, "spatial_dim": 3}' | python scripts/mt-classify.py   # lineon (generic)
echo '{"krull_dimension": -1}'                  | python scripts/mt-classify.py   # trivial (zero module)
```
