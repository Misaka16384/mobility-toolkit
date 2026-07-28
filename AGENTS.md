# AGENTS.md — mobility_toolkit

Shared instructions for AI coding agents (Claude Code, OpenAI Codex, opencode,
Google Antigravity) working in or with this repository.

## What this is

`mobility_toolkit` is a boundary-aware generalized-Pauli stabilizer-code
research toolkit. It combines finite abelian-group algebra, explicit geometry,
cellular relative homology, canonical periodic Laurent presentations,
oriented half-spaces, bounded boundary enumeration, stratified defects, and
finite static Cheshire analysis.

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
| `mt-cheshire` | `defects.cheshire.*` | Finite Cheshire static analysis, tube-to-line synthesis, bounded species search, and static fusion |

Every operation owns its input schema, exactness level, certificate,
provenance, assumptions, and warnings. Query its capability operation before
using a result. In particular, a finite or bounded-exact result is not a
thermodynamic classification, and an `unsupported` result must not be replaced
with a heuristic conclusion.

The computational CLI contains only `service`, `service-catalog`, and
`service-stream`. The streaming command emits NDJSON pages for the registered
2D-completion and symbolic-3D enumerators. Resume state can optionally be
persisted by explicitly constructing
`mobility_toolkit.services.SQLiteCheckpointStore(path)`; there is no default
database or process-global checkpoint store.

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

## Working in this repo

- Install editable: `pip install -e ".[dev]"` (add `mcp` extra for the MCP server).
- Run tests: `pytest` (M2-backed tests need a working Macaulay2 backend).
- Package layout: importable code is in `mobility_toolkit/`; SKILL.md sources are in
  `mobility_toolkit/skills/` (bundled in the wheel); the installer copies those into
  each agent's location.
- Version: single source of truth is `mobility_toolkit.__version__` (in
  `__init__.py`); `pyproject.toml` derives the package version from it
  (`dynamic = ["version"]`). Never hand-edit a version into `pyproject.toml`.
- Cut a release with `python tools/release.py [--minor|--major|--set X.Y.Z] [--push]`:
  it bumps `__version__`, commits, and tags `vX.Y.Z`. Bumping the version is what
  makes `pipx upgrade` pull the new release.
- Don't commit install artifacts (`.claude/`, `.opencode/`, `.codex/`, `.agents/`,
  `.mcp.json`, `opencode.json`, `output/`); they're git-ignored.

Install is **skills-only by default** (the agent runs each skill's bundled
`scripts/<name>.py` directly); MCP is opt-in via `mobility-toolkit install --mcp`.
Project-level skill dirs: Claude `.claude/skills/`; opencode `.opencode/skills/`;
Codex & Antigravity 2.0 share `.agents/skills/`. With `--mcp`, the matching MCP
config is also written (`.mcp.json` / `opencode.json` / `.codex/config.toml` /
`.agents/mcp_config.json`).

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
