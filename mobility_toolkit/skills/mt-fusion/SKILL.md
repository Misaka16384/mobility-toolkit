---
name: mt-fusion
description: "Compute point excitation mobility fusion rules and interference. Use when you need to compute SSET fusion rules (L2->L3 or SSET) or check dimension drops under shifts (L1->L3). Needs Macaulay2."
---

# mt-fusion — mobility fusion and interference (Layer 1/2→3)

This skill handles the computation of excitation mobility fusion rules and spatial interference properties. It supports three distinct workflows:

## Workflow 1: Fusion Interference under Shifts (L1→3)
Checks whether relative translation **shift** vectors cause the annihilator
dimension of `Ext^1_R(bar(P/L),R)` to drop. This is an algebraic diagnostic; it
is not by itself a theorem-level planon/lineon/fracton classification.

### Input
```json
{
  "stabilizer_matrix": [["1 - t", "1 - u", "0", "0"], ["0", "0", "y - 1", "1 - x"]],
  "qudit_dim": 2,
  "shifts": [[1, -1, 0]]
}
```

This is an independently sourced dimension-drop/fusion helper. It is not the
Cech-cocycle braiding construction in Ruba--Yang.
### Examples
```bash
echo '{"stabilizer_matrix": [["1 - t","1 - u","0","0"],["0","0","y - 1","1 - x"]], "qudit_dim": 2, "shifts": [[1,-1]]}' \
  | python scripts/mt-fusion.py
```

---

## Workflow 2: Annihilator Fusion Rules (L2→3)
Directly computes SSET-style mobility fusion rules and channels from the generators of the Point Excitation annihilator ideal. If the ideal is principal, it extracts and normalizes the generator, and computes the fusion channels.

### Input
```json
{
  "generators": ["x1 + x2 + 1"],
  "qudit_dim": 2,
  "variables": ["x1", "x2"]
}
```
### Examples
```bash
echo '{"generators": ["x1 + x2 + 1"], "qudit_dim": 2, "variables": ["x1", "x2"]}' \
  | python scripts/mt-fusion.py
```

---

## Workflow 3: SSET Polynomial Fusion Algebra
Given a skeleton/decoration polynomial `poly_f` and an excitation class or polynomial `poly_g`, solves the SSET characteristic polynomial, LFSR periodicities, and multi-channel fusion rules.

### Input
```json
{
  "poly_f": "1 + y",
  "poly_g": "beta_{y, 1} * beta_{y, 1}"
}
```
### Examples
```bash
echo '{"poly_f": "1 + y", "poly_g": "beta_{y, 1} * beta_{y, 1}"}' \
  | python scripts/mt-fusion.py
```
