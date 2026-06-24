"""Regression tests: a Macaulay2 timeout / missing-backend must NOT be
silently swallowed into a (wrong) "fully mobile" answer.

Background: the WSL-leniency heuristic in ``safe_run_m2_script`` resets a
non-zero exit code to 0 when the output carries no "error" marker. Exit codes
124 (timeout) and 127 (no backend) carry no such marker, so without an explicit
guard a timed-out fracton computation would fall through to an empty valuation
matrix and report ``mobility_dimension == num_vars`` (mobile in every
direction) -- the exact opposite of the truth for an immobile excitation.
"""
import pytest

import mobility_toolkit.mobility as mobility
import mobility_toolkit.fusion as fusion
import mobility_toolkit.registry as registry


@pytest.mark.parametrize("code, stderr", [
    (124, "Macaulay2 process timed out after 60 seconds."),
    (127, "Macaulay2 backend not found. Install Macaulay2 ..."),
])
def test_mobility_timeout_raises_not_mobile(monkeypatch, code, stderr):
    """compute_true_mobility_dimension must raise on timeout/no-backend,
    not return a fabricated full-mobility result."""
    # Force a cache miss so the (monkeypatched) backend path is actually taken;
    # otherwise a prior test that cached this exact input would short-circuit it.
    monkeypatch.setattr(registry.ModelRegistry, "get_cached_properties", lambda self, *a, **k: None)
    monkeypatch.setattr(mobility, "run_m2_script", lambda *a, **k: (code, "", stderr))
    with pytest.raises(RuntimeError):
        mobility.compute_true_mobility_dimension(["z - 1"], qudit_dim=2, all_vars=["x", "y", "z"])


@pytest.mark.parametrize("code", [124, 127])
def test_safe_run_m2_preserves_timeout_codes(monkeypatch, code):
    """The leniency heuristic must preserve 124/127 verbatim in both modules."""
    monkeypatch.setattr(mobility, "run_m2_script", lambda *a, **k: (code, "", "timed out / not found"))
    out_code, _, _ = mobility.safe_run_m2_script("dummy")
    assert out_code == code

    monkeypatch.setattr(fusion, "run_m2_script", lambda *a, **k: (code, "", "timed out / not found"))
    out_code, _, _ = fusion.safe_run_m2_script("dummy")
    assert out_code == code


def test_safe_run_m2_still_swallows_noisy_success(monkeypatch):
    """A non-zero code that is NOT 124/127 and has no error marker is still
    treated as success (the original WSL-noise leniency is preserved)."""
    monkeypatch.setattr(mobility, "run_m2_script", lambda *a, **k: (1, "VAL:ok", "some wsl noise"))
    out_code, _, _ = mobility.safe_run_m2_script("dummy")
    assert out_code == 0
