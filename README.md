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

**One-time — install the CLI** (isolated, with [pipx](https://pipx.pypa.io)):

```bash
pipx install "git+https://github.com/Misaka16384/mobility-toolkit.git"
# also want the optional MCP server?
#   pipx install "mobility-toolkit[mcp] @ git+https://github.com/Misaka16384/mobility-toolkit.git"
```

> No pipx? `python -m pip install --user pipx && pipx ensurepath`, or `pip install "git+https://…"` into a venv.

**Per project — one interactive line.** Open a terminal in the project folder and run:

```bash
mobility-toolkit install
```

That launches an interactive flow (pick agents → MCP yes/no → confirm) and wires everything
into that project. Run `mobility-toolkit doctor` first to check the Macaulay2 backend.

<details><summary>From a clone (development)</summary>

```bash
git clone https://github.com/Misaka16384/mobility-toolkit.git
cd mobility-toolkit
python -m venv .venv && . .venv/Scripts/activate   # (Linux/macOS: . .venv/bin/activate)
pip install -e ".[dev]"        # editable; add ".[mcp]" for the MCP server
mobility-toolkit install
```
</details>

`mobility-toolkit install` is **project-level by default** and installs **skills only** —
the agent runs each skill's bundled script directly (`python scripts/<name>.py < input.json`).
MCP is **opt-in** via `--mcp`. The toolkit auto-detects which agents are present:

| Agent | Skills → (always) | MCP config → (only with `--mcp`) |
|---|---|---|
| Claude Code | `.claude/skills/` | `.mcp.json` |
| opencode | `.opencode/skills/` (also reads `.claude/skills/`) | `opencode.json` |
| Codex | `.agents/skills/` | `.codex/config.toml` |
| Antigravity 2.0 | `.agents/skills/` *(shared with Codex)* | `.agents/mcp_config.json` |

All four are project-level. `.agents/skills/` is shared by Codex and Antigravity 2.0.
To install Antigravity globally instead (`~/.gemini/`), add `--antigravity-global`.
(The MCP server needs the `[mcp]` extra: `pip install -e ".[mcp]"`.)

A bare `mobility-toolkit install` is **interactive** when run in a terminal. Passing any
of `--target` / `--mcp` / `--yes` makes it non-interactive (scriptable / CI):

```bash
mobility-toolkit install --yes                            # non-interactive: detected agents, skills-only
mobility-toolkit install --target claude --target codex   # pick agents
mobility-toolkit install --target all                     # all four agents
mobility-toolkit install --mcp                            # also wire the MCP server
mobility-toolkit install --target antigravity --antigravity-global  # Antigravity into ~/.gemini
mobility-toolkit install --project-dir /path/to/project   # install elsewhere
mobility-toolkit install --list                           # show status
mobility-toolkit install --uninstall                      # remove
```

## Updating

The project skills are **copies**, so updating is two steps — pull the latest code,
then refresh each project. One command does both:

```bash
cd /path/to/project
mobility-toolkit self-update
```

It detects how the toolkit was installed and updates accordingly — `git pull` for a
clone, or a pip reinstall from the git URL for a pipx/wheel install — then re-installs
**exactly the agents already wired into this project** (preserving your MCP choice).
Useful flags:

```bash
mobility-toolkit self-update --dry-run      # show what it would run, change nothing
mobility-toolkit self-update --no-refresh   # update the package only
mobility-toolkit self-update --mcp          # also (re)wire the MCP config
```

Prefer to do it by hand? Update the package, then re-run `install` in each project:

```bash
pipx upgrade mobility-toolkit               # wheel/pipx — picks up the latest release
# or, from a clone:  git pull
mobility-toolkit install --yes              # refresh this project's skills
```

Check what you have with `mobility-toolkit --version`.

> `pipx upgrade` works **across releases** because each release bumps the version (see
> [Development](#development)). To pull *un-released* commits on `main` (same version
> number), use `mobility-toolkit self-update` or
> `pipx install --force "git+https://github.com/Misaka16384/mobility-toolkit.git"`.

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

Importable code lives in `mobility_toolkit/`; SKILL.md sources live in
`mobility_toolkit/skills/` (bundled into the wheel). See
[`AGENTS.md`](AGENTS.md) for agent-facing usage notes.

### Cutting a release

The version is a single source of truth in `mobility_toolkit/__init__.py`
(`__version__`); `pyproject.toml` derives the package version from it. Bumping it
on each release is what lets users `pipx upgrade`. Use the helper:

```bash
python tools/release.py                 # patch bump (0.1.0 -> 0.1.1), commit + tag
python tools/release.py --minor         # 0.1.0 -> 0.2.0
python tools/release.py --set 1.2.3     # explicit version
python tools/release.py --push          # also push the commit + tag to origin
python tools/release.py --dry-run       # preview, change nothing
```

It refuses to run on a dirty tree (override with `--allow-dirty`) or a tag that
already exists. After pushing, `pipx upgrade mobility-toolkit` picks it up.

See [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) for the full development, release,
and update workflow (install kinds, version model, refreshing project skills).
