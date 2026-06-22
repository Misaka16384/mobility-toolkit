#!/usr/bin/env python3
"""Cut a release: bump the version, commit, and tag (optionally push).

The version is the single source of truth in ``mobility_toolkit/__init__.py``
(``__version__``); ``pyproject.toml`` derives the package version from it. Bumping
it on each release is what makes ``pipx upgrade mobility-toolkit`` see a newer
version and actually pull the new code (a static version makes pip treat the git
install as "already up to date").

Usage::

    python tools/release.py                 # patch bump (0.1.0 -> 0.1.1)
    python tools/release.py --minor         # 0.1.0 -> 0.2.0
    python tools/release.py --major         # 0.1.0 -> 1.0.0
    python tools/release.py --set 1.2.3     # set an explicit version
    python tools/release.py --push          # also push the commit + tag to origin
    python tools/release.py --dry-run       # show what would happen, change nothing
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_PY = REPO_ROOT / "mobility_toolkit" / "__init__.py"
VERSION_RE = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.M)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


# --- pure helpers (unit-tested) -------------------------------------------
def read_version(text: str = None) -> str:
    text = INIT_PY.read_text(encoding="utf-8") if text is None else text
    m = VERSION_RE.search(text)
    if not m:
        raise SystemExit(f"could not find __version__ in {INIT_PY}")
    return m.group(1)


def bump_version(current: str, part: str = "patch") -> str:
    if not SEMVER_RE.match(current):
        raise ValueError(f"version {current!r} is not X.Y.Z")
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown bump part {part!r}")


def replace_version(text: str, new: str) -> str:
    new_text, n = VERSION_RE.subn(f'__version__ = "{new}"', text)
    if n != 1:
        raise SystemExit(f"expected exactly one __version__ line, found {n}")
    return new_text


# --- git plumbing ----------------------------------------------------------
def git(*args, check=True, capture=False):
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=check, text=True, capture_output=capture,
    )


def git_out(*args) -> str:
    return git(*args, capture=True).stdout.strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bump the version, commit, and tag a release.")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--major", action="store_const", const="major", dest="part", help="X+1.0.0")
    grp.add_argument("--minor", action="store_const", const="minor", dest="part", help="x.Y+1.0")
    grp.add_argument("--patch", action="store_const", const="patch", dest="part", help="x.y.Z+1 (default)")
    ap.add_argument("--set", dest="explicit", metavar="X.Y.Z", help="Set an explicit version")
    ap.add_argument("--push", action="store_true", help="Push the commit + tag to origin")
    ap.add_argument("--allow-dirty", action="store_true", help="Skip the clean-working-tree check")
    ap.add_argument("--dry-run", action="store_true", help="Show actions without changing anything")
    args = ap.parse_args(argv)

    current = read_version()
    if args.explicit:
        if not SEMVER_RE.match(args.explicit):
            raise SystemExit(f"--set value {args.explicit!r} is not X.Y.Z")
        new = args.explicit
    else:
        new = bump_version(current, args.part or "patch")
    tag = f"v{new}"

    print(f"current : {current}")
    print(f"release : {new}   (tag {tag})")

    # guards
    if git_out("status", "--porcelain") and not args.allow_dirty and not args.dry_run:
        raise SystemExit("working tree not clean — commit/stash first, or pass --allow-dirty")
    if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False, capture=True).returncode == 0:
        raise SystemExit(f"tag {tag} already exists")

    if args.dry_run:
        steps = "write version -> git commit -> git tag" + (" -> git push" if args.push else "")
        print(f"[dry-run] would: {steps}")
        return 0

    INIT_PY.write_text(replace_version(INIT_PY.read_text(encoding="utf-8"), new), encoding="utf-8")
    git("add", str(INIT_PY))
    git("commit", "-m", f"Release {tag}")
    git("tag", "-a", tag, "-m", f"Release {tag}")
    print(f"committed + tagged {tag}")

    if args.push:
        git("push")
        git("push", "origin", tag)
        print(f"pushed commit + {tag} to origin")
    else:
        print(f"not pushed. Publish with:  git push && git push origin {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
