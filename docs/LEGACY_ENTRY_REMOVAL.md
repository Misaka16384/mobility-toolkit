# Legacy entry removal plan

The project is an owner-operated research toolkit. There is no runtime backward
compatibility requirement. Old public entry points are deleted once the new
core operation and its correctness tests exist. Fixtures may survive longer as
differential evidence.

## Immediate policy

- Do not add deprecation wrappers.
- Do not add schema-version branches for old boundary tuples or polynomial
  strings.
- Do not preserve old output shapes in the new service layer.
- A one-shot offline converter is allowed if it helps migrate stored personal
  models, but it is not imported by the package at runtime.

## Bulk wrappers to remove during Phase 1/5B

| Legacy entry | Replacement condition |
|---|---|
| `translate_to_algebra` | `PeriodicCode` + canonical Laurent parser/service exists |
| `compute_homology_and_mobility` | structured homology service and theorem-scoped result exist |
| `compute_true_mobility_dimension` | all internal callers use `compute_translation_lattice` or its new service |
| homology/translation `prime_bypass` | backend `supports()` and structured `unsupported` exist |
| M2 pretty-print parsing contract | structured backend protocol and version probe exist |

The corrected current algorithms remain available internally until their new
literature tests pass through the canonical IR.

## Boundary entries to remove during Phase 3/5A

Delete as a group after the finite compiler and exact boundary-algebra service
replace them:

- CLI `boundary-gauge` parser and dispatch;
- MCP `compute_boundary_gauge`;
- `mt-boundary` skill and installer registration;
- `run_algorithm_1_boundary_ops_2d` and `_3d` public wrappers;
- 2D/3D `GeneratorTerm` public types;
- tuple result `(bulk_stabilizers, boundary_ops, S_mat)`;
- legacy example runners as user-facing commands.

Do not delete legacy model fixtures or the old internal pipeline before the new
compiler/solver has differential tests for the same inputs.

## Representation cleanup

The following concepts must disappear from public/core APIs:

- bare blocked/interleaved NumPy vectors;
- `pauli_type = 0/1` terms;
- dimension-specific `_2d`/`_3d` core functions;
- required floating-point `qudit_positions` for algebra;
- hidden `bottom/top` geometry semantics;
- hidden drop-crossing-stabilizer policy;
- claims of "final exact" without an exactness domain and certificate.

## CLI/MCP/skill consolidation

Once the versioned service layer exists:

1. Python services own validation and dispatch.
2. JSON schema is generated or shared from the service request/result types.
3. CLI, MCP, and skills are thin transports.
4. Removal of an old service removes all three old wrappers in the same commit.

## Evidence required before deletion

For each removed algorithmic entry, the replacement commit must identify:

- the new operation and schema;
- algebraic exhaustive tests;
- relevant literature benchmark;
- differential result against any still-useful legacy fixture;
- explicit behavior for unsupported inputs;
- exactness and provenance fields.
