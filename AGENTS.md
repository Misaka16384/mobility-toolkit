# AGENTS.md — mobility_toolkit

Shared instructions for AI coding agents (Claude Code, OpenAI Codex, opencode,
Google Antigravity) working in or with this repository.

## What this is

`mobility_toolkit` computes **excitation-mobility properties of translation-invariant
stabilizer codes** using homological algebra. A Pauli stabilizer model is mapped to a
module over a Laurent polynomial ring; `Ext` modules, Krull dimensions, Gröbner bases,
and saturations (computed by **Macaulay2**) then classify how excitations move
(point / lineon / planon / fracton), ground-state degeneracy (GSD), and fusion
interference.

The math backend is an external **Macaulay2** binary. The Python core is pure-stdlib
and only orchestrates M2 scripts and parses their output.

## Capabilities

Exposed three ways over the same core (`mobility_toolkit/`):

- **Skills** (`skills/mt-*/SKILL.md`) — installed into each agent's skills directory.
- **MCP server** — `python -m mobility_toolkit.mcp_server` (needs `fastmcp`).
- **CLI** — `mobility-toolkit <subcommand>` (JSON in / JSON out).

### Three-layer model

Skills are named `mt-*` and organized as **edges between three layers** — pick a skill by
"what I have → what I want":

- **L1 Model** — the Pauli stabilizer matrix over `ZZ/N[x,y,z,…]`.
- **L2 Algebra** — ring/matrix, `Ext^{p+1}` charge module, annihilator ideal, Gröbner
  basis, Krull dimension.
- **L3 Physics** — mobility class (fully-mobile / planon / lineon / fracton; topological
  vs fracton), GSD, anyon periodicities, fusion interference.

| Skill | Edge | CLI | Purpose |
|---|---|---|---|
| `mt-translate` | L1→L2 | — | Stabilizer matrix → Laurent ring + variables + M2 matrix |
| `mt-homology` | L1→L2 | `homology` | `Ext^{p+1}` module + Krull dim + annihilator (class attached) |
| `mt-classify` | L2→L3 | `classify` | Krull dimension → mobility class (pure, no backend) |
| `mt-mobility` | L2→L3 | `mobility` | Annihilator generators → true mobility dimension |
| `mt-gsd` | L1→L3 | `grobner` | GSD + anyon periodicities on an Lx×Ly torus (any N) |
| `mt-fusion` | L1→L3 | `fusion-interference` | Dimension drops under relative shift vectors |
| `mt-models` | L1↔L3 | `db` | SQLite model/property registry (init / seed / sync / query) |
| `mt-doctor` | infra | `doctor` | Diagnose the Macaulay2 backend (+ live smoke test) |

CLI-only (no skill): `sset-fusion`, `search`, `install`, `self-update`.

## Input conventions (IMPORTANT — these cause most errors)

- **`qudit_dim` must be prime** (the ring is `ZZ/N`). For composite `N` (e.g. 12),
  pass `prime_bypass=True` / `--prime-bypass`.
- **No parentheses in polynomials.** Inputs are validated against a strict character
  whitelist. Fully expand everything: use `y + z + x*y + x*z`, never `(1+x)*(y+z)`.
- **Variables**: spatial `x, y, z`; their Laurent inverses are `t, u, w`
  (`x*t = y*u = z*w = 1`). Use `x^-1` / `x**-1` in input; it is rewritten to `t`.
- A stabilizer matrix is a list of rows (lists of polynomial strings). All rows must
  have equal length.

## Backend / environment

Macaulay2 invocation is resolved per platform (see `engine.resolve_m2_command`):

1. `MOBILITY_M2_CMD` — explicit override, e.g. `"wsl -d Ubuntu M2 --no-readline -q"`.
2. `MOBILITY_M2_DOCKER_IMAGE` — run M2 inside `docker run --rm -i <image>`.
3. native `M2` on PATH (Linux/macOS / native Windows).
4. WSL on Windows — distro from `MOBILITY_M2_WSL_DISTRO` (default `Ubuntu`).

Always run `mobility-toolkit doctor` first when a computation fails — it reports the
resolved backend and runs a `2+2` smoke test.

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
