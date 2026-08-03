"""Canonical service handlers for retained boundary and defect use cases.

This module owns all JSON-to-domain decoding for the four retained user-facing
skills.  The skills themselves are deliberately transport-only shims.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping, Optional, Tuple

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    LocalPauliTerm,
    PauliModule,
    SparseIntMatrix,
    canonical_hash,
)
from mobility_toolkit.services.contracts import ServiceRequest


SERVICE_HANDLER_VERSION = "2"


def _input_object(request: ServiceRequest) -> Mapping[str, Any]:
    if not isinstance(request.input_data, Mapping):
        raise TypeError("operation input_data must be a JSON object")
    return request.input_data


def _finite_backend(data: Mapping[str, Any]):
    from mobility_toolkit.finite import FlintIntegerBackend

    return FlintIntegerBackend(
        max_dense_entries=int(data.get("max_dense_entries", 2_000_000))
    )


def _native_result(
    request: ServiceRequest,
    source: ComputationResult,
    *,
    value: Any = None,
) -> ComputationResult:
    """Rebind a native result to the canonical public request identity."""

    actual_value = source.value if value is None else value
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=actual_value,
        exactness=source.exactness,
        assumptions=request.assumptions,
        theorem_scope=source.theorem_scope,
        certificate_level=source.certificate_level,
        certificate=source.certificate,
        verification=tuple(source.verification)
        + (
            ("source_assumptions", source.assumptions),
            ("source_input_hash", source.canonical_input_hash),
            ("source_operation", source.operation),
        ),
        backend_provenance=source.backend_provenance,
        resource_usage=source.resource_usage,
        diagnostics=source.diagnostics,
        warnings=source.warnings,
        schema_version=request.schema_version,
    )


def _contract_result(
    request: ServiceRequest,
    value: Any,
    *,
    exactness: Exactness,
    theorem_scope: str,
    certificate_level: CertificateLevel,
    certificate: Any,
    verification: Tuple[Tuple[str, Any], ...],
    backend: BackendProvenance,
    warnings: Tuple[str, ...] = (),
    diagnostics: Tuple[str, ...] = (),
    resource_usage: Tuple[Tuple[str, Any], ...] = (),
) -> ComputationResult:
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=value,
        exactness=exactness,
        assumptions=request.assumptions,
        theorem_scope=theorem_scope,
        certificate_level=certificate_level,
        certificate=certificate,
        verification=verification,
        backend_provenance=backend,
        warnings=warnings,
        diagnostics=diagnostics,
        resource_usage=resource_usage,
        schema_version=request.schema_version,
    )


def _capability_result(
    request: ServiceRequest,
    value: Any,
    algorithm: str,
    theorem_scope: str,
) -> ComputationResult:
    return _contract_result(
        request,
        value,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=theorem_scope,
        certificate_level=CertificateLevel.STANDARD,
        certificate=value,
        verification=(("capability_contract_constructed", True),),
        backend=BackendProvenance(
            "internal-contract", algorithm, SERVICE_HANDLER_VERSION
        ),
    )


# ---------------------------------------------------------------------------
# Oriented Laurent half-spaces


def _normal(values):
    from mobility_toolkit.boundary_halfspace import PrimitiveNormal

    return PrimitiveNormal.from_integer(tuple(int(value) for value in values))


def _depth_polynomial(modulus, normal, terms):
    from mobility_toolkit.boundary_halfspace import (
        TangentDepthPolynomial,
        TangentDepthTerm,
    )

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


def _bulk_submodule(payload):
    from mobility_toolkit.boundary_halfspace import LaurentHalfSpaceSubmodule

    modulus = int(payload["coefficient_modulus"])
    normal = _normal(payload["normal"])
    columns = tuple(
        tuple(_depth_polynomial(modulus, normal, entry) for entry in column)
        for column in payload["generator_columns"]
    )
    return LaurentHalfSpaceSubmodule(
        modulus,
        normal,
        int(payload["ambient_rank"]),
        columns,
    )


def _tangent_polynomial(modulus, rank, terms):
    from mobility_toolkit.boundary_halfspace import (
        TangentLaurentPolynomial,
        TangentLaurentTerm,
    )

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


def halfspace_capabilities(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        boundary_module_capability_report,
        halfspace_capability_report,
        toric3d_halfspace_capability_report,
    )

    value = {
        "halfspace": halfspace_capability_report(),
        "boundary_module": boundary_module_capability_report(),
        "toric3d": toric3d_halfspace_capability_report(),
    }
    return _capability_result(
        request,
        value,
        "halfspace-capabilities",
        "Software capability declaration, not a physical boundary classification.",
    )


def halfspace_geometry(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        HalfSpaceSemigroup,
        OrientedHalfSpace,
    )

    data = _input_object(request)
    half_space = OrientedHalfSpace(
        _normal(data["normal"]),
        int(data.get("boundary_offset", 0)),
    )
    value = {
        "half_space": half_space,
        "basis_change": half_space.basis_change,
        "semigroup": HalfSpaceSemigroup.create(half_space),
    }
    return _contract_result(
        request,
        value,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Exact primitive-normal, adapted-basis, tangent-lattice, and "
            "one-sided semigroup data for the supplied rational flat half-space."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate=value,
        verification=(
            ("normal_is_primitive", True),
            ("adapted_unimodular_basis_constructed", True),
        ),
        backend=BackendProvenance(
            "internal-integer", "oriented-halfspace-geometry", SERVICE_HANDLER_VERSION
        ),
    )


def halfspace_compare_orientations(
    request: ServiceRequest,
) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import compare_orientations

    data = _input_object(request)
    comparison = compare_orientations(
        _normal(data["left_normal"]),
        _normal(data["right_normal"]),
    )
    return _contract_result(
        request,
        comparison,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Exact comparison of the two supplied primitive lattice normals; "
            "no model-specific boundary equivalence is inferred."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate=comparison,
        verification=(("orientation_comparison_constructed", True),),
        backend=BackendProvenance(
            "internal-integer", "compare-halfspace-orientations", SERVICE_HANDLER_VERSION
        ),
    )


def halfspace_contract(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import contract_laurent_submodule

    data = _input_object(request)
    source = contract_laurent_submodule(
        _bulk_submodule(data["bulk"]),
        timeout_seconds=float(data.get("timeout_seconds", 60)),
    )
    return _native_result(request, source)


def halfspace_primary(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        compile_projected_bulk_primary,
        contract_laurent_submodule,
    )

    data = _input_object(request)
    bulk = _bulk_submodule(data["bulk"])
    contracted = contract_laurent_submodule(
        bulk,
        timeout_seconds=float(data.get("timeout_seconds", 60)),
    )
    source = compile_projected_bulk_primary(bulk, contracted.value)
    return _native_result(request, source)


def halfspace_free_pairing(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        FreeBoundaryPairingPresentation,
        analyze_free_boundary_pairing,
    )

    data = _input_object(request)
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
        str(data.get("source_scope") or "canonical halfspace service input"),
    )
    source = analyze_free_boundary_pairing(
        presentation,
        timeout_seconds=float(data.get("timeout_seconds", 60)),
    )
    return _native_result(request, source)


def halfspace_toric2d(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        toric_z2_y_nonnegative_boundary_module,
    )

    return _native_result(request, toric_z2_y_nonnegative_boundary_module())


def halfspace_toric3d_primary(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        toric3d_z2_z_nonnegative_primary_benchmark,
    )

    return _native_result(
        request, toric3d_z2_z_nonnegative_primary_benchmark()
    )


def halfspace_secondary_example(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        ruba_yang_secondary_boundary_example,
    )

    return _native_result(request, ruba_yang_secondary_boundary_example())


def halfspace_xcube_orientation(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import xcube_orientation_benchmark

    data = _input_object(request)
    return _native_result(
        request, xcube_orientation_benchmark(_normal(data["normal"]))
    )


# ---------------------------------------------------------------------------
# Two-dimensional metric groups and finite local completion


def completion2d_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "metric_group_condensation": "certified_exact",
        "finite_local_completion": "bounded_exact",
        "automatic_stabilizer_anyon_extraction": "unsupported",
        "coefficients": "uniform prime and composite cyclic Pauli sites",
        "folding": "second_spin_and_braiding_forms_reversed",
        "thermodynamic_gap_proof": "unsupported",
    }
    return _capability_result(
        request,
        value,
        "completion2d-capabilities",
        "Software capability declaration; no gapped-boundary theorem is inferred.",
    )


def _metric_model(name, backend):
    from mobility_toolkit.anyons2d import (
        color_code_metric_model,
        double_semion_metric_model,
        fish_toric_metric_model,
        three_fermion_metric_model,
        zd_toric_metric_model,
    )

    models = {
        "z2-toric": lambda: zd_toric_metric_model(2, backend),
        "z4-toric": lambda: zd_toric_metric_model(4, backend),
        "double-semion": lambda: double_semion_metric_model(backend),
        "color-code": lambda: color_code_metric_model(backend),
        "fish-toric": lambda: fish_toric_metric_model(backend),
        "three-fermion": lambda: three_fermion_metric_model(backend),
    }
    if name not in models:
        raise ValueError("unknown metric model: " + str(name))
    return models[name]()


def _metric(data, backend):
    from mobility_toolkit.anyons2d import FiniteMetricGroup
    from mobility_toolkit.finite import FiniteAbelianGroup

    if "model" in data:
        return _metric_model(data["model"], backend).metric
    spec = data["metric"]
    group = FiniteAbelianGroup.from_coordinate_orders(
        tuple(spec["orders"]),
        backend,
        tuple(spec.get("labels", ())),
    )
    return FiniteMetricGroup.create(
        group,
        int(spec["phase_modulus"]),
        SparseIntMatrix.from_rows(
            tuple(tuple(row) for row in spec["braiding_rows"])
        ),
        tuple(spec["generator_spins"]),
        backend,
    )


def completion2d_metric(request: ServiceRequest) -> ComputationResult:
    data = _input_object(request)
    backend = _finite_backend(data)
    metric = _metric(data, backend)
    value = {
        "metric": metric,
        "group_order": metric.group.order(backend),
        "fusion_invariant_factors": metric.group.invariant_factors,
        "phase_modulus": metric.phase_modulus,
        "generator_spins": metric.generator_spins,
        "braiding_matrix": metric.braiding_matrix,
        "nondegenerate": metric.certificate.nondegenerate,
    }
    return _contract_result(
        request,
        value,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Exact finite Abelian fusion, spin, and braiding data for the "
            "explicitly supplied metric group or source-locked benchmark."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=metric.certificate,
        verification=(("finite_metric_group_verified", True),),
        backend=BackendProvenance(
            getattr(backend, "name", "python-flint"),
            "finite-metric-group",
            getattr(backend, "version", ""),
        ),
        warnings=(
            "An abstract metric group does not by itself provide a microscopic "
            "boundary Hamiltonian.",
        ),
    )


def completion2d_enumerate(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.anyons2d import (
        CondensateEnumerationBudget,
        CondensateEnumerationCheckpoint,
        enumerate_condensates,
    )

    data = _input_object(request)
    backend = _finite_backend(data)
    metric = _metric(data, backend)
    budget_data = data.get("budget", {})
    budget = CondensateEnumerationBudget(
        max_work_units=int(budget_data.get("max_work_units", 500_000)),
        max_results=int(budget_data.get("max_results", 100_000)),
        max_elements=int(budget_data.get("max_elements", 4096)),
        max_subgroups=int(budget_data.get("max_subgroups", 500_000)),
    )
    max_pages = int(data.get("max_pages", 1000))
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    checkpoint = _condensate_checkpoint(
        data.get("checkpoint"), CondensateEnumerationCheckpoint
    )
    candidates = []
    page = None
    pages = 0
    for _ in range(max_pages):
        page = enumerate_condensates(metric, backend, budget, checkpoint)
        candidates.extend(page.candidates)
        checkpoint = page.checkpoint
        pages += 1
        if checkpoint is None:
            break
    if page is None:
        raise ArithmeticError("condensate enumeration produced no page")
    certificate = page.certificate
    return _contract_result(
        request,
        {
            "metric": metric,
            "search_domain": page.domain,
            "candidates": tuple(candidates),
            "next_checkpoint": checkpoint,
            "page_count": pages,
        },
        exactness=certificate.exactness,
        theorem_scope=(
            "Exhaustive only for raw bosonic subgroups of the explicitly "
            "supplied finite metric group after the returned certificate marks "
            "the finite search complete."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=tuple(
            ("enumerator:" + item, True)
            for item in certificate.verification
        )
        + (("output_complete", checkpoint is None),),
        backend=BackendProvenance(
            getattr(backend, "name", "python-flint"),
            "finite-metric-condensate-enumeration",
            getattr(backend, "version", ""),
            (
                ("max_elements", budget.max_elements),
                ("max_pages", max_pages),
                ("max_subgroups", budget.max_subgroups),
            ),
        ),
        warnings=(
            "Completeness is only over raw subgroups of this finite metric group.",
            "No microscopic completion or thermodynamic spectral gap follows.",
        ),
        resource_usage=(
            ("candidate_count", len(candidates)),
            ("page_count", pages),
        ),
    )


def _strict_checkpoint_payload(payload, schema_id, fields):
    if not isinstance(payload, Mapping):
        raise TypeError("checkpoint must be an object or null")
    if payload.get("schema") != schema_id:
        raise ValueError("checkpoint schema is missing or unsupported")
    allowed = set(fields) | {"schema"}
    unknown = sorted(set(payload) - allowed)
    missing = sorted(set(fields) - set(payload))
    if unknown:
        raise ValueError("unknown checkpoint fields: " + ", ".join(unknown))
    if missing:
        raise ValueError("missing checkpoint fields: " + ", ".join(missing))


def _condensate_checkpoint(payload, checkpoint_type):
    if payload is None:
        return None
    fields = (
        "metric_hash",
        "element_cursor",
        "element_vectors",
        "pending_subgroups",
        "seen_subgroups",
        "active_subgroup",
        "active_element_cursor",
        "subgroup_join_tests",
        "subgroup_search_complete",
        "candidate_scan_cursor",
        "candidate_transcript",
        "output_cursor",
        "output_prefix",
        "output_transcript_hash",
    )
    _strict_checkpoint_payload(payload, checkpoint_type.SCHEMA_ID, fields)
    active = payload["active_subgroup"]
    return checkpoint_type(
        metric_hash=str(payload["metric_hash"]),
        element_cursor=int(payload["element_cursor"]),
        element_vectors=tuple(
            tuple(int(value) for value in vector)
            for vector in payload["element_vectors"]
        ),
        pending_subgroups=tuple(
            tuple(int(value) for value in subgroup)
            for subgroup in payload["pending_subgroups"]
        ),
        seen_subgroups=tuple(
            tuple(int(value) for value in subgroup)
            for subgroup in payload["seen_subgroups"]
        ),
        active_subgroup=(
            None
            if active is None
            else tuple(int(value) for value in active)
        ),
        active_element_cursor=int(payload["active_element_cursor"]),
        subgroup_join_tests=int(payload["subgroup_join_tests"]),
        subgroup_search_complete=bool(payload["subgroup_search_complete"]),
        candidate_scan_cursor=int(payload["candidate_scan_cursor"]),
        candidate_transcript=tuple(
            (
                tuple(int(value) for value in entry[0]),
                str(entry[1]),
                str(entry[2]),
            )
            for entry in payload["candidate_transcript"]
        ),
        output_cursor=int(payload["output_cursor"]),
        output_prefix=tuple(
            (tuple(int(value) for value in entry[0]), str(entry[1]))
            for entry in payload["output_prefix"]
        ),
        output_transcript_hash=str(payload["output_transcript_hash"]),
    )


def completion2d_fold(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.anyons2d import fold_metric_groups

    data = _input_object(request)
    backend = _finite_backend(data)
    left = _metric(data["left"], backend)
    right = _metric(data["right"], backend)
    folded = fold_metric_groups(left, right, backend)
    return _contract_result(
        request,
        folded,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Exact finite direct-sum folding with the second spin and braiding "
            "forms reversed. No microscopic interface completion is constructed."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=folded,
        verification=(
            ("second_braiding_form_reversed", folded.second_form_reversed),
            ("second_spin_form_reversed", folded.second_form_reversed),
        ),
        backend=BackendProvenance(
            getattr(backend, "name", "python-flint"),
            "finite-metric-folding",
            getattr(backend, "version", ""),
        ),
    )


def _pauli_operator(module, data):
    return module.operator(
        tuple(
            LocalPauliTerm.cyclic(
                item["site_id"],
                x=int(item.get("x", 0)),
                z=int(item.get("z", 0)),
            )
            for item in data.get("terms", ())
        ),
        phase=int(data.get("phase", 0)),
    )


def _named_pauli_terms(module, items):
    from mobility_toolkit.completion2d import NamedPauliTerm

    return tuple(
        NamedPauliTerm(item["term_id"], _pauli_operator(module, item))
        for item in items
    )


def _completion_request(data, backend):
    from mobility_toolkit.completion2d import (
        CondensateStringLift,
        FiniteBoundaryLocalityDomain,
        LocalBoundaryCompletionRequest,
    )

    sites = tuple(data["sites"])
    dimensions = tuple(int(item["dimension"]) for item in sites)
    if len(set(dimensions)) != 1:
        raise ValueError(
            "explicit 2D completion currently supports uniform cyclic site dimensions"
        )
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
        site_depths=tuple((item["site_id"], item["depth"]) for item in sites),
        max_completion_depth=int(locality_data["max_completion_depth"]),
        max_boundary_term_sites=int(locality_data["max_boundary_term_sites"]),
        max_boundary_term_diameter=int(
            locality_data["max_boundary_term_diameter"]
        ),
        max_short_string_sites=int(locality_data["max_short_string_sites"]),
    )
    lifts = tuple(
        CondensateStringLift(
            item["label"],
            tuple(item["anyon"]),
            _pauli_operator(module, item["operator"]),
            tuple(item["remote_excitation_term_ids"]),
        )
        for item in data["string_lifts"]
    )
    return LocalBoundaryCompletionRequest(
        metric=_metric(data, backend),
        pauli_module=module,
        bulk_terms=_named_pauli_terms(module, data["bulk_terms"]),
        boundary_terms=_named_pauli_terms(module, data["boundary_terms"]),
        string_lifts=lifts,
        locality_domain=locality,
        source_scope=data["source_scope"],
        assumptions=tuple(data.get("completion_assumptions", ())),
    )


def completion2d_toric_cut(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.completion2d import (
        verify_local_boundary_completion,
        zd_toric_cut_completion_benchmark,
    )

    data = _input_object(request)
    backend = _finite_backend(data)
    benchmark = zd_toric_cut_completion_benchmark(
        int(data["modulus"]), data["boundary_kind"], backend
    )
    source = verify_local_boundary_completion(benchmark.request, backend)
    return _native_result(request, source)


def completion2d_verify(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.completion2d import verify_local_boundary_completion

    data = _input_object(request)
    backend = _finite_backend(data)
    source = verify_local_boundary_completion(
        _completion_request(data, backend), backend
    )
    return _native_result(request, source)


# ---------------------------------------------------------------------------
# Bounded symbolic three-dimensional boundary enumeration


def symbolic3d_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "e1_finite_isotropic_subgroups": "python_api_certified_exact_after_exhaustion",
        "e2_translation_compatible_submodules": "python_api_bounded_exact_after_exhaustion",
        "e2_ancillas": "unsupported",
        "e2_local_completions": "unsupported",
        "e3_bounded_seed_presentations": "bounded_exact_after_exhaustion",
        "e3_saturation": "unsupported",
        "e3_anomaly_and_completion": "unsupported",
        "e3_thermodynamic_classification": "unsupported",
        "implemented_e3_equivalences": (
            "raw_constant_generator_change",
            "raw_plus_common_tangent_translation",
        ),
    }
    return _capability_result(
        request,
        value,
        "symbolic3d-capabilities",
        "Software capability declaration; no thermodynamic 3D boundary classification.",
    )


def _symbolic3d_request(data):
    from mobility_toolkit.boundary.enumeration.symbolic3d import (
        Symbolic3DEquivalence,
        Symbolic3DSearchRequest,
    )
    from mobility_toolkit.boundary_halfspace import (
        FreeBoundaryPairingPresentation,
    )

    if data.get("full_boundary_module_supplied") is not True:
        raise ValueError(
            "symbolic E3 requires full_boundary_module_supplied=true; "
            "primary-only input is insufficient"
        )
    modulus = int(data["coefficient_modulus"])
    pairing = tuple(
        tuple(_tangent_polynomial(modulus, 2, entry) for entry in row)
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
    return Symbolic3DSearchRequest(
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


def symbolic3d_enumerate(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary.enumeration.symbolic3d import (
        Symbolic3DBudget,
        Symbolic3DCheckpoint,
        enumerate_symbolic3d_candidates,
    )

    data = _input_object(request)
    search_request = _symbolic3d_request(data)
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
    checkpoint = _symbolic3d_checkpoint(
        data.get("checkpoint"), Symbolic3DCheckpoint
    )
    candidates = []
    final = None
    page_count = 0
    for _ in range(max_pages):
        final = enumerate_symbolic3d_candidates(
            search_request, budget, checkpoint=checkpoint
        )
        candidates.extend(final.value.candidates)
        checkpoint = final.value.checkpoint
        page_count += 1
        if checkpoint is None:
            break
    if final is None:
        raise ArithmeticError("symbolic E3 enumeration produced no page")
    value = {
        "request": search_request,
        "candidates": tuple(candidates),
        "candidate_hashes": tuple(item.candidate_hash for item in candidates),
        "next_checkpoint": checkpoint,
        "page_count": page_count,
    }
    rebound = _native_result(request, final, value=value)
    return replace(
        rebound,
        verification=tuple(rebound.verification)
        + (("all_requested_pages_aggregated", True),),
        resource_usage=tuple(rebound.resource_usage)
        + (("service_page_count", page_count),),
    )


def _symbolic3d_checkpoint(payload, checkpoint_type):
    from mobility_toolkit.boundary.enumeration.symbolic3d import (
        Symbolic3DDecision,
        Symbolic3DTranscriptEntry,
    )

    if payload is None:
        return None
    fields = (
        "request_hash",
        "rref_cursor",
        "transcript",
        "transcript_hash",
        "equivalence_representative_prefix",
        "equivalence_representative_prefix_hash",
        "output_prefix",
        "output_prefix_hash",
        "total_work",
        "checkpoint_hash",
    )
    _strict_checkpoint_payload(payload, checkpoint_type.SCHEMA_ID, fields)
    transcript = []
    transcript_fields = (
        "coefficient_basis",
        "basis_hash",
        "decision",
        "equivalence_key",
        "pairing_hash",
    )
    for entry in payload["transcript"]:
        _strict_checkpoint_payload(
            entry, Symbolic3DTranscriptEntry.SCHEMA_ID, transcript_fields
        )
        transcript.append(
            Symbolic3DTranscriptEntry(
                coefficient_basis=tuple(
                    tuple(int(value) for value in row)
                    for row in entry["coefficient_basis"]
                ),
                basis_hash=str(entry["basis_hash"]),
                decision=Symbolic3DDecision(entry["decision"]),
                equivalence_key=str(entry["equivalence_key"]),
                pairing_hash=str(entry["pairing_hash"]),
            )
        )
    checkpoint = checkpoint_type(
        request_hash=str(payload["request_hash"]),
        rref_cursor=int(payload["rref_cursor"]),
        transcript=tuple(transcript),
        transcript_hash=str(payload["transcript_hash"]),
        equivalence_representative_prefix=tuple(
            (str(entry[0]), str(entry[1]))
            for entry in payload["equivalence_representative_prefix"]
        ),
        equivalence_representative_prefix_hash=str(
            payload["equivalence_representative_prefix_hash"]
        ),
        output_prefix=tuple(str(value) for value in payload["output_prefix"]),
        output_prefix_hash=str(payload["output_prefix_hash"]),
        total_work=int(payload["total_work"]),
        checkpoint_hash=str(payload["checkpoint_hash"]),
    )
    if not checkpoint.structurally_verified:
        raise ValueError("symbolic3d checkpoint failed structural verification")
    return checkpoint


def symbolic3d_toric_primary_preflight(
    request: ServiceRequest,
) -> ComputationResult:
    from mobility_toolkit.boundary import toric3d_primary_symbolic_crosscheck

    return _native_result(request, toric3d_primary_symbolic_crosscheck())


def symbolic3d_xcube_preflight(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary import xcube_symbolic_orientation_crosscheck

    data = _input_object(request)
    return _native_result(
        request, xcube_symbolic_orientation_crosscheck(_normal(data["normal"]))
    )


# ---------------------------------------------------------------------------
# Cheshire static, synthesis, finite enumeration, fusion, and X-cube reference


def cheshire_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "api_version": "2",
        "operations": {
            "defects.cheshire.classify_abelian": {
                "scope": "finite pointed/Abelian metric groups",
                "classification": "exhaustive only after folded Lagrangian search exhaustion",
                "generic_direct_algebra": "requires pointed cochain input",
            },
            "defects.cheshire.toric2d_reference": {
                "scope": "source-locked Z2 toric code",
                "classification": "computed_exact_six_oriented_morita_species",
                "ordered_fusion": "source_theorem_with_exact_table_replay",
                "anyon_action": "source_theorem_with_exact_crosswalk",
            },
            "defects.cheshire.fuse": {
                "scope": "Z2 toric six-species reference",
                "coefficient_semantics": "1+1D_TQFT_valued_not_numeric_scalar",
            },
            "defects.cheshire.realize_toric2d": {
                "scope": "explicit finite square-cellular slit",
                "status": "bounded_exact_commuting_Pauli_realization",
            },
            "defects.cheshire.circuit_toric2d": {
                "scope": "finite defect-chain Clifford templates",
                "status": "exact_phase_aware_conjugation_replay",
            },
            "defects.cheshire.toric3d_finite_reference": {
                "scope": "explicit finite 3+1D plaquette-qubit toric cellulation",
                "status": "certified_exact_static",
            },
            "defects.cheshire.xcube_candidates": {
                "scope": "fixed coordinate-axis five-generator support slice",
                "status": "support_candidate_only",
                "optional_finite_reference": (
                    "bounded_exact local q2 z-lineon condensate completion; "
                    "upgrades only <ell_z> to static_cheshire_candidate"
                ),
                "classification_complete": False,
            },
        },
        "evidence_statuses": (
            "source_theorem",
            "computed_exact",
            "bounded_exact",
            "conditional",
            "conjectural",
            "unsupported",
        ),
        "fracton_evidence_ladder": (
            "support_candidate",
            "static_cheshire_candidate",
            "mobility_enriched_algebra",
            "circuit_certified_cheshire",
        ),
        "fracton_default_equivalence": (
            "fixed oriented axis + finite-depth equivalence + retained planon dressing"
        ),
        "general_fracton_ir": {
            "primitive_rational_direction": "implemented_exact_geometry_validation",
            "stratified_tube_endpoints_junctions": "implemented_geometry_carrier",
            "equivalence_scopes": (
                "microscopic",
                "finite_depth",
                "foliated",
                "orientation_reversal",
                "cubic_symmetry",
                "planon_dressing",
            ),
            "arbitrary_direction_classifier": "unsupported",
        },
        "unsupported": (
            "complete non-Abelian algebra-object solver",
            "generic thermodynamic gap proof",
            "slanted X-cube line classification",
            "automatic foliated quotient from support data",
        ),
    }
    return _capability_result(
        request,
        value,
        "cheshire-capabilities",
        "Software capability declaration, not a Cheshire phase theorem.",
    )


def _cheshire_domain(data: Mapping[str, Any], defect_key: str = "defects"):
    from mobility_toolkit.defects import ClosedLoop, OpenSegment
    from mobility_toolkit.geometry import rectangular_cubical_complex

    shape = tuple(int(value) for value in data["shape"])
    if len(shape) != 3:
        raise ValueError("shape must contain exactly three lengths")
    complex_ = rectangular_cubical_complex(
        shape, periodic_axes=tuple(int(value) for value in data.get("periodic_axes", ()))
    )
    defects = []
    for item in data[defect_key]:
        arguments = (
            complex_,
            item["defect_id"],
            tuple(tuple(int(value) for value in base) for base in item["cube_bases"]),
        )
        if item["topology"] == "open_segment":
            defects.append(OpenSegment.from_cube_bases(*arguments))
        elif item["topology"] == "closed_loop":
            defects.append(ClosedLoop.from_cube_bases(*arguments))
        else:
            raise ValueError("topology must be open_segment or closed_loop")
    if not defects:
        raise ValueError("at least one defect is required")
    return complex_, tuple(defects)


def _cheshire_network(spec):
    from mobility_toolkit.defects.cheshire import LineTopology
    from mobility_toolkit.defects.cheshire_fusion import (
        CheshireDefectNetwork,
        CheshireNetworkEdge,
        CheshireNetworkNode,
        EndpointBinding,
        NetworkNodeKind,
    )

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
        str(spec.get("provenance") or "canonical Cheshire service network"),
    )


def cheshire_toric3d_finite_reference(
    request: ServiceRequest,
) -> ComputationResult:
    from mobility_toolkit.defects import analyze_toric_cheshire

    data = _input_object(request)
    complex_, defects = _cheshire_domain(data)
    analysis = analyze_toric_cheshire(
        complex_,
        defects,
        _finite_backend(data),
        tube_radius_lattice_steps=int(data.get("tube_radius_lattice_steps", 0)),
    )
    return _contract_result(
        request,
        analysis,
        exactness=analysis.exactness,
        theorem_scope=analysis.theorem_scope,
        certificate_level=analysis.certificate_level,
        certificate={
            "defect_transformations": tuple(
                report.transformation_certificate
                for report in analysis.defect_reports
            ),
            "pinned_elimination": analysis.pinned_elimination_certificate,
            "tube_representation": (
                analysis.tubular_deleted_representation.certificate
            ),
        },
        verification=(
            ("source_assumptions", analysis.assumptions),
            ("static_finite_certificates_verified", True),
        ),
        backend=analysis.backend_provenance,
    )


def cheshire_synthesis(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import (
        synthesize_tubular_to_line,
        toric_cheshire_condensation_candidate,
    )

    data = _input_object(request)
    complex_, defects = _cheshire_domain(data)
    backend = _finite_backend(data)
    candidate = toric_cheshire_condensation_candidate(
        complex_, defects, backend, data.get("candidate_id")
    )
    synthesis = synthesize_tubular_to_line(candidate, tuple(data["radii"]))
    source = synthesis.samples[0].analysis
    return _contract_result(
        request,
        synthesis,
        exactness=synthesis.exactness,
        theorem_scope=synthesis.theorem_scope,
        certificate_level=CertificateLevel.FULL,
        certificate={
            "adjacent": synthesis.adjacent_certificates,
            "steps": synthesis.step_certificates,
            "transcript_hash": synthesis.transcript_hash,
        },
        verification=(
            ("finite_invariants_preserved", synthesis.finite_invariants_preserved),
            ("finite_depth_circuit_constructed", synthesis.circuit_constructed),
            ("phase_equivalence_claimed", synthesis.phase_equivalence_claimed),
        ),
        backend=source.backend_provenance,
    )


def cheshire_species(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import (
        enumerate_cheshire_species,
        toric_cheshire_condensation_candidate,
        verify_cheshire_species_enumeration,
    )
    from mobility_toolkit.geometry import rectangular_cubical_complex

    data = _input_object(request)
    complex_ = rectangular_cubical_complex(
        tuple(data["shape"]),
        periodic_axes=tuple(data.get("periodic_axes", ())),
    )
    backend = _finite_backend(data)
    candidates = []
    for candidate_data in data["candidate_sets"]:
        merged = dict(data)
        merged["defects"] = candidate_data["defects"]
        _, defects = _cheshire_domain(merged)
        candidates.append(
            toric_cheshire_condensation_candidate(
                complex_,
                defects,
                backend,
                candidate_data["candidate_id"],
            )
        )
    enumeration = enumerate_cheshire_species(candidates, tuple(data["radii"]))
    verified = verify_cheshire_species_enumeration(enumeration)
    if not verified:
        raise ArithmeticError("Cheshire species transcript replay failed")
    provenance = (
        enumeration.syntheses[0].samples[0].analysis.backend_provenance
        if enumeration.syntheses
        else BackendProvenance(
            "python-flint", "bounded-cheshire-species-enumeration", ""
        )
    )
    return _contract_result(
        request,
        enumeration,
        exactness=Exactness.BOUNDED_EXACT,
        theorem_scope=(
            "Complete only for the explicitly supplied finite candidate list and radii."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=enumeration.certificate,
        verification=(("semantic_transcript_replay_verified", verified),),
        backend=provenance,
    )


def cheshire_fusion(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import construct_static_toric_cheshire_fusion

    data = _input_object(request)
    complex_, before = _cheshire_domain(data, "before_defects")
    _, after = _cheshire_domain(data, "after_defects")
    backend = _finite_backend(data)
    fusion = construct_static_toric_cheshire_fusion(
        data["fusion_id"],
        complex_,
        before,
        after,
        backend,
        tube_radius_lattice_steps=int(data.get("tube_radius_lattice_steps", 0)),
        before_network=_cheshire_network(data.get("before_network")),
        after_network=_cheshire_network(data.get("after_network")),
    )
    return _contract_result(
        request,
        fusion,
        exactness=fusion.static_candidate_exactness,
        theorem_scope=fusion.theorem_scope,
        certificate_level=fusion.certificate_level,
        certificate=fusion.certificate,
        verification=(
            ("finite_depth_circuit_constructed", False),
            (
                "static_fusion_certificate_verified",
                fusion.certificate.structurally_verified,
            ),
        ),
        backend=fusion.before_analysis.backend_provenance,
    )


def cheshire_xcube_reference(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import (
        analyze_xcube_fracton_line_reference,
        xcube_axial_line_reference_request,
    )

    data = _input_object(request)
    source_request = xcube_axial_line_reference_request(
        int(data.get("line_length_lattice_steps", 1))
    )
    if "normal" in data:
        source_request = replace(
            source_request,
            normal=_normal(data["normal"]),
        )
    source = analyze_xcube_fracton_line_reference(
        source_request, _finite_backend(data)
    )
    return _native_result(request, source)


def _cheshire_backend_provenance(backend, algorithm: str) -> BackendProvenance:
    return BackendProvenance(
        getattr(backend, "name", "python-flint"),
        algorithm,
        getattr(backend, "version", ""),
    )


def cheshire_classify_abelian(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.anyons2d import (
        CondensateEnumerationBudget,
        CondensateEnumerationCheckpoint,
    )
    from mobility_toolkit.defects import classify_abelian_interfaces

    data = _input_object(request)
    backend = _finite_backend(data)
    left = _metric(data["left"], backend)
    right = _metric(data["right"], backend)
    budget_data = data.get("budget", {})
    budget = CondensateEnumerationBudget(
        max_work_units=int(budget_data.get("max_work_units", 2_000_000)),
        max_results=int(budget_data.get("max_results", 100_000)),
        max_elements=int(budget_data.get("max_elements", 4_096)),
        max_subgroups=int(budget_data.get("max_subgroups", 500_000)),
    )
    checkpoint = _condensate_checkpoint(
        data.get("checkpoint"), CondensateEnumerationCheckpoint
    )
    equivalence_relation = (
        request.equivalence_relation
        if request.equivalence_relation
        in {"oriented_morita", "unoriented_morita", "raw_folded_lagrangian"}
        else str(data.get("classification_scope", "oriented_morita"))
    )
    classification = classify_abelian_interfaces(
        left,
        right,
        backend,
        budget=budget,
        checkpoint=checkpoint,
        max_pages=int(data.get("max_pages", 1_000)),
        equivalence_relation=equivalence_relation,
    )
    certificate = classification.certificate
    return _contract_result(
        request,
        classification,
        exactness=certificate.enumeration.exactness,
        theorem_scope=(
            "Exhaustive oriented finite pointed/Abelian interface support "
            "classification only when classification_complete=true. Abstract "
            "metric data alone does not construct a microscopic Hamiltonian."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            (
                "folded_lagrangian_search_complete",
                certificate.classification_complete,
            ),
            (
                "direct_generic_algebra_multiplication_constructed",
                all(item.algebra is not None for item in classification.species),
            ),
        ),
        backend=_cheshire_backend_provenance(
            backend, "finite-pointed-interface-classification-v2"
        ),
        warnings=classification.warnings,
        resource_usage=(
            ("species_count", len(classification.species)),
            (
                "classification_complete",
                certificate.classification_complete,
            ),
        ),
    )


def cheshire_toric2d_reference(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import (
        toric_2d_defect_classification,
        toric_2d_fusion_table,
    )

    data = _input_object(request)
    backend = _finite_backend(data)
    equivalence_relation = (
        request.equivalence_relation
        if request.equivalence_relation
        in {"oriented_morita", "unoriented_morita", "raw_folded_lagrangian"}
        else "oriented_morita"
    )
    classification = toric_2d_defect_classification(
        backend, equivalence_relation=equivalence_relation
    )
    fusion_table = toric_2d_fusion_table()
    certificate = {
        "classification": classification.certificate,
        "fusion_table_hash": canonical_hash(
            "toric-2d-ordered-fusion-table-v2", fusion_table
        ),
        "ordered_entry_count": len(fusion_table),
        "source_equations": (
            "Roumpedakis--Seifnashri--Shao arXiv:2204.02407 Eq. (6.37)",
            "Roumpedakis--Seifnashri--Shao arXiv:2204.02407 Eq. (6.38)",
        ),
    }
    return _contract_result(
        request,
        {
            "classification": classification,
            "ordered_fusion_table": fusion_table,
        },
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Complete six-species oriented-Morita reference for the 2D Z2 "
            "toric code. The abstract result does not by itself prove a gap "
            "for every finite lattice realization."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("folded_enumerator_returned_exactly_six", len(classification.species) == 6),
            ("literature_crosswalk_verified", True),
            ("ordered_fusion_entries_verified", len(fusion_table) == 36),
            (
                "all_direct_algebras_associative",
                all(
                    item.algebra is not None
                    and item.algebra.certificate.associativity_verified
                    for item in classification.species
                ),
            ),
        ),
        backend=_cheshire_backend_provenance(
            backend, "toric-2d-six-defect-reference-v2"
        ),
        warnings=classification.warnings,
    )


def cheshire_fuse(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import fuse_toric_2d_species

    data = _input_object(request)
    model = str(data.get("model", "z2-toric"))
    if model != "z2-toric":
        missing = (
            "explicit pointed associator/F-symbol data",
            "direct algebra multiplications for both ordered inputs",
            "bimodule composition and Morita-reduction certificate",
            "1+1D coefficient TQFT identification",
        )
        return _contract_result(
            request,
            {
                "status": "unsupported",
                "model": model,
                "left_species_id": data["left_species_id"],
                "right_species_id": data["right_species_id"],
                "missing_obligations": missing,
            },
            exactness=Exactness.UNSUPPORTED,
            theorem_scope=(
                "No categorical fusion conclusion is returned outside the "
                "source-locked Z2 toric executor without explicit pointed "
                "cochain and bimodule-composition data."
            ),
            certificate_level=CertificateLevel.FULL,
            certificate={
                "evidence_status": "unsupported",
                "missing_obligations": missing,
            },
            verification=(("fusion_claim_returned", False),),
            backend=BackendProvenance(
                "internal-contract",
                "unsupported-generic-cheshire-fusion-v2",
                SERVICE_HANDLER_VERSION,
            ),
        )
    fusion = fuse_toric_2d_species(
        str(data["left_species_id"]),
        str(data["right_species_id"]),
    )
    return _contract_result(
        request,
        fusion,
        exactness=Exactness.CERTIFIED_EXACT,
        theorem_scope=(
            "Ordered fusion in the source-locked six-defect 2D Z2 toric "
            "reference. Coefficients are 1+1D TQFT records, never numeric "
            "multiplicities."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate={
            "fusion": fusion,
            "tqft_coefficients_are_numeric_scalars": False,
        },
        verification=(
            ("ordered_fusion_verified", fusion.verified),
            (
                "all_coefficients_tqft_valued",
                all(
                    not term.coefficient.numeric_scalar
                    for term in fusion.terms
                ),
            ),
        ),
        backend=BackendProvenance(
            "internal-exact", "toric-2d-ordered-fusion-v2", SERVICE_HANDLER_VERSION
        ),
    )


def cheshire_realize_toric2d(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import realize_toric_2d_defect

    data = _input_object(request)
    backend = _finite_backend(data)
    realization = realize_toric_2d_defect(
        str(data["species_id"]),
        int(data.get("line_length_lattice_steps", 2)),
        backend,
    )
    return _contract_result(
        request,
        realization,
        exactness=Exactness.BOUNDED_EXACT,
        theorem_scope=realization.certificate.theorem_scope,
        certificate_level=CertificateLevel.FULL,
        certificate=realization.certificate,
        verification=(
            ("finite_realization_verified", realization.certificate.verified),
            ("diagram_derived_from_operator_support", bool(realization.tikz)),
        ),
        backend=_cheshire_backend_provenance(
            backend, "toric-2d-finite-lattice-realization-v2"
        ),
        warnings=realization.warnings,
        resource_usage=(
            ("qubit_count", len(realization.pauli_module.local_systems)),
            ("defect_term_count", len(realization.defect_terms)),
        ),
    )


def cheshire_circuit_toric2d(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import construct_toric_2d_circuit

    data = _input_object(request)
    circuit = construct_toric_2d_circuit(
        str(data["process"]),
        str(data["left_species_id"]),
        int(data.get("line_length_lattice_steps", 2)),
        right_species_id=(
            None
            if data.get("right_species_id") is None
            else str(data["right_species_id"])
        ),
    )
    return _contract_result(
        request,
        circuit,
        exactness=Exactness.BOUNDED_EXACT,
        theorem_scope=circuit.certificate.theorem_scope,
        certificate_level=CertificateLevel.FULL,
        certificate=circuit.certificate,
        verification=(
            (
                "exact_phase_aware_pauli_conjugation_verified",
                circuit.certificate.exact_pauli_conjugation_verified,
            ),
            (
                "circuit_layer_disjointness_verified",
                circuit.certificate.layer_disjointness_verified,
            ),
            (
                "endpoint_incidence_verified",
                circuit.certificate.endpoint_incidence_verified,
            ),
            (
                "fusion_ancilla_decoupling_verified",
                circuit.certificate.ancilla_decoupling_verified,
            ),
            (
                "fusion_degeneracy_matches_coefficient_shadow",
                circuit.certificate.fusion_degeneracy_matches_coefficient_shadow,
            ),
        ),
        backend=BackendProvenance(
            "internal-exact", "finite-clifford-replay-v2", SERVICE_HANDLER_VERSION
        ),
        warnings=circuit.warnings,
        resource_usage=(
            ("circuit_depth", circuit.circuit.depth),
            (
                "gate_count",
                sum(len(layer.gates) for layer in circuit.circuit.layers),
            ),
            (
                "coefficient_sector_codespace_dimension",
                circuit.certificate.coefficient_sector_codespace_dimension,
            ),
        ),
    )


def cheshire_xcube_candidates(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import xcube_cheshire_candidates

    data = _input_object(request)
    include_reference = bool(data.get("include_finite_static_reference", False))
    backend = _finite_backend(data) if include_reference else None
    catalog = xcube_cheshire_candidates(
        axis=str(data.get("axis", "all")),
        orientation=str(data.get("orientation", "+")),
        include_finite_static_reference=include_reference,
        finite_reference_line_length=int(
            data.get("finite_reference_line_length", 1)
        ),
        backend=backend,
    )
    return _contract_result(
        request,
        catalog,
        exactness=Exactness.EXPERIMENTAL,
        theorem_scope=(
            "Exact exhaustion of nonzero totally singular subgroups in the "
            "recorded five-generator coordinate-axis support slice. This is "
            "not a complete X-cube Cheshire classification."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate={
            "support_search_complete": catalog.support_search_complete,
            "classification_complete": catalog.classification_complete,
            "transcript_hash": catalog.transcript_hash,
            "highest_uniform_evidence_tier":
                catalog.highest_uniform_evidence_tier,
            "missing_obligations": catalog.missing_obligations,
        },
        verification=(
            (
                "58_support_candidates_per_selected_axis",
                len(catalog.candidates) == 58 * len(catalog.selected_axes),
            ),
            ("classification_complete", False),
            (
                "no_record_above_static_candidate",
                all(
                    item.evidence_tier.value
                    in {"support_candidate", "static_cheshire_candidate"}
                    for item in catalog.candidates
                ),
            ),
            (
                "finite_static_upgrade_count",
                sum(
                    item.evidence_tier.value == "static_cheshire_candidate"
                    for item in catalog.candidates
                )
                == int(include_reference),
            ),
        ),
        backend=(
            _cheshire_backend_provenance(
                backend, "xcube-support-candidates-v2"
            )
            if backend is not None
            else BackendProvenance(
                "internal-gf2",
                "xcube-support-candidates-v2",
                SERVICE_HANDLER_VERSION,
            )
        ),
        warnings=catalog.warnings,
        resource_usage=(
            ("candidate_count", len(catalog.candidates)),
            ("selected_axis_count", len(catalog.selected_axes)),
        ),
    )


# ---------------------------------------------------------------------------
# Default-registry contribution


def _object_schema(required, properties):
    return {
        "additionalProperties": False,
        "properties": dict(properties),
        "required": list(required),
        "type": "object",
    }


_ARRAY = {"type": "array"}
_BOOLEAN = {"type": "boolean"}
_INTEGER = {"type": "integer"}
_NUMBER = {"type": "number"}
_OBJECT = {"type": "object"}
_STRING = {"type": "string"}


def boundary_usecase_service_registrations(
    existing_operations: Tuple[str, ...] = (),
):
    """Return canonical retained-use-case registrations not already present.

    ``build_default_registry`` passes its existing operation names so this
    contribution can coexist with the Phase-10 migration while older in-file
    handlers are being deleted.  There are no alternate operation aliases.
    """

    from mobility_toolkit.services.contracts import (
        ServiceCapability,
        ServiceCatalogEntry,
    )
    from mobility_toolkit.services.registry import ServiceRegistration

    existing = set(existing_operations)

    empty_schema = _object_schema((), {})
    normal_schema = _object_schema(("normal",), {"normal": _ARRAY})
    geometry_schema = _object_schema(
        ("normal",),
        {"normal": _ARRAY, "boundary_offset": _INTEGER},
    )
    comparison_schema = _object_schema(
        ("left_normal", "right_normal"),
        {"left_normal": _ARRAY, "right_normal": _ARRAY},
    )
    bulk_schema = _object_schema(
        ("bulk",),
        {"bulk": _OBJECT, "timeout_seconds": _NUMBER},
    )
    pairing_schema = _object_schema(
        ("coefficient_modulus", "tangent_rank", "pairing_matrix"),
        {
            "coefficient_modulus": _INTEGER,
            "tangent_rank": _INTEGER,
            "pairing_matrix": _ARRAY,
            "generator_labels": _ARRAY,
            "source_scope": _STRING,
            "timeout_seconds": _NUMBER,
        },
    )
    metric_schema = _object_schema(
        (),
        {
            "model": _STRING,
            "metric": _OBJECT,
            "max_dense_entries": _INTEGER,
        },
    )
    enumerate_metric_schema = _object_schema(
        (),
        {
            "model": _STRING,
            "metric": _OBJECT,
            "budget": _OBJECT,
            "max_pages": _INTEGER,
            "checkpoint": {"type": ["object", "null"]},
            "max_dense_entries": _INTEGER,
        },
    )
    fold_schema = _object_schema(
        ("left", "right"),
        {
            "left": _OBJECT,
            "right": _OBJECT,
            "max_dense_entries": _INTEGER,
        },
    )
    toric_cut_schema = _object_schema(
        ("modulus", "boundary_kind"),
        {
            "modulus": _INTEGER,
            "boundary_kind": {"enum": ["rough", "smooth"]},
            "max_dense_entries": _INTEGER,
        },
    )
    explicit_completion_schema = _object_schema(
        (
            "sites",
            "bulk_terms",
            "boundary_terms",
            "string_lifts",
            "locality",
            "source_scope",
        ),
        {
            "model": _STRING,
            "metric": _OBJECT,
            "sites": _ARRAY,
            "bulk_terms": _ARRAY,
            "boundary_terms": _ARRAY,
            "string_lifts": _ARRAY,
            "locality": _OBJECT,
            "source_scope": _STRING,
            "completion_assumptions": _ARRAY,
            "max_dense_entries": _INTEGER,
        },
    )
    symbolic_schema = _object_schema(
        (
            "full_boundary_module_supplied",
            "coefficient_modulus",
            "normal",
            "pairing_matrix",
            "exponent_bounds",
            "max_generators",
        ),
        {
            "full_boundary_module_supplied": _BOOLEAN,
            "coefficient_modulus": _INTEGER,
            "normal": _ARRAY,
            "pairing_matrix": _ARRAY,
            "exponent_bounds": _ARRAY,
            "max_generators": _INTEGER,
            "generator_labels": _ARRAY,
            "source_scope": _STRING,
            "equivalence": {
                "enum": [
                    "raw_constant_generator_change",
                    "raw_plus_common_tangent_translation",
                ]
            },
            "include_zero_submodule": _BOOLEAN,
            "budget": _OBJECT,
            "max_pages": _INTEGER,
            "checkpoint": {"type": ["object", "null"]},
        },
    )
    cheshire_toric3d_finite_reference_schema = _object_schema(
        ("shape", "defects"),
        {
            "shape": _ARRAY,
            "periodic_axes": _ARRAY,
            "defects": _ARRAY,
            "tube_radius_lattice_steps": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_classify_abelian_schema = _object_schema(
        ("left", "right"),
        {
            "left": _OBJECT,
            "right": _OBJECT,
            "classification_scope": {
                "enum": [
                    "oriented_morita",
                    "unoriented_morita",
                    "raw_folded_lagrangian",
                ]
            },
            "budget": _OBJECT,
            "max_pages": _INTEGER,
            "checkpoint": {"type": ["object", "null"]},
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_fuse_schema = _object_schema(
        ("left_species_id", "right_species_id"),
        {
            "model": _STRING,
            "left_species_id": _STRING,
            "right_species_id": _STRING,
        },
    )
    cheshire_realize_toric2d_schema = _object_schema(
        ("species_id",),
        {
            "species_id": {
                "enum": ["1", "S_e", "S_m", "S_psi", "S_em", "S_me"]
            },
            "line_length_lattice_steps": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_circuit_toric2d_schema = _object_schema(
        ("process", "left_species_id"),
        {
            "process": {
                "enum": ["creation", "deformation", "motion", "fusion"]
            },
            "left_species_id": {
                "enum": ["1", "S_e", "S_m", "S_psi", "S_em", "S_me"]
            },
            "right_species_id": {
                "enum": ["1", "S_e", "S_m", "S_psi", "S_em", "S_me"]
            },
            "line_length_lattice_steps": _INTEGER,
        },
    )
    xcube_cheshire_schema = _object_schema(
        (),
        {
            "axis": {"enum": ["x", "y", "z", "all"]},
            "orientation": {"enum": ["+", "-"]},
            "include_finite_static_reference": _BOOLEAN,
            "finite_reference_line_length": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )

    def registration(
        operation: str,
        summary: str,
        schema,
        handler,
        exactness: Exactness,
        certificate_level: CertificateLevel,
        reason: str,
        constraints: Tuple[Tuple[str, Any], ...] = (),
    ) -> Optional[ServiceRegistration]:
        if operation in existing:
            return None

        def capability(request):
            return ServiceCapability(
                operation=operation,
                supported=True,
                maximum_exactness=exactness,
                backend_fingerprint=request.backend_fingerprint,
                reason=reason,
                maximum_certificate_level=certificate_level,
                input_schema=schema,
                constraints=constraints,
            )

        return ServiceRegistration(
            operation=operation,
            handler=handler,
            capability=capability,
            catalog=ServiceCatalogEntry(
                operation=operation,
                summary=summary,
                input_schema=schema,
                adapter_kind="native",
            ),
        )

    m2_prime = (
        ("requires_macaulay2", True),
        ("uniform_prime_coefficient_field", True),
    )
    flint = (("requires_python_flint", True),)
    specifications = (
        (
            "boundary.halfspace.capabilities",
            "Versioned half-space capability contract.",
            empty_schema,
            halfspace_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            (),
        ),
        (
            "boundary.halfspace.geometry",
            "Primitive-normal and tangent-lattice half-space geometry.",
            geometry_schema,
            halfspace_geometry,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact integer lattice geometry for a rational flat half-space.",
            (),
        ),
        (
            "boundary.halfspace.compare_orientations",
            "Compare two primitive lattice boundary orientations.",
            comparison_schema,
            halfspace_compare_orientations,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact integer orientation comparison; no phase equivalence.",
            (),
        ),
        (
            "boundary.halfspace.contract",
            "Exact one-sided Laurent submodule contraction.",
            bulk_schema,
            halfspace_contract,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact for a finite Laurent presentation over a uniform prime field.",
            m2_prime,
        ),
        (
            "boundary.halfspace.primary",
            "Exact projected-bulk primary boundary subquotient.",
            bulk_schema,
            halfspace_primary,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Primary subquotient only; no generic full boundary module.",
            m2_prime,
        ),
        (
            "boundary.halfspace.free_pairing",
            "Exact invariants of a supplied free boundary pairing.",
            pairing_schema,
            halfspace_free_pairing,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Requires a caller-supplied free tangent-Laurent module.",
            m2_prime,
        ),
        (
            "boundary.halfspace.toric2d",
            "Source-locked Z2 toric half-space benchmark.",
            empty_schema,
            halfspace_toric2d,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact source-locked benchmark.",
            (),
        ),
        (
            "boundary.halfspace.toric3d_primary",
            "Source-locked 3D Z2 toric primary boundary benchmark.",
            empty_schema,
            halfspace_toric3d_primary,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Primary module only; no generic full boundary module.",
            (),
        ),
        (
            "boundary.halfspace.secondary_example",
            "Ruba--Yang secondary-boundary strict-inclusion example.",
            empty_schema,
            halfspace_secondary_example,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact source-locked counterexample to primary equality.",
            (),
        ),
        (
            "boundary.halfspace.xcube_orientation",
            "Orientation-sensitive X-cube source benchmark.",
            normal_schema,
            halfspace_xcube_orientation,
            Exactness.EXPERIMENTAL,
            CertificateLevel.STANDARD,
            "Only registered source orientations carry analytic benchmark data.",
            (),
        ),
        (
            "boundary.completion2d.capabilities",
            "Versioned 2D metric/completion capability contract.",
            empty_schema,
            completion2d_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            (),
        ),
        (
            "boundary.completion2d.metric",
            "Exact finite Abelian metric-group invariants.",
            metric_schema,
            completion2d_metric,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact for an explicit finite metric group.",
            flint,
        ),
        (
            "boundary.completion2d.enumerate",
            "Bounded resumable bosonic/Lagrangian subgroup enumeration.",
            enumerate_metric_schema,
            completion2d_enumerate,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Certified exact only after exhaustion of the recorded finite metric domain.",
            flint,
        ),
        (
            "boundary.completion2d.fold",
            "Fold two finite metric groups across an interface.",
            fold_schema,
            completion2d_fold,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact finite folding; no microscopic completion.",
            flint,
        ),
        (
            "boundary.completion2d.toric_cut",
            "Finite certified rough/smooth Z_d toric cut completion.",
            toric_cut_schema,
            completion2d_toric_cut,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Exact on the explicit finite patch and locality window.",
            flint,
        ),
        (
            "boundary.completion2d.verify",
            "Verify an explicit finite phase-aware 2D boundary completion.",
            explicit_completion_schema,
            completion2d_verify,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Exact only for the supplied finite Hamiltonian and locality domain.",
            flint,
        ),
        (
            "boundary.symbolic3d.capabilities",
            "Versioned bounded E3 capability contract.",
            empty_schema,
            symbolic3d_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software declaration; no enumeration is performed.",
            (),
        ),
        (
            "boundary.symbolic3d.enumerate",
            "Bounded symbolic E3 Laurent-isotropic seed enumeration.",
            symbolic_schema,
            symbolic3d_enumerate,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Complete only inside the recorded finite coefficient and rank bounds.",
            (),
        ),
        (
            "boundary.symbolic3d.toric_primary_preflight",
            "Honest 3D toric primary-only E3 preflight.",
            empty_schema,
            symbolic3d_toric_primary_preflight,
            Exactness.UNSUPPORTED,
            CertificateLevel.STANDARD,
            "Full free boundary module is unavailable; no E3 search is run.",
            (),
        ),
        (
            "boundary.symbolic3d.xcube_preflight",
            "Orientation-aware X-cube E3 preflight.",
            normal_schema,
            symbolic3d_xcube_preflight,
            Exactness.UNSUPPORTED,
            CertificateLevel.STANDARD,
            "Full free boundary module is unavailable; no E3 search is run.",
            (),
        ),
        (
            "defects.capabilities",
            "Versioned finite defect and Cheshire capability contract.",
            empty_schema,
            cheshire_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            (),
        ),
        (
            "defects.cheshire.capabilities",
            "Versioned Cheshire capability contract.",
            empty_schema,
            cheshire_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            (),
        ),
        (
            "defects.cheshire.classify_abelian",
            "Classify folded finite pointed/Abelian interfaces.",
            cheshire_classify_abelian_schema,
            cheshire_classify_abelian,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact only after exhaustive folded-Lagrangian enumeration.",
            flint,
        ),
        (
            "defects.cheshire.toric2d_reference",
            "Complete six-species 2D Z2 toric Cheshire/descendant reference.",
            empty_schema,
            cheshire_toric2d_reference,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Source-locked classification, ordered fusion, and anyon action.",
            flint,
        ),
        (
            "defects.cheshire.fuse",
            "Ordered categorical fusion with 1+1D TQFT-valued coefficients.",
            cheshire_fuse_schema,
            cheshire_fuse,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Currently exact for the six-species 2D Z2 toric reference.",
            (),
        ),
        (
            "defects.cheshire.realize_toric2d",
            "Finite square-lattice realization of one toric defect.",
            cheshire_realize_toric2d_schema,
            cheshire_realize_toric2d,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Exact only for the emitted finite Hamiltonian and support geometry.",
            flint,
        ),
        (
            "defects.cheshire.circuit_toric2d",
            "Replayable finite Clifford creation/deformation/motion/fusion witness.",
            cheshire_circuit_toric2d_schema,
            cheshire_circuit_toric2d,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Exact Pauli conjugation for the emitted finite defect-chain template.",
            (),
        ),
        (
            "defects.cheshire.toric3d_finite_reference",
            "Finite certified 3+1D Z2 toric Cheshire analysis.",
            cheshire_toric3d_finite_reference_schema,
            cheshire_toric3d_finite_reference,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact for the explicitly supplied finite cellulation.",
            flint,
        ),
        (
            "defects.cheshire.xcube_candidates",
            "Three-axis mobility-enriched X-cube support-candidate enumeration.",
            xcube_cheshire_schema,
            cheshire_xcube_candidates,
            Exactness.EXPERIMENTAL,
            CertificateLevel.FULL,
            "Support enumeration only; classification_complete is always false.",
            (),
        ),
    )
    output = []
    for specification in specifications:
        item = registration(*specification)
        if item is not None:
            output.append(item)
    return tuple(output)


def install_boundary_usecase_service_registrations(registrations):
    """Replace migrated retained operations and append the missing ones."""

    canonical = boundary_usecase_service_registrations()
    by_operation = {item.operation: item for item in canonical}
    output = []
    seen = set()
    for item in registrations:
        replacement = by_operation.get(item.operation, item)
        output.append(replacement)
        seen.add(replacement.operation)
    output.extend(
        item for item in canonical if item.operation not in seen
    )
    return tuple(output)


__all__ = [
    "cheshire_capabilities",
    "cheshire_classify_abelian",
    "cheshire_circuit_toric2d",
    "cheshire_fuse",
    "cheshire_realize_toric2d",
    "cheshire_toric2d_reference",
    "cheshire_toric3d_finite_reference",
    "cheshire_xcube_candidates",
    "completion2d_capabilities",
    "completion2d_enumerate",
    "completion2d_fold",
    "completion2d_metric",
    "completion2d_toric_cut",
    "completion2d_verify",
    "halfspace_capabilities",
    "halfspace_compare_orientations",
    "halfspace_contract",
    "halfspace_free_pairing",
    "halfspace_geometry",
    "halfspace_primary",
    "halfspace_secondary_example",
    "halfspace_toric2d",
    "halfspace_toric3d_primary",
    "halfspace_xcube_orientation",
    "symbolic3d_capabilities",
    "symbolic3d_enumerate",
    "symbolic3d_toric_primary_preflight",
    "symbolic3d_xcube_preflight",
    "boundary_usecase_service_registrations",
    "install_boundary_usecase_service_registrations",
]
