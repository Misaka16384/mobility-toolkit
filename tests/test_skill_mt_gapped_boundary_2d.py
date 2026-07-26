import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("flint")


SCRIPT = (
    Path(__file__).parents[1]
    / "mobility_toolkit"
    / "skills"
    / "mt-gapped-boundary-2d"
    / "scripts"
    / "mt-gapped-boundary-2d.py"
)


def _run(request):
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(request),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_skill_reports_honest_capabilities():
    result = _run({"operation": "capabilities"})
    assert result["status"] == "success"
    assert result["metric_group_condensation"] == "certified_exact"
    assert result["finite_local_completion"] == "bounded_exact"
    assert result["automatic_stabilizer_anyon_extraction"].startswith("unsupported")


def test_skill_enumerates_double_semion_lagrangian():
    result = _run({"operation": "enumerate", "model": "double-semion"})
    assert result["status"] == "success"
    assert result["exactness"] == "certified_exact"
    assert sum(item["lagrangian"] for item in result["bosonic_candidates"]) == 1
    assert result["certificate"]["lagrangian_subgroups"] == 1


@pytest.mark.parametrize("model", ("z2-toric", "z4-toric"))
@pytest.mark.parametrize("boundary_kind", ("rough", "smooth"))
def test_skill_runs_source_locked_toric_completion(model, boundary_kind):
    result = _run(
        {
            "operation": "completion-benchmark",
            "model": model,
            "boundary_kind": boundary_kind,
        }
    )
    modulus = 2 if model == "z2-toric" else 4
    assert result["status"] == "success"
    assert result["exactness"] == "bounded_exact"
    assert result["fusion_invariant_factors"] == [modulus, modulus]
    assert result["condensate_invariant_factors"] == [modulus]
    assert result["verification"]["short_string_termination_verified"]


def test_skill_parses_and_verifies_explicit_uniform_composite_completion():
    result = _run(
        {
            "operation": "verify-completion",
            "model": "z4-toric",
            "sites": [
                {
                    "site_id": "remote",
                    "dimension": 4,
                    "coordinate": [0, 0],
                    "depth": 1,
                },
                {
                    "site_id": "boundary",
                    "dimension": 4,
                    "coordinate": [1, 0],
                    "depth": 0,
                },
            ],
            "bulk_terms": [
                {
                    "term_id": "bulk:remote",
                    "terms": [{"site_id": "remote", "x": 1}],
                }
            ],
            "boundary_terms": [
                {
                    "term_id": "boundary:pin",
                    "terms": [{"site_id": "boundary", "z": 1}],
                }
            ],
            "string_lifts": [
                {
                    "label": "electric",
                    "anyon": [1, 0],
                    "operator": {
                        "terms": [{"site_id": "remote", "z": 1}]
                    },
                    "remote_excitation_term_ids": ["bulk:remote"],
                }
            ],
            "locality": {
                "window_label": "explicit-z4-two-site-test",
                "boundary_site_ids": ["boundary"],
                "max_completion_depth": 1,
                "max_boundary_term_sites": 1,
                "max_boundary_term_diameter": 0,
                "max_short_string_sites": 1,
            },
            "source_scope": "explicit parser regression",
        }
    )
    assert result["status"] == "success"
    assert result["exactness"] == "bounded_exact"
    assert result["codespace_dimension"] == 1
    assert result["termination"][0]["exact_remote_syndrome_verified"]
