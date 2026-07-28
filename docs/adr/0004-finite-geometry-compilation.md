# ADR 0004: finite geometry, quotient, and compilation semantics

Status: accepted

Date: 2026-07-22

## Decision

Finite geometry is represented independently from Pauli operators and from
display coordinates.

1. A `FiniteCellComplex` owns oriented integer boundary maps and validates
   `boundary * boundary = 0` at construction.
2. A `FiniteRegion` owns translation coordinates, source species, physical
   sites, explicit site embeddings, axis identifications, aliases, and
   strata. Floating-point display positions live in a separate object and do
   not enter the mathematical hash.
3. A resolved site consists of a physical site ID, a phase-aware local Pauli
   frame, and winding/seam provenance. Local frame maps contain the central
   phase lift, not only a projective symplectic matrix.
4. Periodic template offsets contain both free and torsion translation
   components.
5. Site gluing and branch-cut frame rewrites are different operations. Site
   gluing reduces the Hilbert-space dimension; a frame rewrite changes only a
   selected term instance and leaves physical sites unchanged.
6. Compilation requires explicit `CrossingPolicy` and `SupportAliasPolicy`.
   There is no default drop/truncate behavior.
7. A generator instance is identified by canonical template hash plus raw
   anchor. Deduplication of equal final operators merges provenance sources
   instead of discarding them.
8. Local modifications run in a fixed order: add physical systems, instantiate
   bulk terms, remove selected source instances, apply term-frame rewrites,
   add explicit local generators, deduplicate, then run full phase/stabilizer
   validation.
9. Oriented cell quotients carry signed gluing relations. The quotient is
   accepted only when every identified cell has the same induced boundary.

## Explicit policies

Crossing policies:

- `error_on_crossing`;
- `omit_whole_instance`;
- `truncate_missing_terms`;
- `require_local_rewrite`.

Support-alias policies:

- `reject_support_alias`;
- `normal_form_pushforward`.

Normal-form pushforward multiplies mapped terms in canonical template order,
so collisions on one physical site retain the Weyl cocycle and central phase.

## Consequences

- Small periodic quotients may turn distinct cover terms into the same local
  operator. This is visible in the certificate and never treated as ordinary
  set deduplication.
- Truncated generators may form a noncommuting gauge algebra. `FiniteCode`
  therefore always contains the full stabilizer validation result and exposes
  a subsystem view when validation fails.
- Twisted axis holonomies are rejected if phase-aware frame compositions are
  path dependent. Non-Abelian spatial gluings such as a Klein bottle are
  handled at the oriented cell-complex level rather than pretending that all
  deck transformations commute.
- Boundary-term synthesis is not part of Phase 3. The compiler faithfully
  applies user-supplied rewrites; later phases search for them.

## Rejected alternatives

- Fixed last-axis open boundaries;
- hidden crossing-term deletion;
- float-coordinate equality as site identity;
- a projective-only Clifford matrix without phase lift;
- treating a branch cut as physical-site identification;
- using the legacy boundary generator list as a topology or physics oracle.
