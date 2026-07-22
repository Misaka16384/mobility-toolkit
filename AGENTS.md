# AGENTS.md — mobility_toolkit

Shared instructions for AI coding agents (Claude Code, OpenAI Codex, opencode,
Google Antigravity) working in or with this repository.

## What this is

`mobility_toolkit` computes **charge-module invariants of translation-invariant
stabilizer codes** using homological algebra. The corrected homology path evaluates
Ruba--Yang's `Q^p = Ext_R^(p+1)(bar(P/L),R)` and validates the stabilizer map.
Krull dimension alone is not mapped to planon/lineon/fracton labels. GSD,
finite-torus periodicity, fusion, and boundary algorithms are separate features.

The homological backend is an external **Macaulay2** binary. NumPy/SymPy support
other finite-lattice and translation-lattice calculations.

## Capabilities

Exposed three ways over the same core (`mobility_toolkit/`):

- **Skills** (`skills/mt-*/SKILL.md`) — installed into each agent's skills directory.
- **MCP server** — `python -m mobility_toolkit.mcp_server` (needs `fastmcp`).
- **CLI** — `mobility-toolkit <subcommand>` (JSON in / JSON out).

### Three-layer model

Skills are named `mt-*` and organized as **edges between three layers** — pick a skill by
"what I have → what I want":

- **L1 Model** — the Pauli stabilizer matrix over `ZZ/N[x,y,z,…]`.
- **L2 Algebra** — ring/matrix, `Ext^{p+1}(bar(P/L),R)` charge module, annihilator ideal, Gröbner
  basis, Krull dimension.
- **L3 Physics** — theorem-scoped mobility conclusions, GSD, periodicities, and
  independently sourced fusion results.

| Skill | Edge | CLI | Purpose |
|---|---|---|---|
| `mt-translate` | L1→L2 | — | Stabilizer matrix → Laurent ring + variables + M2 matrix |
| `mt-homology` | L1→L2 | `homology` | Validated `Ext^{p+1}(bar(P/L),R)` + Krull dim + annihilator |
| `mt-classify` | L2→L3 | `classify` | The theorem-safe conclusion supported by Krull dimension |
| `mt-mobility` | L2→L3 | `mobility` | Exact translation lattice for Laurent-binomial annihilators |
| `mt-gsd` | L1→L3 | `grobner` | GSD + anyon periodicities on an Lx×Ly torus (any N) |
| `mt-fusion` | L1→L3 | `fusion-interference` | Dimension drops under relative shift vectors |
| `mt-models` | L1↔L3 | `db` | SQLite model/property registry (init / seed / sync / query) |
| `mt-doctor` | infra | `doctor` | Diagnose the Macaulay2 backend (+ live smoke test) |

CLI-only (no skill): `sset-fusion`, `search`, `install`, `self-update`.

## Input conventions (IMPORTANT — these cause most errors)

- The current Ext backend requires a uniform prime **`qudit_dim`**. The paper is
  more general; `prime_bypass` does not add composite Ext support.
- **No parentheses in polynomials.** Inputs are validated against a strict character
  whitelist. Fully expand everything: use `y + z + x*y + x*z`, never `(1+x)*(y+z)`.
- **Variables**: spatial `x, y, z`; their Laurent inverses are `t, u, w`
  (`x*t = y*u = z*w = 1`). Use `x^-1` / `x**-1` in input; it is rewritten to `t`.
- A stabilizer matrix is a list of equal-length rows. Each row is one generator
  in `[X_1,...,X_q,Z_1,...,Z_q]` coordinates, so its length must be even.
  Homology checks `sigma^dagger lambda sigma=0` by default.
- Supply `spatial_dim` when the ambient ring has axes absent from the coefficients.

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

<!-- mobility-toolkit:start -->
## mobility_toolkit

Homological-algebra toolkit for validated Ruba--Yang charge-module invariants of translation-invariant stabilizer codes (backed by Macaulay2). Krull dimension is interpreted only within the theorem's stated scope.

Skills are organized by three layers -- L1 model, L2 algebra, L3 physics -- each skill being an edge between two layers:
- L1->L2: `mt-translate`, `mt-homology`
- L2->L3: `mt-classify`, `mt-mobility`
- L1->L3: `mt-gsd`, `mt-fusion`
- store/infra: `mt-models`, `mt-doctor`
Each skill bundles a script run directly, e.g. `python scripts/<name>.py < input.json`.

Optionally also available as MCP server `mobility_toolkit` (install with `mobility-toolkit install --mcp`).

Run `mobility-toolkit doctor` to verify the Macaulay2 backend; `mobility-toolkit self-update` to pull the latest version and refresh these skills.
<!-- mobility-toolkit:end -->
