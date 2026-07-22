# ADR 0003: Exactness, certificates, and theorem scope

Status: accepted for schema v1

Date: 2026-07-22

## Context

The legacy boundary pipeline calls finite-patch representatives "final exact"
without recording the patch domain or a completeness certificate. Research
algorithms for half-spaces, 3D/fracton boundaries, and Cheshire defects require
stronger separation between an exact finite calculation and a thermodynamic
classification claim.

## Decision

Every public computation returns:

```text
ComputationResult[T]
  schema_version
  canonical_input_hash
  value
  exactness
  assumptions
  theorem_scope
  certificate
  verification
  backend_provenance
  resource_usage
  diagnostics
  warnings
```

### Exactness levels

`certified_exact`
: The result is exact for its stated mathematical domain and carries enough
  evidence for the independent verifier to check the defining identities and
  completeness criterion.

`bounded_exact`
: The result is exhaustive only inside an explicit finite region, support
  radius, period, depth, ancilla budget, or other finite search domain. That
  domain is part of the value and hash.

`stabilized_empirically`
: Results agree across a documented sequence of increasing finite domains, but
  there is no proof that later domains cannot change the answer.

`experimental`
: The operation or coefficient domain is research-grade, lacks the required
  cross-checks, or relies on assumptions that have not been promoted to a
  production theorem contract.

`unsupported`
: The requested backend/domain/operation is not implemented. Exact requests
  never silently fall back to heuristics.

### Required provenance

Backend provenance includes:

- backend and algorithm name;
- software version/fingerprint;
- coefficient and translation domains;
- input dimensions/density;
- time and memory/resource limits;
- whether transforms/witnesses were requested;
- theorem/invariant version.

### Certificate families

The standard certificate interface supports:

- normal form: diagonal/Hermite/Howell result and defining identities;
- module map: relation witness;
- kernel: soundness plus a completeness invariant/presentation;
- membership: coefficients and relation witness;
- quotient/intersection: inclusion and presentation witnesses;
- pairing: relation compatibility, alternation, radical/nondegeneracy claim;
- stabilizer: isotropy, phase consistency, group order, no-scalar check;
- logical module: representatives, quotient presentation, pairing and GSD
  order identities;
- enumeration: canonical finite search domain, exhaustive traversal evidence,
  and orbit-reduction witnesses;
- Laurent/Ext: ring, term order, presentation/resolution provenance, differential
  checks, and backend trust tier.

Certificates have two storage levels:

`standard`
: Default. Stores enough compact witnesses and invariant identities to detect
  backend corruption or a mismatched result.

`full`
: Stores potentially large transforms, representative maps, and enumeration
  traversal details. Requested only when a downstream operation needs them.

### Physics claims

A physics label is emitted only when its assumptions and theorem scope are
explicit. In particular:

- finite-patch completeness is not half-space completeness;
- maximal isotropy in a finite boundary algebra is not automatically a proof
  of a thermodynamic gapped boundary;
- a static Cheshire logical degeneracy does not prove a circuit-depth claim;
- positive charge-module Krull dimension is not mapped directly to a
  planon/lineon/fracton label;
- a 3D enumeration result always names E1, E2, or E3 and the selected physical
  equivalence relation.

## Consequences

- Legacy output can remain a regression fixture but cannot be re-exported as a
  certified new result.
- Enumeration APIs must be resumable and store their finite domain.
- Backend timeouts and iteration limits are failures or incomplete results, not
  successful exact answers.
- Literature benchmarks assert physical invariants, not merely process exit or
  generator counts.
