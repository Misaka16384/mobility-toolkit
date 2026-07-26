"""JSON adapter for finite static Cheshire analysis and bounded synthesis."""

from __future__ import annotations

import json
import sys
from dataclasses import replace

from mobility_toolkit.core import canonicalize
from mobility_toolkit.defects.cheshire import (
    ClosedLoop,
    LineTopology,
    OpenSegment,
    analyze_toric_cheshire,
    cheshire_scaling_sample,
)
from mobility_toolkit.defects.cheshire_fusion import (
    CheshireDefectNetwork,
    CheshireNetworkEdge,
    CheshireNetworkNode,
    EndpointBinding,
    NetworkNodeKind,
    construct_static_toric_cheshire_fusion,
)
from mobility_toolkit.defects.cheshire_synthesis import (
    enumerate_cheshire_species,
    synthesize_tubular_to_line,
    toric_cheshire_condensation_candidate,
)
from mobility_toolkit.defects.fracton_cheshire import (
    analyze_xcube_fracton_line_reference,
    xcube_axial_line_reference_request,
)
from mobility_toolkit.boundary_halfspace import PrimitiveNormal
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import rectangular_cubical_complex


def _defects(complex_, items):
    result = []
    for item in items:
        arguments = (
            complex_,
            item["defect_id"],
            tuple(tuple(base) for base in item["cube_bases"]),
        )
        topology = item["topology"]
        if topology == "open_segment":
            result.append(OpenSegment.from_cube_bases(*arguments))
        elif topology == "closed_loop":
            result.append(ClosedLoop.from_cube_bases(*arguments))
        else:
            raise ValueError("topology must be open_segment or closed_loop")
    if not result:
        raise ValueError("at least one defect is required")
    return tuple(result)


def _complex(data):
    shape = tuple(data["shape"])
    if len(shape) != 3:
        raise ValueError("shape must contain exactly three positive lengths")
    return rectangular_cubical_complex(
        shape, periodic_axes=tuple(data.get("periodic_axes", ()))
    )


def _network(spec):
    if spec is None:
        return None
    nodes = tuple(
        CheshireNetworkNode(
            item["node_id"],
            NetworkNodeKind(item["kind"]),
            tuple(item["stratum_cell_ids"]),
            tuple(
                EndpointBinding(binding["defect_id"], binding["cube_cell_id"])
                for binding in item["endpoint_bindings"]
            ),
        )
        for item in spec["nodes"]
    )
    edges = tuple(
        CheshireNetworkEdge(
            item["edge_id"],
            item["defect_id"],
            LineTopology(item["topology"]),
            tuple(item["incident_node_ids"]),
        )
        for item in spec["edges"]
    )
    return CheshireDefectNetwork(
        nodes,
        edges,
        str(spec.get("provenance") or "mt-cheshire explicit network input"),
    )


def _defect_summary(report):
    charge = report.charge_termination
    magnetic = report.magnetic_termination
    return {
        "defect_id": report.line_defect.defect_id,
        "topology": report.line_defect.topology.value,
        "cube_cell_ids": list(report.line_defect.cube_cell_ids),
        "condensate_plaquette_ids": list(
            report.line_defect.condensate_plaquette_ids
        ),
        "endpoint_cube_ids": list(report.line_defect.endpoint_cube_ids),
        "tube": {
            "radius_lattice_steps": report.tube.radius_lattice_steps,
            "support_site_count": len(report.tube.tube_site_ids),
            "wall_site_count": len(report.tube.tube_wall_site_ids),
        },
        "defect_local_algebra": {
            "invariant_factors": list(
                report.defect_local_algebra.invariant_factors
            ),
            "radical_invariant_factors": list(
                report.defect_local_algebra.radical_invariant_factors
            ),
            "order": report.defect_local_algebra.order,
        },
        "charge_termination": {
            "terminates_on_defect": charge.terminates_on_defect,
            "changes_fixed_sector": charge.changes_fixed_sector,
            "absorbed_bulk_term_ids": list(charge.absorbed_bulk_term_ids),
            "residual_bulk_term_ids": list(charge.residual_bulk_term_ids),
            "probe_id": charge.probe_id,
        },
        "magnetic_termination": {
            "terminates_on_defect": magnetic.terminates_on_defect,
            "conclusion_basis": magnetic.conclusion_basis,
            "no_solution_verified": (
                magnetic.no_solution_certificate is not None
                and magnetic.no_solution_certificate.verified
            ),
            "probe_id": magnetic.probe_id,
        },
        "eq8_construction_verified": (
            report.transformation_certificate.product_identity_verified
            and report.transformation_certificate.local_commutation_verified
        ),
    }


def _static(data, backend):
    complex_ = _complex(data)
    defects = _defects(complex_, data["defects"])
    result = analyze_toric_cheshire(
        complex_,
        defects,
        backend,
        tube_radius_lattice_steps=data.get("tube_radius_lattice_steps", 0),
    )
    samples = [
        cheshire_scaling_sample(report.line_defect.defect_id, result, index)
        for index, report in enumerate(result.defect_reports)
    ]
    output = {
        "operation": "static",
        "exactness": result.exactness.value,
        "certificate_level": result.certificate_level.value,
        "theorem_scope": result.theorem_scope,
        "backend_provenance": canonicalize(result.backend_provenance),
        "bulk": {
            "codespace_dimension": result.bulk_analysis.codespace_dimension,
            "logical_invariant_factors": list(
                result.bulk_analysis.logical_invariant_factors
            ),
        },
        "local_hamiltonian": {
            "codespace_dimension": result.local_analysis.codespace_dimension,
            "logical_invariant_factors": list(
                result.local_analysis.logical_invariant_factors
            ),
            "gsd_factor": canonicalize(result.local_gsd_factor),
        },
        "fixed_charge_sectors": {
            "sector_eigenvalue_convention": "+1 stabilizer eigenspace",
            "codespace_dimension": result.fixed_sector_analysis.codespace_dimension,
            "logical_invariant_factors": list(
                result.fixed_sector_analysis.logical_invariant_factors
            ),
            "gsd_factor": canonicalize(result.fixed_sector_gsd_factor),
        },
        "representations": {
            "pinned_condensate_elimination_verified": (
                result.pinned_elimination_certificate.verified
            ),
            "deleted_tube_matches_direct_line": (
                result.tubular_deleted_representation.certificate.verified
            ),
            "equivalence_scope": (
                result.tubular_deleted_representation.certificate.equivalence_scope
            ),
        },
        "defects": [_defect_summary(report) for report in result.defect_reports],
        "finite_scaling_samples": [canonicalize(sample) for sample in samples],
    }
    if data.get("include_full_result", False):
        output["full_result"] = canonicalize(result)
    return output


def _synthesis_summary(result):
    return {
        "candidate_id": result.candidate_id,
        "exactness": result.exactness.value,
        "theorem_scope": result.theorem_scope,
        "finite_invariants_preserved": result.finite_invariants_preserved,
        "circuit_constructed": result.circuit_constructed,
        "phase_equivalence_claimed": result.phase_equivalence_claimed,
        "snapshots": canonicalize(result.snapshots),
        "step_certificates": canonicalize(result.step_certificates),
        "adjacent_certificates": canonicalize(result.adjacent_certificates),
        "transcript_hash": result.transcript_hash,
    }


def _synthesize(data, backend):
    complex_ = _complex(data)
    defects = _defects(complex_, data["defects"])
    candidate = toric_cheshire_condensation_candidate(
        complex_, defects, backend, data.get("candidate_id")
    )
    result = synthesize_tubular_to_line(candidate, tuple(data["radii"]))
    output = {"operation": "synthesize-toric", **_synthesis_summary(result)}
    if data.get("include_full_result", False):
        output["full_result"] = canonicalize(result)
    return output


def _enumerate(data, backend):
    complex_ = _complex(data)
    candidates = tuple(
        toric_cheshire_condensation_candidate(
            complex_,
            _defects(complex_, item["defects"]),
            backend,
            item["candidate_id"],
        )
        for item in data["candidate_sets"]
    )
    result = enumerate_cheshire_species(candidates, tuple(data["radii"]))
    output = {
        "operation": "enumerate-toric",
        "search_certificate": canonicalize(result.certificate),
        "syntheses": [_synthesis_summary(item) for item in result.syntheses],
    }
    if data.get("include_full_result", False):
        output["full_result"] = canonicalize(result)
    return output


def _fusion(data, backend):
    complex_ = _complex(data)
    before = _defects(complex_, data["before_defects"])
    after = _defects(complex_, data["after_defects"])
    result = construct_static_toric_cheshire_fusion(
        data["fusion_id"],
        complex_,
        before,
        after,
        backend,
        tube_radius_lattice_steps=int(
            data.get("tube_radius_lattice_steps", 0)
        ),
        before_network=_network(data.get("before_network")),
        after_network=_network(data.get("after_network")),
    )
    output = {
        "operation": "fusion-toric",
        "exactness": result.static_candidate_exactness.value,
        "certificate_level": result.certificate_level.value,
        "theorem_scope": result.theorem_scope,
        "finite_depth_circuit": canonicalize(result.finite_depth_circuit),
        "junction_completion_scope": result.junction_completion_scope,
        "logical_counting": canonicalize(result.logical_counting),
        "local_hamiltonian_delta": canonicalize(
            result.local_hamiltonian_delta
        ),
        "fixed_sector_hamiltonian_delta": canonicalize(
            result.fixed_sector_hamiltonian_delta
        ),
        "defect_algebra_and_termination": canonicalize(
            result.defect_algebra_and_termination
        ),
        "certificate": canonicalize(result.certificate),
    }
    if data.get("include_full_result", False):
        output["full_result"] = canonicalize(result)
    return output


def _fracton(data, backend):
    request = xcube_axial_line_reference_request(
        int(data.get("line_length_lattice_steps", 1))
    )
    if "normal" in data:
        request = replace(
            request,
            normal=PrimitiveNormal.from_integer(
                tuple(int(value) for value in data["normal"])
            ),
        )
    result = analyze_xcube_fracton_line_reference(request, backend)
    return {
        "operation": "fracton-reference",
        "result": canonicalize(result),
    }


def _capabilities():
    return {
        "operation": "capabilities",
        "static_toric_open_closed": "certified_exact_finite",
        "tubular_to_line": "bounded_exact_for_supplied_finite_radii",
        "species_enumeration": "bounded_complete_only_for_supplied_candidate_list",
        "static_fusion": "certified_exact_before_after_finite_candidate",
        "junction_network": "incidence_and_strata_only",
        "xcube_axial_reference": "experimental_candidate_with_exact_finite_data",
        "finite_depth_circuit": "unsupported",
        "phase_equivalence": "unsupported",
        "thermodynamic_completeness": "unsupported",
    }


def _run(data):
    backend = FlintIntegerBackend()
    operation = data.get("operation", "static")
    if operation == "capabilities":
        result = _capabilities()
    elif operation == "static":
        result = _static(data, backend)
    elif operation == "synthesize-toric":
        result = _synthesize(data, backend)
    elif operation == "enumerate-toric":
        result = _enumerate(data, backend)
    elif operation == "fusion-toric":
        result = _fusion(data, backend)
    elif operation == "fracton-reference":
        result = _fracton(data, backend)
    else:
        raise ValueError(
            "operation must be capabilities, static, synthesize-toric, "
            "enumerate-toric, fusion-toric, or fracton-reference"
        )
    return {"status": "success", **result}


if __name__ == "__main__":
    try:
        request = json.loads(sys.stdin.read())
        print(json.dumps(_run(request), ensure_ascii=False, sort_keys=True))
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        sys.exit(1)
