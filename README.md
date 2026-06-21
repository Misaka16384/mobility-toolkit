# mobility_toolkit

A homological-algebra toolkit for computing **excitation-mobility properties of
translation-invariant stabilizer codes** — point/lineon/planon/fracton mobility,
ground-state degeneracy (GSD), anyon periodicities, and fusion interference — packaged
as a **cross-platform agent skill set** for Claude Code, OpenAI Codex, opencode, and
Google Antigravity.

Stabilizer models are mapped to modules over a Laurent polynomial ring; `Ext` modules,
Krull dimensions, Gröbner bases, and saturations (computed by **Macaulay2**) do the
classification. The Python core is pure-stdlib and shells out to an external Macaulay2
binary.

## Requirements

- **Python ≥ 3.9**
- **Macaulay2** reachable as `M2` (native on Linux/macOS, via **WSL** on Windows, or via
  **Docker**). See [macaulay2.com](https://macaulay2.com).

## Install

```bash
git clone <this-repo> mobility_toolkit
cd mobility_toolkit
python -m venv .venv && . .venv/Scripts/activate   # (Linux/macOS: . .venv/bin/activate)
pip install -e ".[mcp]"        # core + MCP server; use ".[dev]" to also get pytest

mobility-toolkit doctor        # verify the Macaulay2 backend
mobility-toolkit install       # wire skills + MCP into detected agents (project-level)
```

`mobility-toolkit install` is **project-level by default** and auto-detects which agents
are present, writing each agent's native config:

| Agent | Skills → | MCP config → |
|---|---|---|
| Claude Code | `.claude/skills/` | `.mcp.json` |
| opencode | `.opencode/skills/` (also reads `.claude/skills/`) | `opencode.json` |
| Codex | `.agents/skills/` | `.codex/config.toml` |
| Antigravity | `~/.gemini/skills/` *(global only)* | `~/.gemini/config/mcp_config.json` |

Antigravity has no per-project config, so it is **opt-in**: `mobility-toolkit install
--target antigravity` (or `--target all`).

Useful install flags:

```bash
mobility-toolkit install --target claude --target codex   # pick agents
mobility-toolkit install --target all                     # incl. Antigravity (global)
mobility-toolkit install --project-dir /path/to/project   # install elsewhere
mobility-toolkit install --list                           # show status
mobility-toolkit install --uninstall                      # remove
```

## Macaulay2 backend

The M2 invocation is resolved per platform, overridable by environment variable:

| Variable | Effect |
|---|---|
| `MOBILITY_M2_CMD` | Explicit command, e.g. `wsl -d Ubuntu M2 --no-readline -q` |
| `MOBILITY_M2_DOCKER_IMAGE` | Run M2 inside `docker run --rm -i <image>` |
| `MOBILITY_M2_WSL_DISTRO` | WSL distro name on Windows (default `Ubuntu`) |

Resolution order: `MOBILITY_M2_CMD` → Docker image → native `M2` on PATH → WSL (Windows).
There is no official Macaulay2 Docker image; if you use the Docker path, point
`MOBILITY_M2_DOCKER_IMAGE` at one you build/pull (see the
[M2 Docker guide](https://github.com/Macaulay2/M2/blob/master/M2/BUILD/docker/README.md)).

Run `mobility-toolkit doctor` to see what was resolved.

## CLI examples

```bash
# Toric code point excitations: Krull dimension 0 (fully mobile anyons)
mobility-toolkit homology \
  --stabilizer '[["1 - x","1 - y","0","0"],["0","0","1 - y","1 - x"]]' --qudit-dim 2 --p-ext 0

# X-Cube point excitations: Krull dimension 2 (fractons)
mobility-toolkit homology \
  --stabilizer '[["1 - x","1 - y","1 - z","0"],["0","1 - y","1 - z","1 - x"]]' --qudit-dim 2 --p-ext 0

# Seed + query the bundled model registry
mobility-toolkit db init
mobility-toolkit db query --query-str "SELECT name, gsd_val FROM models WHERE qudit_dim=12"
```

## Input conventions

- **`qudit_dim` must be prime** (ring is `ZZ/N`); for composite `N` pass `--prime-bypass`.
- **No parentheses** in polynomials — fully expand (`y + z + x*y + x*z`, not `(1+x)*(y+z)`).
- Variables: spatial `x, y, z`; Laurent inverses `t, u, w` (`x*t = y*u = z*w = 1`).
  Write inverses as `x^-1` / `x**-1`; they are rewritten to `t`/`u`/`w`.

## Development

```bash
pip install -e ".[dev]"
pytest                       # M2-backed tests require a working Macaulay2 backend
```

Importable code lives in `mobility_toolkit/`; SKILL.md sources live in `skills/`. See
[`AGENTS.md`](AGENTS.md) for agent-facing usage notes.
