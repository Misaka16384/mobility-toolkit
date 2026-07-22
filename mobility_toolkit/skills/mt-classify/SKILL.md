---
name: mt-classify
description: "Use when you have a charge-module Krull dimension and need the theorem-safe physical conclusion. For Q^0 this tests whether all local point charges are fully mobile; higher degrees are marked conjectural."
---

# mt-classify — theorem-scoped reading of Krull dimension

This pure-Python skill reports only what Ruba--Yang's mobility result proves.

- `p_ext=0`, Krull dimension `0`: every local point-charge class is fully
  mobile in all noncompact directions.
- `p_ext=0`, positive dimension: not every local point-charge class is fully
  mobile. The dimension alone does not determine planon/lineon/fracton labels.
- `p_ext>0`: direct mobility interpretation is conjectural/undetermined.
- Negative dimension: the selected charge module is zero; no phase-level
  conclusion follows.

Topological order is reported only as an assumption-qualified conclusion when
the caller explicitly supplies all three assumptions below.

```json
{
  "krull_dimension": 0,
  "spatial_dim": 2,
  "p_ext": 0,
  "assumptions": {
    "lagrangian": true,
    "saturated": true,
    "no_ssb": true
  }
}
```

Run:

```bash
python scripts/mt-classify.py < input.json
```

The deprecated `generic_mobility_dimension` and ambiguous phase flags are
`null` whenever the theorem does not determine them. Use **mt-mobility** on an
individual binomial annihilator to compute a certified translation lattice.
