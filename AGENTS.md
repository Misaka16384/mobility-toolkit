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

- **Skills** (`skills/*/SKILL.md`) — installed into each agent's skills directory.
- **MCP server** — `python -m mobility_toolkit.mcp_server` (needs `fastmcp`).
- **CLI** — `mobility-toolkit <subcommand>` (JSON in / JSON out).

| Skill / MCP tool | CLI | Purpose |
|---|---|---|
| `translate_to_algebra` | — | Parse a stabilizer matrix → Laurent ring + M2 definitions |
| `compute_homology_and_mobility` / `compute_homology` | `homology` | `Ext^{p+1}` module + Krull dimension (excitation mobility) |
| (mobility) / `compute_mobility` | `mobility` | True physical mobility dimension of an annihilator ideal |
| (grobner) / `compute_grobner` | `grobner` | GSD + anyon periodicities on an Lx×Ly torus |
| `analyze_fusion_interference` / `compute_fusion_interference` | `fusion-interference` | Dimension drops under relative shift vectors |
| (search) / `search_models` | `search` | Reverse-search Koszul models hitting a target dimension |
| `query_vector_db` | `db` | SQLite model registry (init / seed / sync / query) |
| — | `doctor` | Diagnose the Macaulay2 backend (+ live smoke test) |

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
- Don't commit install artifacts (`.claude/`, `.opencode/`, `.codex/`, `.agents/`,
  `.mcp.json`, `opencode.json`, `output/`); they're git-ignored.

Install is **skills-only by default** (the agent runs each skill's bundled
`scripts/<name>.py` directly); MCP is opt-in via `mobility-toolkit install --mcp`.
Project-level skill dirs: Claude `.claude/skills/`; opencode `.opencode/skills/`;
Codex & Antigravity 2.0 share `.agents/skills/`. With `--mcp`, the matching MCP
config is also written (`.mcp.json` / `opencode.json` / `.codex/config.toml` /
`.agents/mcp_config.json`).
