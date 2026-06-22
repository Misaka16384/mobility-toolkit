# Development & Release Workflow

How to develop, release, and update `mobility_toolkit`. The toolkit is consumed
three ways over one core (`mobility_toolkit/`) — agent **skills**, an optional
**MCP server**, and the **`mobility-toolkit` CLI** — but they all ship from this
one repo, so the workflow below covers everything.

## How it's installed (two kinds)

There are two distinct ways the package can live on a machine; knowing which you
have explains most "why didn't my change show up" confusion.

| Kind | What it is | Updates how |
|---|---|---|
| **Wheel / pipx** | A snapshot built from the git URL (`pipx install …`). Provides the `mobility-toolkit` command on `PATH`. This is what end users run. | `pipx upgrade` / `self-update` — a **copy**, so it does *not* track the repo automatically |
| **Editable clone** | `pip install -e .` from a clone. The install points back at the working tree. | `git pull` — code changes are live immediately, no reinstall |

Check what you have:

```bash
mobility-toolkit --version          # version of the command on PATH
pip show mobility-toolkit           # "Editable project location" => editable install
pipx list | grep mobility           # is there a pipx install too?
```

> **Gotcha:** you can have *both* at once (a pipx command **and** an editable
> install in your main Python). If the editable install points at a folder you
> moved or renamed, `import mobility_toolkit` from an unrelated directory will
> silently use stale code. Keep at most one editable install, pointing at the
> clone you actually develop in.

## Local development

```bash
git clone https://github.com/Misaka16384/mobility-toolkit.git
cd mobility-toolkit
python -m venv .venv && . .venv/Scripts/activate   # (Linux/macOS: . .venv/bin/activate)
pip install -e ".[dev]"        # editable; add ".[mcp]" for the MCP server
mobility-toolkit doctor        # confirm the Macaulay2 backend resolves
pytest                         # M2-backed tests need a working Macaulay2 backend
```

With an editable install, edits to `mobility_toolkit/` take effect immediately.
The only thing that does **not** auto-refresh is a project's **copied** skill
folders (`.claude/skills/`, `.agents/skills/`, …) — re-run `mobility-toolkit
install` in that project to recopy them. The copied skill scripts import the core
live, so changes to the *core* are picked up without recopying; only edits to a
skill's own `SKILL.md` / wrapper script need a recopy.

## Version model

The version is a **single source of truth** in `mobility_toolkit/__init__.py`:

```python
__version__ = "0.1.1"
```

`pyproject.toml` derives the package version from it (`dynamic = ["version"]` +
`[tool.setuptools.dynamic] version = {attr = "mobility_toolkit.__version__"}`),
so the wheel, `importlib.metadata`, and `mobility-toolkit --version` always agree.
**Never hand-edit a version into `pyproject.toml`** — bump `__version__` instead
(the release helper does this for you).

## Cutting a release

Bumping the version on each release is what makes `pipx upgrade` actually pull the
new code: with a static version, pip compares `0.1.0 == 0.1.0` and reports
"already up to date". Use the helper:

```bash
python tools/release.py                 # patch bump (0.1.1 -> 0.1.2), commit + tag
python tools/release.py --minor         # 0.1.1 -> 0.2.0
python tools/release.py --major         # 0.1.1 -> 1.0.0
python tools/release.py --set 1.2.3     # explicit version
python tools/release.py --push          # also push the commit + tag to origin
python tools/release.py --dry-run       # preview, change nothing
```

It bumps `__version__`, commits `Release vX.Y.Z`, and creates the annotated tag
`vX.Y.Z`. It refuses to run on a dirty working tree (override with `--allow-dirty`)
or when the tag already exists. Without `--push` it prints the exact push command.

A typical release:

```bash
pytest                                  # green first
python tools/release.py --minor --push  # bump, tag, push in one shot
```

## Updating an install

After a release is pushed, update each machine/project:

```bash
# 1. update the command (wheel/pipx install)
pipx upgrade mobility-toolkit           # picks up the latest release (version bumped)

# 2. refresh each project's copied skills (idempotent)
cd /path/to/project
mobility-toolkit install --yes
```

Or do both in one step from inside a project:

```bash
mobility-toolkit self-update            # update the package + refresh this project
```

`self-update` auto-detects the install kind: `git pull` for an editable clone, or a
`pip install --force-reinstall` from the git URL for a wheel/pipx install (done
in-place so it doesn't recreate the venv — which would fail to delete the running
`python.exe` on Windows). It then re-installs exactly the agents already wired into
the project, preserving the MCP choice. Flags: `--dry-run`, `--no-refresh`, `--mcp`.

**To pull un-released commits** (commits on `main` that share the current version
number), `pipx upgrade` won't see them — use either:

```bash
mobility-toolkit self-update
# or
pipx install --force "git+https://github.com/Misaka16384/mobility-toolkit.git"
```

## Repository layout

- `mobility_toolkit/` — importable core (pure-stdlib; algebra delegated to Macaulay2).
- `mobility_toolkit/skills/` — SKILL.md sources + scripts, bundled into the wheel;
  the installer copies these into each agent's location.
- `tools/release.py` — the release/version bumper (dev-only, not shipped in the wheel).
- `tests/` — `pytest`; M2-backed tests skip automatically without a backend.
- `docs/VALIDATION.md` — benchmark results against known literature models.

Don't commit install artifacts (`.claude/`, `.opencode/`, `.codex/`, `.agents/`,
`.mcp.json`, `opencode.json`, `output/`); they're git-ignored. See
[`AGENTS.md`](../AGENTS.md) for agent-facing usage notes and input conventions.
