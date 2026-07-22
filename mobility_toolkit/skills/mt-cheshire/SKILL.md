---
name: mt-cheshire
description: "Compute certified finite static data for user-specified Cheshire open segments, closed loops, and multiple line components in the 3+1D Z2 plaquette-qubit toric code. Use for finite GSD changes, total-charge sectors, endpoint and defect-local Pauli algebras, charge/flux termination checks, tube-versus-line representation certificates, or finite length/radius comparisons."
---

# mt-cheshire

Run the bundled script on a 3D cubical region. It implements the static
stabilizer replacement of Tantivasadakarn--Chen, arXiv:2307.03180, Eq. (6)--(8),
and returns exact finite-system certificates.

## Workflow

1. Choose `shape` and any `periodic_axes`.
2. Give each defect an ordered nearest-neighbor `cube_bases` path and select
   `open_segment` or `closed_loop`.
3. Run `python scripts/mt-cheshire.py` with JSON on stdin.
4. Read `bulk`, `local_hamiltonian`, and `fixed_charge_sectors` separately.
   `local_hamiltonian` retains every bulk term away from the line; only path
   charge checks are replaced. `fixed_charge_sectors` uses the stabilizer
   `+1` eigenvalue convention for the added `Q_gamma` generators.
5. Treat `tube_radius_lattice_steps` only as the finite support window used for
   defect-local algebra. The separately certified deleted-tube representation
   removes the specified core volume while retaining wall/cap plaquettes.

```json
{
  "shape": [3, 1, 1],
  "periodic_axes": [],
  "tube_radius_lattice_steps": 0,
  "defects": [
    {
      "defect_id": "gamma",
      "topology": "open_segment",
      "cube_bases": [[0, 0, 0], [1, 0, 0]]
    }
  ]
}
```

```bash
python scripts/mt-cheshire.py < input.json
```

Set `include_full_result` to `true` only when the complete canonical subgroup,
pairing, and lattice certificates are needed; the payload can be large.

## Interpretation limits

- Each finite stabilizer and specified window result is exact.
- A sequence of exact finite samples is not a thermodynamic theorem.
- Do not infer creation-circuit depth, finite-depth phase equivalence, dynamic
  deformation/fusion, or completeness of Cheshire species.
- `charge_termination` is a positive operator witness.
- `magnetic_termination` is backed by a finite cellular syndrome no-solution
  certificate, not merely a failed representative probe.

The script needs the `python-flint` finite backend; it does not use Macaulay2.
