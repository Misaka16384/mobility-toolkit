# ADR 0002: Canonical IR and map directions

Status: accepted for schema v1

Date: 2026-07-22

## Context

The repository currently has independent string, tuple, dictionary, blocked
matrix, and interleaved matrix representations. CLI, MCP, and skills duplicate
their request schemas. Canonical hashing and cache correctness cannot be built
on backend pretty-printing.

## Decision

### Maps and matrices

All algebraic elements are column vectors. A matrix `A` denotes a map

```text
A: source -> target
```

and therefore has shape `(target_generator_count, source_generator_count)`.
Generators of a submodule are columns of its generator map.

The canonical sparse integer matrix representation is sorted COO:

```text
SparseIntMatrix
  nrows
  ncols
  entries: sorted unique (row, column, integer)
```

Duplicate entries are combined and zero entries are removed before hashing.

### Presented modules and maps

```text
PresentedModule
  ambient_rank: m
  relations: R

ModuleMap
  source
  target
  matrix
  relation_witness

Submodule
  ambient
  generator_map
```

`PresentedModule(m,R)` means `Z^m / image(R)`. A `ModuleMap` is valid only when
its relation witness proves that source relations map into target relations.

### Operator templates

Translation-invariant generators use a dimension-independent sparse template:

```text
OperatorTerm
  offset: tuple[int, ...]
  species_id
  x_exponent
  z_exponent

OperatorTemplate
  phase
  terms
```

An individual term may carry both X and Z exponents. `pauli_type=0/1` and the
separate 2D/3D tuple types are legacy-only concepts.

### Laurent polynomials

Canonical Laurent polynomials are sparse terms, not free text:

```text
LaurentTerm
  coefficient
  free_exponents: tuple[int, ...]
  torsion_exponents: tuple[int, ...]

LaurentPolynomial
  coefficient_domain
  ordered combined terms
```

Parsing legacy strings is an input concern. Macaulay2 source generation is a
backend concern. Neither string is part of the mathematical identity.

### Periodic and finite IR

The project uses two concrete IRs sharing the same Pauli semantics:

```text
PeriodicCode
  translation_group
  species
  operator_templates
  equivariant_pauli_presentation
  stabilizer_map

FiniteCode
  finite_pauli_module
  stabilizer_or_gauge_presentation
  geometry
  provenance
```

`PeriodicCode -> FiniteCode` is an explicit geometry compilation operation.
The two representations are not merged into a generic matrix mega-class.

### Canonical serialization and hashing

Every public object carries an independent `schema_version`. Canonical JSON:

1. uses UTF-8;
2. sorts object keys;
3. uses canonical ordering for sets, sites, terms, and matrix entries;
4. emits no insignificant whitespace;
5. rejects floating-point values in mathematical identity fields;
6. excludes display metadata from the mathematical hash.

The canonical input hash is SHA-256 over

```text
schema identifier || canonical mathematical JSON.
```

Coordinates used only for visualization do not affect the hash. Discrete
incidence, identifications, orientations, and gluing maps do.

### Service boundary

Core algebra and geometry functions are pure. Registry, cache, logs,
discovery files, CLI formatting, MCP transport, and skill orchestration live in
the service layer and are explicit options.

CLI, MCP, and skills consume the same versioned request/result dataclasses or
generated JSON schema. They do not reimplement validation or dispatch.

## Consequences

- Existing blocked/interleaved arrays require named backend adapters.
- Existing polynomial strings and boundary tuples are removed when their
  replacement tests exist; there is no runtime compatibility promise.
- Cache keys can include exact mathematical identity rather than generated M2
  strings or unstable dictionary order.
- Geometry and visualization metadata can evolve without invalidating algebra
  caches unnecessarily.

## Non-goals

- Schema v1 does not choose a database serialization format.
- This ADR does not require dense or sparse storage inside a backend.
- It does not define physical equivalence of two boundary conditions; that is
  an explicit enumeration option.
