import json
import subprocess
import sys
from pathlib import Path


def test_mt_cheshire_skill_open_segment_smoke():
    script = (
        Path(__file__).parents[1]
        / "mobility_toolkit"
        / "skills"
        / "mt-cheshire"
        / "scripts"
        / "mt-cheshire.py"
    )
    request = {
        "shape": [2, 1, 1],
        "periodic_axes": [],
        "defects": [
            {
                "defect_id": "gamma",
                "topology": "open_segment",
                "cube_bases": [[0, 0, 0], [1, 0, 0]],
            }
        ],
    }
    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, payload
    assert payload["status"] == "success"
    assert payload["exactness"] == "certified_exact"
    assert payload["bulk"]["codespace_dimension"] == 1
    assert payload["local_hamiltonian"]["codespace_dimension"] == 2
    assert payload["fixed_charge_sectors"]["codespace_dimension"] == 1
    assert payload["representations"]["deleted_tube_matches_direct_line"]
    assert payload["defects"][0]["eq8_construction_verified"]
