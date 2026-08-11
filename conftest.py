"""Pytest bootstrap.

Ensures the repo root is on ``sys.path`` so ``import mobility_toolkit`` resolves
when running ``pytest`` directly from a fresh clone, before ``pip install -e .``.

Also enforces the project's own backend policy at the test boundary: a missing
Macaulay2 must produce an explicit skip, never a failure and never a fabricated
result.  Roughly seventy tests reach the backend through call paths that carry
no ``skipif`` guard, so without the hook below a machine with no Macaulay2 sees
them as errors rather than as uncovered ground.
"""
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# The single sentinel emitted by mobility_toolkit.engine._no_backend_message().
_NO_BACKEND_SENTINEL = "Macaulay2 backend not found"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Convert *backend-absent* failures into skips, and nothing else.

    Only a failure whose exception text carries the engine's own
    no-backend sentinel is rewritten.  Every other failure — including a wrong
    invariant, a bad dimension, or a genuine Macaulay2 error with a different
    message — is reported unchanged.  A test that deliberately asserts the
    absent-backend error already passes, so it never reaches this branch.
    """
    outcome = yield
    report = outcome.get_result()
    if not report.failed or call.excinfo is None:
        return
    if _NO_BACKEND_SENTINEL not in str(call.excinfo.value):
        return
    report.outcome = "skipped"
    report.longrepr = (
        str(item.fspath),
        item.location[1],
        "Skipped: Macaulay2 backend not available (see `mobility-toolkit doctor`)",
    )
