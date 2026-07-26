"""JSON adapter for the mt-halfspace skill."""

from __future__ import annotations

import json
import sys

from mobility_toolkit.boundary_halfspace import (
    FreeBoundaryPairingPresentation,
    HalfSpaceSemigroup,
    LaurentHalfSpaceSubmodule,
    OrientedHalfSpace,
    PrimitiveNormal,
    TangentDepthPolynomial,
    TangentDepthTerm,
    TangentLaurentPolynomial,
    TangentLaurentTerm,
    analyze_free_boundary_pairing,
    boundary_module_capability_report,
    compare_orientations,
    compile_projected_bulk_primary,
    contract_laurent_submodule,
    halfspace_capability_report,
    ruba_yang_secondary_boundary_example,
    toric3d_halfspace_capability_report,
    toric3d_z2_z_nonnegative_primary_benchmark,
    toric_z2_y_nonnegative_boundary_module,
    xcube_orientation_benchmark,
)
from mobility_toolkit.core.canonical import canonical_json


def _normal(values):
    return PrimitiveNormal.from_integer(tuple(int(value) for value in values))


def _depth_polynomial(modulus, normal, terms):
    return TangentDepthPolynomial(
        modulus,
        normal,
        (),
        tuple(
            TangentDepthTerm(
                int(term["coefficient"]),
                tuple(int(value) for value in term["tangent_exponents"]),
                int(term["depth"]),
                (),
            )
            for term in terms
        ),
    )


def _bulk(payload):
    modulus = int(payload["coefficient_modulus"])
    normal = _normal(payload["normal"])
    columns = tuple(
        tuple(
            _depth_polynomial(modulus, normal, entry)
            for entry in column
        )
        for column in payload["generator_columns"]
    )
    return LaurentHalfSpaceSubmodule(
        modulus,
        normal,
        int(payload["ambient_rank"]),
        columns,
    )


def _tangent_polynomial(modulus, rank, terms):
    return TangentLaurentPolynomial(
        modulus,
        rank,
        tuple(
            TangentLaurentTerm(
                int(term["coefficient"]),
                tuple(int(value) for value in term["exponents"]),
            )
            for term in terms
        ),
    )


def _execute(data):
    operation = data.get("operation")
    if operation == "capabilities":
        return {
            "halfspace": halfspace_capability_report(),
            "boundary_module": boundary_module_capability_report(),
            "toric3d": toric3d_halfspace_capability_report(),
        }
    if operation == "geometry":
        normal = _normal(data["normal"])
        half_space = OrientedHalfSpace(
            normal,
            int(data.get("boundary_offset", 0)),
        )
        return {
            "half_space": half_space,
            "basis_change": half_space.basis_change,
            "semigroup": HalfSpaceSemigroup.create(half_space),
        }
    if operation == "compare-orientations":
        return compare_orientations(
            _normal(data["left_normal"]),
            _normal(data["right_normal"]),
        )
    if operation in {"contract", "primary"}:
        bulk = _bulk(data["bulk"])
        contracted = contract_laurent_submodule(
            bulk,
            timeout_seconds=float(data.get("timeout_seconds", 60)),
        )
        if operation == "contract":
            return contracted
        return compile_projected_bulk_primary(bulk, contracted.value)
    if operation == "free-pairing":
        modulus = int(data["coefficient_modulus"])
        rank = int(data["tangent_rank"])
        pairing = tuple(
            tuple(
                _tangent_polynomial(modulus, rank, entry)
                for entry in row
            )
            for row in data["pairing_matrix"]
        )
        presentation = FreeBoundaryPairingPresentation(
            modulus,
            rank,
            pairing,
            tuple(data.get("generator_labels") or ()),
            str(data.get("source_scope") or "mt-halfspace JSON input"),
        )
        return analyze_free_boundary_pairing(
            presentation,
            timeout_seconds=float(data.get("timeout_seconds", 60)),
        )
    if operation == "toric2d":
        return toric_z2_y_nonnegative_boundary_module()
    if operation == "toric3d":
        return toric3d_z2_z_nonnegative_primary_benchmark()
    if operation == "secondary-example":
        return ruba_yang_secondary_boundary_example()
    if operation == "xcube":
        return xcube_orientation_benchmark(_normal(data["normal"]))
    raise ValueError(
        "operation must be capabilities, geometry, compare-orientations, "
        "contract, primary, free-pairing, toric2d, toric3d, "
        "secondary-example, or xcube"
    )


if __name__ == "__main__":
    try:
        request = json.loads(sys.stdin.read())
        print(canonical_json({"status": "success", "result": _execute(request)}))
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"{type(error).__name__}: {error}",
                },
                sort_keys=True,
            )
        )
        sys.exit(1)
