import json
import sys

from mobility_toolkit.core import canonicalize
from mobility_toolkit.defects import (
    ClosedLoop,
    OpenSegment,
    analyze_toric_cheshire,
    cheshire_scaling_sample,
)
from mobility_toolkit.finite import FlintIntegerBackend
from mobility_toolkit.geometry import rectangular_cubical_complex


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


def _run(data):
    shape = tuple(data["shape"])
    if len(shape) != 3:
        raise ValueError("shape must contain exactly three positive lengths")
    periodic_axes = tuple(data.get("periodic_axes", ()))
    complex_ = rectangular_cubical_complex(shape, periodic_axes=periodic_axes)
    defects = []
    for item in data["defects"]:
        topology = item["topology"]
        arguments = (
            complex_,
            item["defect_id"],
            tuple(tuple(base) for base in item["cube_bases"]),
        )
        if topology == "open_segment":
            defects.append(OpenSegment.from_cube_bases(*arguments))
        elif topology == "closed_loop":
            defects.append(ClosedLoop.from_cube_bases(*arguments))
        else:
            raise ValueError("topology must be open_segment or closed_loop")
    backend = FlintIntegerBackend()
    result = analyze_toric_cheshire(
        complex_,
        tuple(defects),
        backend,
        tube_radius_lattice_steps=data.get("tube_radius_lattice_steps", 0),
    )
    samples = [
        cheshire_scaling_sample(report.line_defect.defect_id, result, index)
        for index, report in enumerate(result.defect_reports)
    ]
    output = {
        "status": "success",
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
