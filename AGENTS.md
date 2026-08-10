# AGENTS.md — mobility_toolkit

Shared instructions for AI coding agents (Claude Code, OpenAI Codex, opencode,
Google Antigravity) working in or with this repository. This is the single
agent-facing document for the repo; there is no separate `CLAUDE.md`.

## What this is

`mobility_toolkit` is a boundary-aware generalized-Pauli stabilizer-code
research toolkit. It combines finite abelian-group algebra, explicit geometry,
cellular relative homology, canonical periodic Laurent presentations,
oriented half-spaces, bounded boundary enumeration, stratified defects, and
evidence-graded Cheshire classification, fusion, lattice, and circuit work.

The public computational surface is one versioned native service registry.
Python, CLI, MCP, and the eight use-case skills are transports over that
registry; they are not separate algorithm APIs. Macaulay2 is an
operation-specific backend for supported periodic Laurent/Ext requests, not a
global requirement for finite and relative-homology work.

## Capabilities

The public surface is organized by **use case**, with eight `mt-*` skills over
one operation registry. Skills are installed into each agent's skill
directory; the same registry is available through
`python -m mobility_toolkit.mcp_server` and the package's service API. The CLI
remains a low-level and maintenance surface.

| Skill | Primary service operations | Scope |
|---|---|---|
| `mt-finite-code` | `finite.code.capabilities` | Finite generalized-Pauli arithmetic, centralizers, logical groups, and GSD |
| `mt-boundary-algebra` | `boundary.finite.capabilities`, `boundary.enumeration.capabilities` | Explicit finite cuts, paired groups, primary projections, and bounded E1/E2 searches |
| `mt-relative-homology` | `topology.relative_homology` | Exact cellular relative homology for explicit finite pairs |
| `mt-halfspace` | `boundary.halfspace.*` | Oriented one-sided Laurent half-spaces and source-locked benchmarks |
| `mt-gapped-boundary-2d` | `boundary.completion2d.*` | Finite metric condensation and explicitly bounded local completions |
| `mt-gapped-boundary-3d` | `boundary.symbolic3d.*` | E1/E2 and bounded symbolic E3 candidate searches |
| `mt-defect` | `defects.capabilities` | Finite stratified boundaries, endpoints, tubes, and junction incidence |
| `mt-cheshire` | `defects.cheshire.*` | Complete 2D toric reference, finite pointed/Abelian classification and ordered fusion, finite lattice/circuit replay, retained 3+1D reference, and graded X-cube candidates |

This table is **advisory routing, not a partition**. Every skill script is the
same thin transport (`services.execute_service_payload`), so any skill can
execute any registered operation. `mobility-toolkit service-catalog` is the
authoritative inventory — currently **40 operations**.

Every operation owns its input schema, exactness level, certificate,
provenance, assumptions, and warnings. Query its capability operation before
using a result. In particular, a finite or bounded-exact result is not a
thermodynamic classification, and an `unsupported` result must not be replaced
with a heuristic conclusion.

### The periodic / Ext family

`periodic.presentation`, `periodic.charge_module`, and `periodic.ext` are the
Ruba–Yang charge-module core. They are registered and supported but are **not
named by any `mt-*` row above** — reach them through `mobility-toolkit service`
or any skill script.

Their capability is deliberately input-dependent: the ceiling is
`certified_exact`, but the constraints `coefficient_domain`, `execution_mode`,
and `support_tier` all report `input_dependent`. The canonical presentation is
computed exactly for every representable input; **Ext execution is production
only for the uniform-prime, free-translation domain.** Composite, nonuniform,
and non-free presentations are representable and return structured
`experimental` / `unsupported` results. There is no bypass switch.

## Command-line surface

Computational (one versioned JSON `ServiceRequest` in, JSON out):

| Command | Purpose |
|---|---|
| `service --request <json\|->` | Execute one canonical `ServiceRequest` |
| `service-catalog` | Print the machine-readable operation catalog |
| `service-stream --request <json\|-> [--max-pages N]` | NDJSON pages for the two streamable enumerators |

Administrative (not a computational API):

| Command | Purpose |
|---|---|
| `install [--target …] [--mcp] [--list] [--uninstall] [-y]` | Copy skills (and optional MCP config) into a project |
| `self-update [--dry-run] [--no-refresh] [--mcp]` | Update the package and refresh installed skills |
| `doctor [--no-smoke]` | Resolve the Macaulay2 backend and run a `2+2` smoke test |
| `db {init,seed,sync,query} [--query-str SQL]` | Explicitly manage the personal model registry (read-only queries) |
| `--version` | Print the package version |

Streaming covers exactly `boundary.completion2d.enumerate` and
`boundary.symbolic3d.enumerate`. Each output line is a complete
`ServiceExecution`; an incomplete page carries a sealed
`result.value.next_checkpoint` that is resumed by placing it back into the
original request. Persistence is opt-in and caller-owned: construct
`mobility_toolkit.services.SQLiteCheckpointStore(path)` yourself. Importing the
package creates no database, chooses no path, and opens no process-global state.

Python callers use the root entry points exported from `mobility_toolkit`:
`ServiceRequest`, `ServiceExecutor`, `ServiceExecution`,
`execute_service_request`, `execute_service_payload`, `default_service_catalog`,
`stream_service_payload`, and `streamable_operations`.

## Input conventions (IMPORTANT — these cause most errors)

- Begin with `mobility-toolkit service-catalog`. Every operation owns a strict
  JSON input schema; do not infer one operation's fields from another.
- The only public computational request is
  `mobility_toolkit.service_request.v1`. Unknown top-level and operation input
  fields are rejected.
- Finite operators are phase-aware, site-labelled sparse generalized-Pauli
  data with explicit local dimensions. Floating-point drawing positions,
  bare blocked/interleaved vectors, and dimension-specific tuples are not
  algebraic identities.
- Periodic requests use the canonical Laurent AST: translation group,
  structured terms, explicit Pauli basis and local-order relations,
  stabilizer-image columns, and phase modulus. Free-form polynomial strings
  and flat stabilizer matrices are not the public IR.
- Composite and nonuniform periodic presentations are representable, but
  execution support is operation-specific. The current production Ext path is
  uniform-prime/free-translation; other domains return structured
  experimental or unsupported results. There is no bypass switch.
- Geometry requests state region, identifications, restriction policy, strata,
  equivalence relation, search domain, and resource budget explicitly.
- E1/E2/E3, finite, bounded-exact, experimental, and unsupported results must
  not be promoted beyond the exact domain written in their certificate.

## Backend / environment

Macaulay2 invocation is resolved per platform (see `engine.resolve_m2_command`):

1. `MOBILITY_M2_CMD` — explicit override, e.g. `"wsl -d Ubuntu M2 --no-readline -q"`.
2. `MOBILITY_M2_DOCKER_IMAGE` — run M2 inside `docker run --rm -i <image>`.
3. native `M2` on PATH (Linux/macOS / native Windows).
4. WSL on Windows — distro from `MOBILITY_M2_WSL_DISTRO` (default `Ubuntu`).

When a capability contract requires Macaulay2 and execution fails, use the
low-level `mobility-toolkit doctor` CLI command to report the resolved backend
and run a `2+2` smoke test.

## Repository architecture

Four layers. Changes almost always belong to exactly one of them.

```
core/          Canonical IR and hashing. pauli.py, laurent.py, codes.py,
               canonical.py, and results.py (Exactness, CertificateLevel,
               ComputationResult, BackendProvenance).

domain pkgs    The mathematics. finite/ geometry/ boundary/
               boundary_halfspace/ completion2d/ defects/ anyons2d/
               periodic/. These know nothing about JSON or transports.

services/      The public registry. *_operations.py modules wrap domain code
               as registered operations; contracts.py (ServiceRequest /
               ServiceCapability / ServiceCatalogEntry / ServiceExecution),
               registry.py (dispatch + validation), default.py (assembly,
               executor, caching), cache.py, checkpoint_store.py, streaming.py.

transports     __main__.py (CLI), mcp_server.py, skills/*/scripts/*.py.
               All thin; none owns a validator or an algorithm.
```

Every operation passes through the same four gates:

1. `ServiceExecutor._validate_input_shape` rejects unknown and missing
   `input_data` fields against the catalog schema
   (`services/default.py:97-122`).
2. `ServiceRegistry.capability()` gates execution — an unsupported capability
   raises rather than degrading to an approximation
   (`services/registry.py:98-107`).
3. The registered handler runs and returns a `ComputationResult`.
4. `ServiceRegistry.validate_result` re-checks operation, `canonical_input_hash`,
   assumptions, and certificate level — on **both** fresh and cached results
   (`services/registry.py:109-127`).

Two runtime rules that are easy to miss:

- An operation whose capability declares a `requires_*` constraint is
  **backend-sensitive**: it is cacheable only when the request carries a
  `backend_fingerprint`, so a result computed with one backend can never be
  served for another (`services/default.py:78-84`).
- `ComputationResult` is not a bare value. Anything that computes must fill in
  `exactness`, `theorem_scope`, `certificate`, `backend_provenance`, and
  `warnings` honestly; downstream promotion rules depend on them.

## Changing the toolkit

**Adding an operation.** Write the handler, a capability handler, and a
`ServiceCatalogEntry` in a `services/*_operations.py` module; return them from
that module's `*_service_registrations()`; wire that function into
`build_default_registry()` (`services/default.py:46-53`).
`services/relative_operations.py:239-272` is the smallest complete example.
`adapter_kind` must stay `"native"` — any other value raises.

**Internal modules are not public API.** The top-level `homology.py`,
`translate.py`, `mobility.py`, `fusion.py`, `grobner.py`, `physics.py`,
`search.py`, `bridge.py`, `registry.py`, `reference_models.py`, and
`boundary_gauge/` are still imported directly by tests, but must never be
re-exported from the package root. `tests/test_legacy_public_surface_removed.py`
pins both the removed root names and the removed operation names — read it
before adding anything to `mobility_toolkit/__init__.py`.

**Skill bundles.** Edit `mobility_toolkit/skills/` — that is the wheel source.
The copies under `.claude/skills/`, `.agents/skills/`, and `.opencode/skills/`
are install output and go stale; re-run `mobility-toolkit install` to refresh
them. Core changes are picked up live without recopying, since the copied
scripts import the core. `tests/test_skills_structure.py` pins exactly eight
`mt-*` skills, frontmatter `name` equal to the folder name, exactly one script
per skill named after it, and a description containing a usage trigger.

**Version.** Single source of truth is `mobility_toolkit.__version__` in
`__init__.py` (currently `0.3.0`); `pyproject.toml` derives it via
`dynamic = ["version"]`. Never hand-edit a version into `pyproject.toml`.

## Working in this repo

```bash
pip install -e ".[dev]"                        # extras: mcp, finite, viz
pytest                                         # full suite
pytest tests/test_cheshire.py::test_name -x    # one test
python tools/phase10_verify_dashboard.py       # research-release evidence gate
mobility-toolkit doctor                        # resolve + smoke-test M2
python tools/release.py [--minor|--major|--set X.Y.Z] [--push]
```

`conftest.py` puts the repo root on `sys.path`, so `pytest` works from a fresh
clone before `pip install -e .`.

**M2-backed tests skip silently without a backend.** They compute
`M2_AVAILABLE = describe_m2_backend()["available"]` and guard with
`@pytest.mark.skipif` (e.g. `tests/test_ruba_yang_core.py:12`). A green run on a
machine with no Macaulay2 does not mean the Ext paths were exercised — check the
skip count, or run `mobility-toolkit doctor` first.

`tools/release.py` bumps `__version__`, commits `Release vX.Y.Z`, and tags it.
It refuses a dirty tree (override with `--allow-dirty`) or an existing tag.
Bumping the version is what makes `pipx upgrade` pull new code. The
[research release checklist](docs/RELEASE_CHECKLIST.md) requires the
operation-scoped dashboard, four evidence layers, full-suite results, and
external-backend records before a research release is promoted.

**Do not commit install or scratch artifacts.** Git-ignored: `.agents/`,
`.claude/`, `.opencode/`, `.codex/`, `.gemini/`, `.mcp.json`, `opencode.json`,
`output/`, `tmp/`, `working/`, `mobility_models.db`, and `*.m2`. `AGENTS.md`
itself is authored and committed, so it is intentionally *not* ignored.

Install is **skills-only by default** (the agent runs each skill's bundled
`scripts/<name>.py` directly); MCP is opt-in via `mobility-toolkit install --mcp`.
Project-level skill dirs: Claude `.claude/skills/`; opencode `.opencode/skills/`;
Codex & Antigravity 2.0 share `.agents/skills/`. With `--mcp`, the matching MCP
config is also written (`.mcp.json` / `opencode.json` / `.codex/config.toml` /
`.agents/mcp_config.json`).

## Further reading

- [`docs/THEORY_SCOPE.md`](docs/THEORY_SCOPE.md) — what each exactness tier means.
- [`docs/CAPABILITY_DASHBOARD.md`](docs/CAPABILITY_DASHBOARD.md) — operation-scoped claims.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) — install kinds, release, self-update.
- [`docs/VALIDATION.md`](docs/VALIDATION.md) — benchmarks against literature models.

<!-- Everything below is regenerated by `mobility-toolkit install`
     (installer._write_agents_md). Edit above this line only. -->

<!-- mobility-toolkit:start -->
## mobility_toolkit

Boundary-aware stabilizer-code toolkit with finite generalized-Pauli arithmetic, exact cellular relative homology, oriented Laurent half-spaces, bounded boundary enumeration, and finite defect analysis. Every operation reports its own exactness and scope; finite-window results are not thermodynamic classifications.

Choose one public skill by use case:
- finite foundations: `mt-finite-code`, `mt-relative-homology`
- finite and Laurent boundary algebra: `mt-boundary-algebra`, `mt-halfspace`
- gapped-boundary candidates: `mt-gapped-boundary-2d`, `mt-gapped-boundary-3d`
- stratified and Cheshire defects: `mt-defect`, `mt-cheshire`
The shared service registry owns canonical operation contracts, capability declarations, exactness, certificates, provenance, and warnings. Query the relevant capability operation before requesting a stronger physical conclusion.

Optionally also available as MCP server `mobility_toolkit` (install with `mobility-toolkit install --mcp`).

Run `mobility-toolkit self-update` to pull the latest version and refresh these skills.
<!-- mobility-toolkit:end -->
