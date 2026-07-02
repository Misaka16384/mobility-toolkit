---
name: mt-boundary
description: "Use to compute boundary gauge operators using Algorithm 1 pipeline. Supports 2D and 3D translation-invariant stabilizer codes with periodic/open boundaries."
---

# mt-boundary — Boundary gauge operator generator (Algorithm 1)

Runs the **Algorithm 1** boundary-gauge pipeline for 2D/3D translation-invariant stabilizer codes.
Given the system dimensions, qudits per site, qudit dimension, patch boundaries, stabilizer generators, and qudit positions, it constructs the bulk stabilizers, builds the S-matrix, extracts the raw zero-syndrome operators within the boundary patch, and simplifies/prunes them to obtain the final exact boundary gauge operator generators.

## Input
JSON object containing:
- `dim`: Spatial dimension (2 or 3).
- `Lx`, `Ly`: System sizes in X and Y directions.
- `Lz`: System size in Z direction (required for 3D).
- `q`: Number of qudits per site.
- `d`: Qudit dimension (characteristic N).
- `wx`, `wy`: Boundary patch size in X and Y directions.
- `wz`: Boundary patch size in Z direction (required for 3D).
- `stabilizer_generators`: List of lists of generator terms.
  - 2D generator term: `[coeff, dx, dy, sublattice, pauli_type]`
  - 3D generator term: `[coeff, dx, dy, dz, sublattice, pauli_type]`
- `qudit_positions`: List of lists of floats representing qudit positions relative to site origin.
- `boundary`: `"bottom"` or `"top"`.

Example:
```json
{
  "dim": 2,
  "Lx": 5, "Ly": 5, "q": 2, "d": 2,
  "wx": 3, "wy": 3,
  "boundary": "bottom",
  "stabilizer_generators": [
    [[1, 0, 0, 0, 0], [1, 0, 0, 1, 0], [1, -1, 0, 0, 0], [1, 0, -1, 1, 0]],
    [[1, 0, 0, 0, 1], [1, 1, 0, 1, 1], [1, 0, 1, 0, 1], [1, 0, 0, 1, 1]]
  ],
  "qudit_positions": [[0.5, 0.0], [0.0, 0.5]]
}
```

## Output
JSON object containing:
- `status`: `"success"` or `"error"`.
- `bulk_stabilizers`: List of stabilizer dicts (with stringified keys in JSON).
- `boundary_ops`: List of lists representing final boundary gauge operator generators.
- `S_mat`: List of lists representing bulk stabilizer row span matrix.

## Examples
```bash
echo '{"dim": 2, "Lx": 5, "Ly": 5, "q": 2, "d": 2, "wx": 3, "wy": 3, "boundary": "bottom", "stabilizer_generators": [[[1, 0, 0, 0, 0], [1, 0, 0, 1, 0], [1, -1, 0, 0, 0], [1, 0, -1, 1, 0]], [[1, 0, 0, 0, 1], [1, 1, 0, 1, 1], [1, 0, 1, 0, 1], [1, 0, 0, 1, 1]]], "qudit_positions": [[0.5, 0.0], [0.0, 0.5]]}' \
  | python scripts/mt-boundary.py
```
