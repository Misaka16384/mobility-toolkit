# ADR 0001: Pauli and phase conventions

Status: accepted for schema v1

Date: 2026-07-22

## Context

The Laurent path currently exposes blocked vectors
`[X_1,...,X_q,Z_1,...,Z_q]`, while the finite boundary path uses interleaved
vectors `[X_0,Z_0,X_1,Z_1,...]`. Neither representation records the central
phase of an operator. That is not a safe foundation for composite or
nonuniform local dimensions, stabilizer-lift validation, defects, or boundary
Hamiltonian completion.

## Decision

### Projective Pauli space

The semantic local system at site `i` is a finite abelian group `A_i`. Schema
v1 implements cyclic systems `A_i = Z/d_i`; the surrounding schema uses
invariant-factor lists so a later general finite abelian implementation does
not require a serialization break.

The projective Pauli group is

```text
P = direct_sum_i (A_i + dual(A_i)).
```

For cyclic local systems an element is a sparse map

```text
site_id -> (x_exponent mod d_i, z_exponent mod d_i).
```

Public APIs do not expose blocked or interleaved flat-vector layouts. Such
layouts are backend adapters with explicit names.

### Alternating pairing

Let `L = lcm(2*d_i)` and let `zeta = exp(2*pi*i/L)`. In integer coordinates the
pairing exponent is

```text
omega(v,w) = sum_i (L/d_i) * (z_i*x'_i - x_i*z'_i) mod L.
```

Equivalently the pairing takes values in `Q/Z`. The sign agrees with the
existing Laurent convention

```text
lambda = [[0, -I], [I, 0]].
```

Changing this sign is a schema/theorem convention change and requires a new
ADR and invariant version.

### Default phase convention

Schema v1 uses normal-ordered operators

```text
zeta^c product_i X_i^x_i Z_i^z_i,
```

with central phase exponent `c mod L`. Multiplication is

```text
(c,x,z) * (c',x',z') =
  (c + c' + sum_i (L/d_i)*z_i*x'_i, x+x', z+z').
```

This convention is closed for odd, even, composite, and mixed `d_i`, and is
sufficient to validate a commuting stabilizer subgroup and its common `+1`
eigenspace. The factor of two is intentional: even-dimensional Pauli lifts can
require phases of order `2*d_i`. For example, raw `XZ` on a four-level qudit
has `(XZ)^4 = -I`, while an eighth-root phase produces a valid order-four
lift. A schema that stores phases only modulo `lcm(d_i)` cannot represent that
lift.

The default convention identifier is `"xz_normal_2lcm"`. A symmetric Weyl
convention may use the same central phase group with a different cocycle; it
must be represented by a different explicit identifier and is never silently
mixed with the default.

### Stabilizer and subsystem data

`StabilizerCodeSpec` stores phase-aware generators. Validation proves:

1. projective isotropy;
2. closure under the declared local orders;
3. no nontrivial central scalar belongs to the generated stabilizer group;
4. the declared `+1` eigenspace is phase-consistent.

`SubsystemCodeSpec` stores a possibly noncommuting gauge subgroup. Its
stabilizer center is derived or supplied with a certificate. Boundary gauge
operators are represented using this subsystem semantics rather than being
mislabelled as a commuting Hamiltonian.

### Laurent involution

For the translation group `Lambda`, the group-ring involution is

```text
bar(g) = g^-1,
```

and the adjoint is transpose followed by this involution. The corrected
Ruba--Yang invariant remains

```text
Q^p = Ext_R^(p+1)(bar(P/L), R).
```

## Consequences

- Composite and nonuniform local dimensions are semantic first-class data.
- Phase-free legacy generators must pass through an adapter that inserts an
  explicit zero phase and records the assumption.
- Backend vectors always state their layout; no bare `numpy.ndarray` crosses a
  public API boundary.
- A future symmetric-Weyl/Clifford backend can coexist without changing the
  meaning of schema-v1 operators.

## Non-goals

- This ADR does not implement arbitrary finite abelian `A_i` in Phase 1.
- It does not classify non-Pauli or magic boundaries.
- It does not assert that every projectively isotropic subgroup has a valid
  phase lift; the validator exists precisely to detect failures.
