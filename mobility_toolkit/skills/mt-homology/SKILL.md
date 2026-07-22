---
name: mt-homology
description: "Use when you have stabilizer generator rows and need Ruba--Yang's Q^p = Ext_R^{p+1}(bar(P/L),R), its Krull dimension, annihilator, and validation metadata. Needs Macaulay2."
---

# mt-homology — validated stabilizer → Ruba--Yang charge module

Computes

```text
Q^p = Ext_R^(p+1)(bar(P/L), R)
```

over a Laurent ring, including the antipode in `bar(P/L)`. It returns the Ext
presentation, annihilator, Krull dimension, ambient-ring metadata, stabilizer
validation, and Proposition 25 consistency checks.

## Input convention

- Each input row is one stabilizer generator.
- Coordinates are `[X_1,...,X_q,Z_1,...,Z_q]` and therefore have even length.
- The default validates `sigma^dagger lambda sigma = 0`, where dagger includes
  Laurent inversion.
- Use `validate_stabilizer=false` only for an arbitrary algebraic presentation;
  that result is not certified as a stabilizer-code invariant.
- Set `spatial_dim` whenever the ambient lattice has axes absent from the matrix.
- `qudit_dim` must currently be prime. The paper supports composite and
  nonuniform qudits; the current Ext backend does not.
- `p_ext=0` computes local point charges. Higher `p_ext` has no theorem-proven
  direct mobility classification in the paper.

## Example

```json
{
  "stabilizer_matrix": [
    ["1-t", "1-u", "0", "0"],
    ["0", "0", "y-1", "1-x"]
  ],
  "qudit_dim": 2,
  "p_ext": 0,
  "spatial_dim": 2
}
```

Run:

```bash
python scripts/mt-homology.py < input.json
```

## Reading the result

- `krull_dimension=-1` means this charge module is zero, not that the entire
  code or phase is trivial.
- For `Q^0`, dimension zero is equivalent to every local point-charge class
  being mobile in all noncompact directions. Positive dimension only says that
  not all such classes are fully mobile.
- Krull dimension alone does not distinguish planons, lineons, or fractons and
  does not prove topological order.
- Pass `saturated=true` only if saturation is known independently; this enables
  the stronger Proposition 25 bound check.

The returned ideal is `Ann(Q^p)`, the annihilator of the whole charge module.
Passing it with the full `variables` list to **mt-mobility** computes only the
translations acting trivially on every class in that module. To study an
individual charge, first obtain that element's own `Ann(q)`; do not substitute
`Ann(Q^p)` and label the result as individual mobility.

If the backend fails, run **mt-doctor** first.
