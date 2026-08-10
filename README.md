# mobility_toolkit

`mobility_toolkit` is a boundary-aware stabilizer-code research toolkit. Its
public computational surface is one versioned, native service registry shared
by Python, CLI, MCP, and eight use-case skills. The implemented operation
families cover:

- finite generalized-Pauli codes over prime, composite, and mixed local
  dimensions;
- explicit finite cuts, boundary algebras, and bounded E1/E2 searches;
- exact cellular relative homology for finite pairs;
- canonical periodic Laurent presentations and theorem-scoped charge-module
  operations;
- oriented rational half-spaces and source-locked boundary benchmarks;
- bounded 2D and 3D boundary-candidate enumeration;
- stratified defects, endpoints, tubes, and junction incidence;
- complete 2D Z2 toric Cheshire/descendant classification and ordered fusion,
  finite lattice/circuit witnesses, finite pointed/Abelian interface
  classification, retained 3+1D static references, and evidence-graded X-cube
  support candidates.

Every result reports its operation scope, exactness, assumptions, certificate,
provenance, and warnings. A finite or bounded-exact computation is not a
thermodynamic classification. Unsupported mathematics is returned as a
structured result instead of being approximated silently.

See [the theorem and research scope](docs/THEORY_SCOPE.md) and the
[capability dashboard](docs/CAPABILITY_DASHBOARD.md) before assigning a
physical interpretation.

## Requirements

- Python 3.10 or newer.
- Macaulay2 only for operations whose capability contract declares that
  backend requirement, notably supported periodic Laurent/Ext computations.
  Finite, relative-homology, static defect, and bounded enumeration operations
  do not all require Macaulay2.

## Install

Install the package, then install the project-local skills:

```bash
pipx install "git+https://github.com/Misaka16384/mobility-toolkit.git"
mobility-toolkit install
```

Add the optional MCP transport with:

```bash
mobility-toolkit install --mcp
```

From a development clone:

```bash
git clone https://github.com/Misaka16384/mobility-toolkit.git
cd mobility-toolkit
python -m venv .venv
# Windows:
. .venv/Scripts/activate
# Linux/macOS:
# . .venv/bin/activate
pip install -e ".[dev]"
mobility-toolkit install
```

Skills are copied into project-level agent directories. MCP configuration is
opt-in.

| Agent | Skills | MCP config with `--mcp` |
|---|---|---|
| Claude Code | `.claude/skills/` | `.mcp.json` |
| opencode | `.opencode/skills/` | `opencode.json` |
| Codex | `.agents/skills/` | `.codex/config.toml` |
| Antigravity 2.0 | `.agents/skills/` | `.agents/mcp_config.json` |

Useful administration commands:

```bash
mobility-toolkit install --list
mobility-toolkit install --yes
mobility-toolkit self-update
mobility-toolkit --version
```

`mobility-toolkit doctor` is a low-level diagnostic for Macaulay2-backed
operations. It is not a computational skill or an alternate public API.

## Public skills

The supported inventory is exactly these eight use-case skills:

| Skill | Primary operation family | Scope |
|---|---|---|
| `mt-finite-code` | `finite.code.*` | Finite generalized-Pauli arithmetic, centralizers, logical groups, and GSD |
| `mt-boundary-algebra` | `boundary.finite.*`, `boundary.enumeration.*` | Explicit finite cuts, paired groups, primary projections, and bounded E1/E2 searches |
| `mt-relative-homology` | `topology.relative_homology` | Exact cellular relative homology for explicit finite pairs |
| `mt-halfspace` | `boundary.halfspace.*` | Oriented one-sided Laurent half-spaces and source-locked benchmarks |
| `mt-gapped-boundary-2d` | `boundary.completion2d.*` | Finite metric condensation and explicitly bounded local completions |
| `mt-gapped-boundary-3d` | `boundary.symbolic3d.*` | E1/E2 and bounded symbolic E3 candidate searches |
| `mt-defect` | `defects.*` | Finite stratified boundaries, endpoints, tubes, and junction incidence |
| `mt-cheshire` | `defects.cheshire.*` | 2D toric and finite Abelian classification/fusion, finite lattice/circuit checks, 3+1D reference, and graded X-cube candidates |

Each skill is a thin transport to the same registry. Skills do not own a
separate validator or algorithm implementation.

## Canonical service transport

Discover operations and their machine-readable input contracts:

```bash
mobility-toolkit service-catalog
```

Execute one canonical `ServiceRequest`:

```bash
mobility-toolkit service --request '{
  "schema": "mobility_toolkit.service_request.v1",
  "schema_version": "2",
  "operation": "finite.code.capabilities",
  "input_data": {}
}'
```

The same payload can be read from standard input by passing `--request -`.
Python callers use `ServiceRequest` plus `execute_service_request`, or the JSON
adapter `execute_service_payload`. MCP and skill scripts forward that same
transport object.

There are no public per-algorithm convenience CLI commands. Old matrix-string,
polynomial-string, blocked/interleaved-vector, and dimension-specific tuple
contracts are not accepted by the canonical service.

## Streaming and checkpoints

Two bounded enumerators currently expose incremental pages:

- `boundary.completion2d.enumerate`;
- `boundary.symbolic3d.enumerate`.

Use the NDJSON transport:

```bash
mobility-toolkit service-stream --request - < request.json
```

`--request` accepts a JSON object or `-` for standard input. Add
`--max-pages 20` (or another positive integer) to impose a transport page
ceiling.

Each output line is a complete `ServiceExecution` envelope. An incomplete page
contains a sealed `result.value.next_checkpoint`; resuming means placing that
checkpoint back into the original request.

Python callers that want persistence explicitly import
`SQLiteCheckpointStore` from `mobility_toolkit.services` and construct it with
a caller-selected path. The store is caller-owned: importing the package does
not create a database, choose a path, or open process-global state. It binds
each session to the canonical base request and rejects foreign, tampered,
completed, or non-progressing checkpoint chains.

## Canonical inputs

- Start from `service-catalog`; each operation owns a strict JSON object schema.
- Finite operators are phase-aware, site-labelled sparse generalized-Pauli
  data with explicit local dimensions. Algebraic identity does not depend on a
  floating-point drawing position.
- Periodic inputs use a structured Laurent AST, translation group, Pauli basis,
  local-order relations, stabilizer-image columns, and phase modulus. Free-form
  polynomial strings and flat Pauli matrices are not the public IR.
- Composite and nonuniform periodic presentations are representable. Whether a
  requested operation is executable is operation- and backend-specific.
  Unsupported Ext domains remain structured `unsupported`/experimental
  results; there is no bypass switch.
- Geometry requests state the selected finite region, identifications,
  restriction policy, strata, and search domain explicitly.
- Enumeration claims apply only to the serialized finite window, support,
  period, rank/exponent box, candidate family, equivalence relation, and
  resource budget.

## Macaulay2 backend

Macaulay2 invocation is resolved in this order:

1. `MOBILITY_M2_CMD`;
2. `MOBILITY_M2_DOCKER_IMAGE`;
3. native `M2` on `PATH`;
4. WSL on Windows, with distro selected by `MOBILITY_M2_WSL_DISTRO`.

Run `mobility-toolkit doctor` to inspect the resolved backend and perform a
small smoke test. Backend absence must produce structured unsupported behavior
or an explicit non-release skip; it must never fabricate an exact result.

## Development and releases

```bash
pip install -e ".[dev]"
pytest
python tools/phase10_verify_dashboard.py
```

Importable code lives in `mobility_toolkit/`; bundled skill sources live in
`mobility_toolkit/skills/`. The version source of truth is
`mobility_toolkit.__version__`; `pyproject.toml` derives it dynamically.

Use the release helper:

```bash
python tools/release.py
python tools/release.py --minor
python tools/release.py --set 1.2.3
python tools/release.py --push
```

The [research release checklist](docs/RELEASE_CHECKLIST.md) requires the
operation-scoped dashboard, four evidence layers, full-suite results, and
external-backend records before a research release is promoted. Notable changes
per release are recorded in [`CHANGELOG.md`](CHANGELOG.md).
