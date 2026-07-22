"""A Macaulay2 non-zero exit status must never be rewritten as success."""
import pytest

import mobility_toolkit.mobility as mobility
import mobility_toolkit.fusion as fusion


@pytest.mark.parametrize("code", [1, 2, 124, 127])
def test_safe_run_m2_preserves_every_nonzero_code(monkeypatch, code):
    monkeypatch.setattr(mobility, "run_m2_script", lambda *a, **k: (code, "", "timed out / not found"))
    out_code, _, _ = mobility.safe_run_m2_script("dummy")
    assert out_code == code


@pytest.mark.parametrize("code", [1, 2, 124, 127])
def test_fusion_safe_run_m2_preserves_every_nonzero_code(monkeypatch, code):
    monkeypatch.setattr(fusion, "run_m2_script", lambda *a, **k: (code, "", "timed out / not found"))
    out_code, _, _ = fusion.safe_run_m2_script("dummy")
    assert out_code == code
