import json
import sys

from mobility_toolkit.anyons2d import (
    CondensateEnumerationBudget,
    FiniteMetricGroup,
    color_code_metric_model,
    double_semion_metric_model,
    enumerate_condensates,
    fish_toric_metric_model,
    fold_metric_groups,
    zd_toric_metric_model,
)
from mobility_toolkit.completion2d import (
    CondensateStringLift,
    FiniteBoundaryLocalityDomain,
    LocalBoundaryCompletionRequest,
    NamedPauliTerm,
    verify_local_boundary_completion,
    zd_toric_cut_completion_benchmark,
)
from mobility_toolkit.core import LocalPauliTerm, PauliModule, SparseIntMatrix, canonicalize
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


def _model(name, backend):
    models = {
        "z2-toric": lambda: zd_toric_metric_model(2, backend),
        "z4-toric": lambda: zd_toric_metric_model(4, backend),
        "double-semion": lambda: double_semion_metric_model(backend),
        "color-code": lambda: color_code_metric_model(backend),
        "fish-toric": lambda: fish_toric_metric_model(backend),
    }
    if name not in models:
        raise ValueError(f"unknown model: {name}")
    return models[name]()


def _metric(data, backend):
    if "model" in data:
        return _model(data["model"], backend).metric
    spec = data["metric"]
    group = FiniteAbelianGroup.from_coordinate_orders(
        tuple(spec["orders"]),
        backend,
        tuple(spec.get("labels", ())),
    )
    return FiniteMetricGroup.create(
        group,
        spec["phase_modulus"],
        SparseIntMatrix.from_rows(tuple(tuple(row) for row in spec["braiding_rows"])),
        tuple(spec["generator_spins"]),
        backend,
    )


def _operator(module, data):
    return module.operator(
        tuple(
            LocalPauliTerm.cyclic(
                item["site_id"],
                x=item.get("x", 0),
                z=item.get("z", 0),
            )
            for item in data.get("terms", ())
        ),
        phase=data.get("phase", 0),
    )


def _named_terms(module, items):
    return tuple(
        NamedPauliTerm(item["term_id"], _operator(module, item))
        for item in items
    )


def _completion_request(data, backend):
    sites = tuple(data["sites"])
    dimensions = tuple(item["dimension"] for item in sites)
    if len(set(dimensions)) != 1:
        raise ValueError("verify-completion currently supports uniform cyclic site dimensions")
    module = PauliModule.from_dimensions(
        dimensions, tuple(item["site_id"] for item in sites)
    )
    locality_data = data["locality"]
    locality = FiniteBoundaryLocalityDomain(
        window_label=locality_data["window_label"],
        site_coordinates=tuple(
            (item["site_id"], tuple(item["coordinate"])) for item in sites
        ),
        boundary_site_ids=tuple(locality_data["boundary_site_ids"]),
        site_depths=tuple(
            (item["site_id"], item["depth"]) for item in sites
        ),
        max_completion_depth=locality_data["max_completion_depth"],
        max_boundary_term_sites=locality_data["max_boundary_term_sites"],
        max_boundary_term_diameter=locality_data["max_boundary_term_diameter"],
        max_short_string_sites=locality_data["max_short_string_sites"],
    )
    lifts = tuple(
        CondensateStringLift(
            item["label"],
            tuple(item["anyon"]),
            _operator(module, item["operator"]),
            tuple(item["remote_excitation_term_ids"]),
        )
        for item in data["string_lifts"]
    )
    return LocalBoundaryCompletionRequest(
        metric=_metric(data, backend),
        pauli_module=module,
        bulk_terms=_named_terms(module, data["bulk_terms"]),
        boundary_terms=_named_terms(module, data["boundary_terms"]),
        string_lifts=lifts,
        locality_domain=locality,
        source_scope=data["source_scope"],
        assumptions=tuple(data.get("assumptions", ())),
    )


def _metric_report(metric, backend):
    order = metric.group.order(backend)
    exponent = metric.group.invariant_factors[-1] if metric.group.invariant_factors else 1
    max_table = 256
    table_complete = order <= max_table
    elements = []
    if table_complete:
        representatives = []
        trivial = metric.group.trivial_subgroup(backend)
        rank = metric.group.presentation_rank
        for index in range(exponent ** rank):
            value = []
            remaining = index
            for _ in range(rank):
                value.append(remaining % exponent)
                remaining //= exponent
            vector = tuple(value)
            if not any(
                trivial.contains(
                    tuple(left - right for left, right in zip(vector, previous)),
                    backend,
                )
                for previous in representatives
            ):
                representatives.append(vector)
                elements.append(
                    {
                        "representative": list(vector),
                        "spin_exponent": metric.spin_exponent(vector),
                    }
                )
            if len(elements) >= order:
                break
    return {
        "fusion_invariant_factors": list(metric.group.invariant_factors),
        "group_order": order,
        "phase_modulus": metric.phase_modulus,
        "generator_spins": list(metric.generator_spins),
        "braiding_matrix": canonicalize(metric.braiding_matrix),
        "nondegenerate": metric.certificate.nondegenerate,
        "representative_spin_table": elements if table_complete else None,
        "table_complete": table_complete,
        "metric": canonicalize(metric),
    }


def _enumerate(data, metric, backend):
    budget_data = data.get("budget", {})
    budget = CondensateEnumerationBudget(
        max_work_units=budget_data.get("max_work_units", 500_000),
        max_results=budget_data.get("max_results", 100_000),
        max_elements=budget_data.get("max_elements", 4096),
        max_subgroups=budget_data.get("max_subgroups", 500_000),
    )
    max_pages = data.get("max_pages", 1000)
    checkpoint = None
    candidates = []
    certificate = None
    for _ in range(max_pages):
        page = enumerate_condensates(metric, backend, budget, checkpoint)
        candidates.extend(page.candidates)
        certificate = page.certificate
        checkpoint = page.checkpoint
        if checkpoint is None:
            break
    return {
        "exactness": certificate.exactness.value,
        "search_domain": canonicalize(page.domain),
        "certificate": canonicalize(certificate),
        "checkpoint": canonicalize(checkpoint),
        "bosonic_candidates": [
            {
                "generator_vectors": [list(vector) for vector in item.generator_vectors],
                "invariant_factors": list(item.invariant_factors),
                "lagrangian": item.lagrangian,
                "order": item.order,
            }
            for item in candidates
        ],
    }


def _run(data):
    backend = FlintIntegerBackend()
    operation = data.get("operation", "capabilities")
    if operation == "capabilities":
        return {
            "status": "success",
            "operations": [
                "metric",
                "enumerate",
                "fold",
                "completion-benchmark",
                "verify-completion",
                "capabilities",
            ],
            "automatic_stabilizer_anyon_extraction": "unsupported without explicit saturation/short-string certificate",
            "metric_group_condensation": "certified_exact",
            "finite_local_completion": "bounded_exact",
            "coefficients": "uniform prime and composite cyclic Pauli sites",
            "thermodynamic_gap_proof": "not inferred from finite completion",
        }
    if operation == "completion-benchmark":
        model = data["model"]
        if model not in {"z2-toric", "z4-toric"}:
            raise ValueError("completion-benchmark supports z2-toric or z4-toric")
        modulus = 2 if model == "z2-toric" else 4
        benchmark = zd_toric_cut_completion_benchmark(
            modulus, data["boundary_kind"], backend
        )
        result = verify_local_boundary_completion(benchmark.request, backend)
    elif operation == "verify-completion":
        result = verify_local_boundary_completion(
            _completion_request(data, backend), backend
        )
    else:
        metric = _metric(data, backend)
        if operation == "metric":
            return {"status": "success", "operation": operation, **_metric_report(metric, backend)}
        if operation == "enumerate":
            return {"status": "success", "operation": operation, **_enumerate(data, metric, backend)}
        if operation == "fold":
            right = _metric(data["right"], backend)
            folded = fold_metric_groups(metric, right, backend)
            return {
                "status": "success",
                "operation": operation,
                "second_form_reversed": folded.second_form_reversed,
                "folded_metric": canonicalize(folded),
            }
        raise ValueError(f"unknown operation: {operation}")

    output = {
        "status": "success",
        "operation": operation,
        "exactness": result.exactness.value,
        "canonical_input_hash": result.canonical_input_hash,
        "theorem_scope": result.theorem_scope,
        "warnings": list(result.warnings),
        "fusion_invariant_factors": list(
            result.value.anyon_fusion_invariant_factors
        ),
        "condensate_invariant_factors": list(
            result.value.condensate_invariant_factors
        ),
        "codespace_dimension": result.value.codespace_dimension,
        "boundary_logical_invariant_factors": list(
            result.value.boundary_logical_invariant_factors
        ),
        "verification": dict(result.verification),
        "termination": [
            canonicalize(item)
            for item in result.value.certificate.termination_witnesses
        ],
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
