---
name: mt-cheshire
description: "Analyze, synthesize, finitely enumerate, and statically fuse Cheshire line defects. Use for certified finite 3+1D Z2 toric open/closed defects, tube-to-line radius checks, bounded supplied-species searches, endpoint/junction networks, or the explicitly experimental axial X-cube reference."
---

# mt-cheshire

Use this skill for Cheshire line/tube defects. It separates exact finite
stabilizer statements from phase, thermodynamic, and dynamical claims.

Run:

```bash
python scripts/mt-cheshire.py < input.json
```

## Operations

- `capabilities`: machine-readable production/experimental/unsupported scope.
- `static`: exact Phase-4 finite analysis of supplied toric open segments,
  closed loops, or several components.
- `synthesize-toric`: revalidate a supplied toric candidate at every strictly
  decreasing radius ending at zero, then compare declared finite invariants.
- `enumerate-toric`: exhaust exactly the supplied finite `candidate_sets` list.
  The result is not complete outside that recorded list.
- `fusion-toric`: compare explicit before/after finite Hamiltonians, logical
  counts, defect-local paired algebras, termination, and Hamiltonian deltas.
  Optional network data can encode endpoint, interface, and junction strata.
- `fracton-reference`: run the axial `(0,0,1)` X-cube finite candidate. Other
  normals return structured `unsupported` results.

The `static`, `synthesize-toric`, `enumerate-toric`, and `fusion-toric`
operations use a common three-dimensional geometry:

```json
{
  "operation": "synthesize-toric",
  "shape": [2, 1, 1],
  "periodic_axes": [],
  "candidate_id": "open-electric",
  "radii": [1, 0],
  "defects": [
    {
      "defect_id": "gamma",
      "topology": "open_segment",
      "cube_bases": [[0, 0, 0], [1, 0, 0]]
    }
  ]
}
```

For `enumerate-toric`, replace `defects` with:

```json
{
  "candidate_sets": [
    {
      "candidate_id": "candidate-a",
      "defects": [
        {
          "defect_id": "gamma",
          "topology": "open_segment",
          "cube_bases": [[0, 0, 0], [1, 0, 0]]
        }
      ]
    }
  ]
}
```

For static fusion supply `fusion_id`, `before_defects`, and `after_defects`.
Network nodes bind physical endpoint cube IDs; a junction node needs at least
three bindings. Network validation certifies incidence/strata only unless the
before/after Hamiltonians themselves contain a junction-local completion.

## Interpretation limits

- Finite stabilizer, commutation, logical, pairing, and syndrome certificates
  are exact in their recorded geometry.
- Tube shrinking certifies only the explicitly compared finite samples and
  invariant names. It is not a finite-depth or phase-equivalence proof.
- Static fusion does not construct a fusion circuit or a thermodynamic fusion
  rule.
- The X-cube workflow is an `experimental` candidate even though its finite
  syndrome and GF(2) calculations are exact.
- Do not identify every line defect with a Cheshire string, infer minimum
  sequential creation depth, or claim species outside the bounded input list.

The finite backend is `python-flint`; Macaulay2 is not used.
