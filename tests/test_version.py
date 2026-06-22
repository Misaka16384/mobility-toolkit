"""Version single-source-of-truth, the `--version` CLI flag, and the release bumper.

Pure Python; no Macaulay2 backend required.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

import mobility_toolkit

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _load_release_tool():
    spec = importlib.util.spec_from_file_location("release_tool", ROOT / "tools" / "release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_package_version_is_semver():
    assert SEMVER.match(mobility_toolkit.__version__), mobility_toolkit.__version__


def test_cli_version_flag_matches_package():
    proc = subprocess.run(
        [sys.executable, "-m", "mobility_toolkit", "--version"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr
    assert mobility_toolkit.__version__ in proc.stdout


def test_pyproject_declares_dynamic_version():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in text
    assert 'attr = "mobility_toolkit.__version__"' in text
    # a static quoted `version = "x.y.z"` must be gone (it would clash with dynamic);
    # the dynamic table's `version = { attr = ... }` is fine and must not match.
    assert not re.search(r"""^version\s*=\s*["']""", text, re.M)


def test_release_bump_version():
    rel = _load_release_tool()
    assert rel.bump_version("0.1.0", "patch") == "0.1.1"
    assert rel.bump_version("0.1.9", "patch") == "0.1.10"
    assert rel.bump_version("0.1.5", "minor") == "0.2.0"
    assert rel.bump_version("1.4.7", "major") == "2.0.0"
    with pytest.raises(ValueError):
        rel.bump_version("not-a-version", "patch")
    with pytest.raises(ValueError):
        rel.bump_version("0.1.0", "nonsense")


def test_release_read_and_replace_roundtrip():
    rel = _load_release_tool()
    sample = '# header\n__version__ = "0.1.0"\nfrom x import y\n'
    assert rel.read_version(sample) == "0.1.0"
    bumped = rel.replace_version(sample, "0.2.3")
    assert '__version__ = "0.2.3"' in bumped
    assert rel.read_version(bumped) == "0.2.3"


def test_release_tool_reads_live_version():
    """The bumper reads the same version the package reports."""
    rel = _load_release_tool()
    assert rel.read_version() == mobility_toolkit.__version__
