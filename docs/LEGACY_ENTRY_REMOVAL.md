# Legacy entry removal record

Status: completed for the public runtime surface.

This is an owner-operated research toolkit. Runtime backward compatibility was
deliberately not retained after the native canonical operations and their
replacement tests existed.

## Current public rule

- The only computational request contract is the versioned
  `ServiceRequest`.
- Every registered computation is a native service operation.
- Python, CLI, MCP, and eight skills are thin transports over the same
  registry.
- There are no public per-algorithm convenience CLI commands.
- There are no runtime schema-version branches for old tuples, polynomial
  text, flat stabilizer matrices, or blocked/interleaved vectors.
- Removed coefficient-domain bypass switches have no runtime replacement.
  Backend capability is decided operation by operation and unsupported
  mathematics returns a structured result.
- A personal one-shot offline converter may be written in the future, but it
  must not be imported by the package runtime.

## Removed public surfaces

The migration deleted the old bulk translation/homology/classification,
mobility, GSD/fusion, model, doctor-skill, and boundary-gauge skill entry
points. The old Algorithm 1 dimension-specific tuple wrappers and term types
are no longer public APIs.

The retained eight-skill inventory is:

- `mt-finite-code`;
- `mt-boundary-algebra`;
- `mt-relative-homology`;
- `mt-halfspace`;
- `mt-gapped-boundary-2d`;
- `mt-gapped-boundary-3d`;
- `mt-defect`;
- `mt-cheshire`.

`doctor`, explicit personal-database actions, installation, and self-update
remain low-level administration commands. They are not alternate computation
contracts.

## Fixture-private compatibility evidence

Some legacy model data and Algorithm 1 implementation details remain
fixture-private because they provide useful differential evidence. They:

- are not exported from the package root;
- are not registered service operations;
- are not reachable through CLI, MCP, or skills;
- do not define the canonical result schema;
- may be deleted when their replacement literature benchmark is stronger.

This distinction preserves scientific regression evidence without preserving a
second public API.

## Replacement evidence

The native surface is guarded by tests that check:

- deleted package-root symbols and service registrations stay absent;
- the service catalog accepts only native adapter kinds;
- old runtime request fields are rejected;
- CLI and Python use the same canonical request/result envelope;
- MCP and skill shims forward into the same service executor;
- origin shifts and site relabelling preserve finite compiler invariants;
- cellular relative homology agrees with an independently constructed finite
  CSS symplectic quotient in known interval cases;
- bounded enumeration can stream and resume from sealed checkpoints;
- caller-owned SQLite persistence rejects foreign or tampered resume chains.

Algorithm-specific scientific promotion still requires the correctness,
literature, cross-formulation, and scale evidence listed in
`CAPABILITY_DASHBOARD.md`. Removal of a legacy wrapper is not itself evidence
that a broader physical classification has been solved.
