# ADR 0005: static Cheshire defects and line/tube representations

Status: accepted

Date: 2026-07-22

## Decision

The first Cheshire workflow is a finite, static stabilizer construction for
the 3+1D Z2 toric code with plaquette qubits. It follows the operator placement
and open-line replacement in Tantivasadakarn--Chen, arXiv:2307.03180,
Eq. (6)--(8).

Every result keeps three Hamiltonians distinct:

1. `bulk`: cube-X charge checks and edge-Z flux checks;
2. `local_hamiltonian`: path cube checks replaced by single-plaquette Z
   condensate terms, with the length-dependent total-charge operator omitted;
3. `fixed_charge_sectors`: the local Hamiltonian plus each independent
   `Q_gamma` total-charge constraint.

The full Eq. (8) generator replacement includes `Q_gamma` and therefore does
not change finite GSD. Omitting that nonlocal operator exposes the Cheshire
charge sector. No field may identify that static sector counting with a
creation-circuit depth.

Two finite representations are compiled and compared:

- direct line-local rewrites;
- a deleted tube-volume cellular complex, with condensate internal
  plaquettes removed and tube-wall/endpoint-cap plaquettes retained.

Before comparison, the direct representation eliminates its explicitly
Z-pinned condensate plaquettes. The comparison certificate requires identical
Pauli modules and identical phase-aware generator sets for both the local and
fixed-sector codes. This is a finite stabilizer identity, not a tube-shrinking
or phase-equivalence theorem.

## Local and endpoint algebra

For a projective Pauli window `W`, the defect-local algebra is

```text
(centralizer(S) intersect W) / (S intersect W).
```

The induced pairing and its radical are retained. The radical is not
automatically quotiented, and the quotient order is not assumed to be a
square. Endpoint reports use separate finite support windows and are marked as
finite-window data rather than intrinsic thermodynamic endpoint types.

## Termination semantics

- Charge termination is reported with a positive Z-string/plaquette witness:
  a bulk charge check removed by the defect disappears from the syndrome.
- Magnetic nontermination is not inferred from a failed X probe. It requires
  an exact finite cellular certificate: all edge-flux checks remain, the
  plaquette-X syndrome map is the mod-2 cellular boundary, and a target open
  1-chain increases the augmented rank. `boundary^2=0` independently explains
  the obstruction.

## Exactness

Finite stabilizer, subgroup-intersection, quotient-pairing, and complete finite
syndrome-image results are `certified_exact`. A finite scaling sample is exact
pointwise; no thermodynamic inference is populated. Cheshire results use
`STANDARD` certificate level because construction/rank checks are stored but
not every GF(2) row operation is emitted as a replay trace.

## Rejected interpretations

- component-count-only GSD formulas on T3;
- treating a noncontractible loop as a contractible loop;
- calling pinned-condensate elimination a tubular representation;
- inferring magnetic nontermination from one failed representative operator;
- identifying local logical counting with a nondegenerate defect-local Pauli
  pair;
- dynamic deformation, fusion, or finite-depth equivalence conclusions.
