import json
import subprocess
import sys
from pathlib import Path


def _script():
    return (
        Path(__file__).parents[1]
        / "mobility_toolkit"
        / "skills"
        / "mt-cheshire"
        / "scripts"
        / "mt-cheshire.py"
    )


def _run(request, timeout=180):
    completed = subprocess.run(
        [sys.executable, str(_script())],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    return payload


def test_mt_cheshire_skill_open_segment_smoke():
    request = {
        "operation": "defects.cheshire.toric3d_finite_reference",
        "input_data": {
            "shape": [2, 1, 1],
            "periodic_axes": [],
            "defects": [
                {
                    "defect_id": "gamma",
                    "topology": "open_segment",
                    "cube_bases": [[0, 0, 0], [1, 0, 0]],
                }
            ],
        },
        "requested_certificate_level": "standard",
    }
    payload = _run(request)
    assert payload["schema"] == "mobility_toolkit.service_execution.v1"
    result = payload["result"]
    value = result["value"]
    assert result["operation"] == "defects.cheshire.toric3d_finite_reference"
    assert result["exactness"] == "certified_exact"
    assert value["bulk_analysis"]["codespace_dimension"] == 1
    assert value["local_analysis"]["codespace_dimension"] == 2
    assert value["fixed_sector_analysis"]["codespace_dimension"] == 1
    assert value["pinned_elimination_certificate"]["verified"]
    transformation = value["defect_reports"][0]["transformation_certificate"]
    assert transformation["product_identity_verified"]
    assert transformation["local_commutation_verified"]


def test_mt_cheshire_v2_capabilities_separate_static_and_dynamic_scope():
    payload = _run(
        {
            "operation": "defects.cheshire.capabilities",
            "input_data": {},
        },
        timeout=30,
    )
    capabilities = payload["result"]["value"]

    assert capabilities["api_version"] == "2"
    operations = capabilities["operations"]
    assert (
        operations["defects.cheshire.toric2d_reference"]["classification"]
        == "computed_exact_six_oriented_morita_species"
    )
    assert (
        operations["defects.cheshire.xcube_candidates"][
            "classification_complete"
        ]
        is False
    )
    assert capabilities["fracton_evidence_ladder"][-1] == (
        "circuit_certified_cheshire"
    )


def test_mt_cheshire_v2_xcube_candidates_are_support_level_only():
    payload = _run(
        {
            "operation": "defects.cheshire.xcube_candidates",
            "input_data": {
                "axis": "z",
            },
            "requested_certificate_level": "full",
        },
        timeout=60,
    )

    result = payload["result"]
    assert result["exactness"] == "experimental"
    value = result["value"]
    assert len(value["candidates"]) == 58
    assert value["support_search_complete"]
    assert value["classification_complete"] is False
    assert {
        item["evidence_tier"] for item in value["candidates"]
    } == {"support_candidate"}
    assert value["equivalence_summary"]["cubic_symmetry_orbit_count"] == 41


def test_mt_cheshire_v2_xcube_static_upgrade_replays_local_lineon_completion():
    payload = _run(
        {
            "operation": "defects.cheshire.xcube_candidates",
            "input_data": {
                "axis": "z",
                "include_finite_static_reference": True,
                "finite_reference_line_length": 1,
            },
            "requested_certificate_level": "full",
        },
        timeout=60,
    )

    result = payload["result"]
    value = result["value"]
    assert sum(
        item["evidence_tier"] == "static_cheshire_candidate"
        for item in value["candidates"]
    ) == 1
    reference = value["finite_static_reference"]["value"]
    certificate = reference["certificate"]
    assert certificate["verified"]
    assert certificate["removed_lineon_sector_only"]
    assert certificate["added_condensation_present"]
    assert certificate["added_condensation_commutes"]
    assert certificate["rank_deficit_relative_to_bulk"] == 1
    assert certificate["hidden_charge_commutes"]
    assert certificate["hidden_charge_independent"]
    assert certificate["hidden_charge_restores_bulk_rank"]
    assert reference["local_algebra"]["invariant_factors"] == []


def test_mt_cheshire_v2_complete_toric_reference_and_ordered_fusion():
    reference = _run(
        {
            "schema_version": "2",
            "operation": "defects.cheshire.toric2d_reference",
            "input_data": {},
            "equivalence_relation": "oriented_morita",
            "requested_certificate_level": "full",
        }
    )["result"]["value"]
    classification = reference["classification"]
    assert classification["certificate"]["classification_complete"]
    assert [
        item["species_id"] for item in classification["species"]
    ] == ["1", "S_e", "S_m", "S_psi", "S_em", "S_me"]
    assert len(reference["ordered_fusion_table"]) == 36

    forward = _run(
        {
            "operation": "defects.cheshire.fuse",
            "input_data": {
                "left_species_id": "S_em",
                "right_species_id": "S_me",
            },
            "requested_certificate_level": "full",
        }
    )["result"]["value"]
    reverse = _run(
        {
            "operation": "defects.cheshire.fuse",
            "input_data": {
                "left_species_id": "S_me",
                "right_species_id": "S_em",
            },
            "requested_certificate_level": "full",
        }
    )["result"]["value"]
    assert forward["terms"][0]["output_species_id"] == "S_e"
    assert reverse["terms"][0]["output_species_id"] == "S_m"
    assert not forward["terms"][0]["coefficient"]["numeric_scalar"]


def test_mt_cheshire_v2_lattice_and_creation_circuit_smoke():
    realization = _run(
        {
            "operation": "defects.cheshire.realize_toric2d",
            "input_data": {
                "species_id": "S_e",
                "line_length_lattice_steps": 2,
            },
            "requested_certificate_level": "full",
        }
    )["result"]["value"]
    assert realization["certificate"]["verified"]
    assert realization["tikz"].startswith("\\begin{tikzpicture}")

    circuit = _run(
        {
            "operation": "defects.cheshire.circuit_toric2d",
            "input_data": {
                "process": "creation",
                "left_species_id": "S_e",
                "line_length_lattice_steps": 3,
            },
            "requested_certificate_level": "full",
        }
    )["result"]["value"]
    assert circuit["certificate"]["exact_pauli_conjugation_verified"]
    assert circuit["circuit"]["provenance_kind"] == "source_locked"
