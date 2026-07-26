"""JSON adapter for bounded 3D boundary candidate enumeration."""

from __future__ import annotations

import json
import sys

from mobility_toolkit.boundary.enumeration.symbolic3d import (
    Symbolic3DBudget,
    Symbolic3DEquivalence,
    Symbolic3DSearchRequest,
    enumerate_symbolic3d_candidates,
    toric3d_primary_symbolic_crosscheck,
    xcube_symbolic_orientation_crosscheck,
)
from mobility_toolkit.boundary_halfspace import (
    FreeBoundaryPairingPresentation,
    PrimitiveNormal,
    TangentLaurentPolynomial,
    TangentLaurentTerm,
)
from mobility_toolkit.core.canonical import canonical_json


def _normal(values):
    return PrimitiveNormal.from_integer(tuple(int(value) for value in values))


def _polynomial(modulus, terms):
    return TangentLaurentPolynomial(
        modulus,
        2,
        tuple(
            TangentLaurentTerm(
                int(term["coefficient"]),
                tuple(int(value) for value in term["exponents"]),
            )
            for term in terms
        ),
    )


def _symbolic(data):
    if data.get("full_boundary_module_supplied") is not True:
        raise ValueError(
            "symbolic E3 requires full_boundary_module_supplied=true; "
            "primary-only input is insufficient"
        )
    modulus = int(data["coefficient_modulus"])
    pairing = tuple(
        tuple(_polynomial(modulus, entry) for entry in row)
        for row in data["pairing_matrix"]
    )
    presentation = FreeBoundaryPairingPresentation(
        coefficient_modulus=modulus,
        tangent_rank=2,
        pairing_matrix=pairing,
        generator_labels=tuple(data.get("generator_labels") or ()),
        source_scope=str(
            data.get("source_scope")
            or "caller asserted full free boundary module"
        ),
    )
    request = Symbolic3DSearchRequest(
        presentation=presentation,
        boundary_normal=_normal(data["normal"]),
        exponent_bounds=tuple(
            tuple(int(value) for value in pair)
            for pair in data["exponent_bounds"]
        ),
        max_generators=int(data["max_generators"]),
        equivalence=Symbolic3DEquivalence(
            data.get("equivalence", "raw_constant_generator_change")
        ),
        include_zero_submodule=bool(data.get("include_zero_submodule", False)),
    )
    budget_data = data.get("budget") or {}
    budget = Symbolic3DBudget(
        max_seed_presentations=int(
            budget_data.get("max_seed_presentations", 100_000)
        ),
        max_output_candidates=int(
            budget_data.get("max_output_candidates", 10_000)
        ),
    )
    max_pages = int(data.get("max_pages", 1))
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    checkpoint = None
    pages = []
    candidates = []
    for _ in range(max_pages):
        result = enumerate_symbolic3d_candidates(
            request,
            budget,
            checkpoint=checkpoint,
        )
        pages.append(result)
        candidates.extend(result.value.candidates)
        checkpoint = result.value.checkpoint
        if checkpoint is None:
            break
    final = pages[-1]
    return {
        "candidate_hashes": tuple(item.candidate_hash for item in candidates),
        "candidates": tuple(candidates),
        "exactness": final.exactness,
        "final_certificate": final.value.certificate,
        "next_checkpoint": checkpoint,
        "page_count": len(pages),
        "theorem_scope": final.theorem_scope,
        "warnings": final.warnings,
    }


def _execute(data):
    operation = data.get("operation", "capabilities")
    if operation == "capabilities":
        return {
            "e1_finite_isotropic_subgroups": "certified_exact_after_exhaustion",
            "e2_translation_compatible_submodules":
                "bounded_exact_after_exhaustion",
            "e2_ancillas": "unsupported",
            "e2_local_completions": "unsupported",
            "e3_bounded_seed_presentations":
                "bounded_exact_after_exhaustion",
            "e3_saturation": "unsupported",
            "e3_anomaly_and_completion": "unsupported",
            "e3_thermodynamic_classification": "unsupported",
            "implemented_e3_equivalences": (
                "raw_constant_generator_change",
                "raw_plus_common_tangent_translation",
            ),
        }
    if operation == "symbolic":
        return _symbolic(data)
    if operation == "toric3d-primary-preflight":
        return toric3d_primary_symbolic_crosscheck()
    if operation == "xcube-preflight":
        return xcube_symbolic_orientation_crosscheck(_normal(data["normal"]))
    raise ValueError(
        "operation must be capabilities, symbolic, "
        "toric3d-primary-preflight, or xcube-preflight"
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
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        sys.exit(1)
