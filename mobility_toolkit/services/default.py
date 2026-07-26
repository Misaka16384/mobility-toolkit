"""Default operation catalog and shared Python/CLI/MCP executor.

The adapters in this module are intentionally thin.  Operations implemented
before the canonical service contract are labelled ``legacy_dict_adapter`` and
receive no mathematical certificate merely because their JSON dictionary was
successfully wrapped.  New boundary operations that already return
``ComputationResult`` preserve their exactness and certificates.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Tuple

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    canonical_json,
)
from mobility_toolkit.services.cache import InMemoryServiceCache, ServiceCache
from mobility_toolkit.services.contracts import (
    BackendFingerprint,
    ServiceCapability,
    ServiceCatalogEntry,
    ServiceExecution,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistration, ServiceRegistry


SERVICE_API_VERSION = "1"
SERVICE_CATALOG_SCHEMA_ID = "mobility_toolkit.service_catalog.v1"


def _object_schema(required: Tuple[str, ...], properties: Mapping[str, Any]) -> dict:
    return {
        "additionalProperties": False,
        "properties": dict(properties),
        "required": required,
        "type": "object",
    }


_ARRAY = {"type": "array"}
_INTEGER = {"type": "integer"}
_STRING = {"type": "string"}
_BOOLEAN = {"type": "boolean"}


def _capability(
    operation: str,
    maximum_exactness: Exactness,
    maximum_certificate_level: CertificateLevel,
    reason: str,
    input_schema: Any,
    constraints: Tuple[Tuple[str, Any], ...] = (),
) -> Callable[[ServiceRequest], ServiceCapability]:
    def report(request: ServiceRequest) -> ServiceCapability:
        return ServiceCapability(
            operation=operation,
            supported=True,
            maximum_exactness=maximum_exactness,
            backend_fingerprint=request.backend_fingerprint,
            reason=reason,
            maximum_certificate_level=maximum_certificate_level,
            input_schema=input_schema,
            constraints=constraints,
        )

    return report


def _legacy_result(
    request: ServiceRequest,
    value: Any,
    algorithm: str,
    theorem_scope: str,
    warnings: Tuple[str, ...] = (),
) -> ComputationResult:
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=value,
        exactness=Exactness.EXPERIMENTAL,
        assumptions=request.assumptions,
        theorem_scope=theorem_scope,
        certificate_level=CertificateLevel.NONE,
        verification=(
            ("legacy_dict_faithfully_wrapped", True),
            ("mathematical_certificate_added_by_adapter", False),
        ),
        backend_provenance=BackendProvenance(
            backend="legacy-python-api",
            algorithm=algorithm,
            version=SERVICE_API_VERSION,
        ),
        warnings=(
            "This adapter preserves a legacy JSON computation. Its transport "
            "wrapper is canonical, but the wrapper is not a mathematical certificate.",
        )
        + warnings,
        schema_version=request.schema_version,
    )


def _reframe_native(
    request: ServiceRequest, source: ComputationResult
) -> ComputationResult:
    """Bind an existing native result to the public service request identity."""

    verification = tuple(source.verification) + (
        ("source_assumptions", source.assumptions),
        ("source_input_hash", source.canonical_input_hash),
        ("source_operation", source.operation),
    )
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=source.value,
        exactness=source.exactness,
        assumptions=request.assumptions,
        theorem_scope=source.theorem_scope,
        certificate_level=source.certificate_level,
        certificate=source.certificate,
        verification=verification,
        backend_provenance=source.backend_provenance,
        resource_usage=source.resource_usage,
        diagnostics=source.diagnostics,
        warnings=source.warnings,
        schema_version=request.schema_version,
    )


def _homology(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.homology import compute_ext_krull

    data = _input_object(request)
    if "prime_bypass" in data:
        raise ValueError("prime_bypass has been removed from the public service")
    value = compute_ext_krull(
        data["stabilizer"],
        data["qudit_dim"],
        p_ext=data.get("p_ext", 0),
        spatial_dim=data.get("spatial_dim"),
        validate_stabilizer=data.get("validate_stabilizer", True),
        saturated=data.get("saturated"),
    )
    return _legacy_result(
        request,
        value,
        "compute_ext_krull",
        "Legacy Ruba--Yang Ext computation; consult the returned theorem-scope fields.",
    )


def _translation_lattice(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.mobility import compute_translation_lattice

    data = _input_object(request)
    value = compute_translation_lattice(
        data["generators"], data["qudit_dim"], data.get("variables")
    )
    return _legacy_result(
        request,
        value,
        "compute_translation_lattice",
        "Exact only for the Laurent-binomial domain recognized by the legacy result.",
    )


def _classify(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.physics import classify_mobility

    data = _input_object(request)
    value = classify_mobility(
        data["krull_dim"],
        data.get("spatial_dim", 3),
        p_ext=data.get("p_ext", 0),
        assumptions=dict(data.get("physics_assumptions", {})),
    )
    return _legacy_result(
        request,
        value,
        "classify_mobility",
        "Theorem-scoped classification; no planon/lineon/fracton label is inferred "
        "from Krull dimension alone.",
    )


def _periodic_gsd(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.grobner import compute_gsd_and_periodicity

    data = _input_object(request)
    value = compute_gsd_and_periodicity(
        data["stabilizer"],
        data.get("Lx"),
        data.get("Ly"),
        data["qudit_dim"],
        data.get("L"),
    )
    return _legacy_result(
        request,
        value,
        "compute_gsd_and_periodicity",
        "Finite-torus GSD and periodicity in the domain reported by the legacy result.",
    )


def _fusion_interference(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.fusion import analyze_fusion_interference

    data = _input_object(request)
    value = analyze_fusion_interference(
        data["stabilizer"], data["qudit_dim"], data["shifts"]
    )
    return _legacy_result(
        request,
        value,
        "analyze_fusion_interference",
        "Finite list of caller-supplied relative shifts; no completeness beyond them.",
    )


def _sset_fusion(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.fusion import solve_sset_fusion

    data = _input_object(request)
    return _legacy_result(
        request,
        solve_sset_fusion(data["poly_f"], data["poly_g"]),
        "solve_sset_fusion",
        "Legacy polynomial SSET fusion computation.",
    )


def _annihilator_fusion(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.fusion import analyze_annihilator_fusion

    data = _input_object(request)
    if "prime_bypass" in data:
        raise ValueError("prime_bypass has been removed from the public service")
    return _legacy_result(
        request,
        analyze_annihilator_fusion(
            data["generators"],
            data["qudit_dim"],
            data.get("variables"),
            False,
        ),
        "analyze_annihilator_fusion",
        "Prime-characteristic annihilator fusion in the legacy implementation domain.",
    )


def _search_models(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.search import search_koszul_models

    data = _input_object(request)
    return _legacy_result(
        request,
        search_koszul_models(
            data["qudit_dim"], data["target_dim"], data.get("max_trials", 100)
        ),
        "search_koszul_models",
        "Bounded randomized search; absence from the output is not a nonexistence proof.",
        ("Randomized search results are intentionally not cached.",),
    )


def _boundary_gauge(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_gauge.boundary.pipeline import (
        run_algorithm_1_boundary_ops_2d,
        run_algorithm_1_boundary_ops_3d,
    )

    data = _input_object(request)
    dimension = data["dim"]
    kwargs = {
        "Lx": data["Lx"],
        "Ly": data["Ly"],
        "q": data["q"],
        "d": data["d"],
        "wx": data["wx"],
        "wy": data["wy"],
        "stabilizer_generators": data["stabilizer_generators"],
        "qudit_positions": data["qudit_positions"],
        "boundary": data.get("boundary", "bottom"),
    }
    if dimension == 2:
        raw = run_algorithm_1_boundary_ops_2d(**kwargs)
    elif dimension == 3:
        if data.get("Lz") is None or data.get("wz") is None:
            raise ValueError("Lz and wz are required for dim=3")
        raw = run_algorithm_1_boundary_ops_3d(
            Lz=data["Lz"], wz=data["wz"], **kwargs
        )
    else:
        raise ValueError("dim must be 2 or 3")
    bulk_stabilizers, boundary_ops, stabilizer_matrix = raw
    value = {
        "bulk_stabilizers": [
            {str(key): list(entry) for key, entry in stabilizer.items()}
            for stabilizer in bulk_stabilizers
        ],
        "boundary_operators": boundary_ops.tolist(),
        "stabilizer_matrix": stabilizer_matrix.tolist(),
    }
    return _legacy_result(
        request,
        value,
        "algorithm_1_boundary_gauge",
        "Finite truncation of Algorithm 1 at the explicit system and patch sizes. "
        "No stabilization or thermodynamic completeness follows.",
        ("The former public tuple transport is not exposed by this service.",),
    )


def _halfspace_capabilities(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import halfspace_capability_report

    report = halfspace_capability_report()
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=report,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope="Software capability declaration, not a physical classification.",
        certificate_level=CertificateLevel.STANDARD,
        certificate=report,
        verification=(("capability_contract_constructed", True),),
        backend_provenance=BackendProvenance(
            "internal-contract", "halfspace_capability_report", SERVICE_API_VERSION
        ),
        schema_version=request.schema_version,
    )


def _toric2d_halfspace(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        toric_z2_y_nonnegative_boundary_module,
    )

    return _reframe_native(request, toric_z2_y_nonnegative_boundary_module())


def _toric3d_halfspace(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        toric3d_z2_z_nonnegative_primary_benchmark,
    )

    return _reframe_native(request, toric3d_z2_z_nonnegative_primary_benchmark())


def _xcube_orientation(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary_halfspace import (
        PrimitiveNormal,
        xcube_orientation_benchmark,
    )

    data = _input_object(request)
    normal = PrimitiveNormal.from_integer(data["normal"])
    return _reframe_native(request, xcube_orientation_benchmark(normal))


def _toric_symbolic3d_preflight(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary import toric3d_primary_symbolic_crosscheck

    return _reframe_native(request, toric3d_primary_symbolic_crosscheck())


def _xcube_symbolic3d_preflight(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary import xcube_symbolic_orientation_crosscheck

    data = _input_object(request)
    return _reframe_native(
        request, xcube_symbolic_orientation_crosscheck(tuple(data["normal"]))
    )


def _toric2d_completion(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.completion2d import (
        verify_local_boundary_completion,
        zd_toric_cut_completion_benchmark,
    )
    from mobility_toolkit.finite import FlintIntegerBackend

    data = _input_object(request)
    backend = FlintIntegerBackend(
        max_dense_entries=data.get("max_dense_entries", 2_000_000)
    )
    benchmark = zd_toric_cut_completion_benchmark(
        data["modulus"], data["boundary_kind"], backend
    )
    source = verify_local_boundary_completion(benchmark.request, backend)
    return _reframe_native(request, source)


def _boundary_enumeration_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "e1_finite_subgroups": {
            "availability": "python_api",
            "exactness": "certified_exact_for_declared_finite_paired_group",
            "service_adapter": False,
        },
        "e2_bounded_periodic": {
            "availability": "python_api",
            "exactness": "bounded_exact_for_declared_support_period_and_ancilla_domain",
            "service_adapter": False,
        },
        "e3_symbolic3d": {
            "availability": "python_api_and_mt_gapped_boundary_3d_skill",
            "exactness": "bounded_exact_only_after_complete_page",
            "equivalence": "generator_change_and_common_monomial_translation_only",
            "service_adapter": False,
        },
        "unsupported": (
            "thermodynamic completeness",
            "generic saturation",
            "automatic anomaly cancellation",
            "automatic local completion",
        ),
    }
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope="Software capability declaration; it does not enumerate candidates.",
        certificate_level=CertificateLevel.STANDARD,
        certificate=value,
        verification=(("declared_operations_importable", True),),
        backend_provenance=BackendProvenance(
            "internal-contract", "boundary-enumeration-capabilities", SERVICE_API_VERSION
        ),
        schema_version=request.schema_version,
    )


def _finite_code_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "finite_abelian_groups": "certified_exact_with_python_flint",
        "composite_modulus": True,
        "mixed_local_dimensions": True,
        "finite_stabilizer_analysis": "certified_exact",
        "phase_aware_pauli_arithmetic": True,
        "dense_materialization_guard": True,
        "optional_backend": "python-flint",
        "registered_operations": ("finite.code.analyze",),
        "transport_semantics": "site-labelled sparse x/z terms with explicit phase",
    }
    return _capability_contract_result(
        request,
        value,
        "finite-code-capabilities",
        "Software capability declaration for finite Abelian and finite stabilizer APIs.",
    )


def _finite_boundary_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
        "finite_boundary_algebra": "certified_exact_for_supplied_finite_code_and_cut",
        "primary_projection_compiler": "certified_exact_finite",
        "e1_subgroups": "certified_exact_for_declared_finite_paired_group",
        "e2_bounded_periodic": (
            "bounded_exact_for_declared_support_period_and_ancilla_domain"
        ),
        "registered_operations": (
            "boundary.finite.analyze",
            "boundary.finite.enumerate_e1",
            "boundary.finite.e2.reference_z2_swap",
        ),
        "generic_e2_transport_decoder": False,
        "e2_transport_reference": "source_locked_two_site_z2_tangent_swap",
        "local_2d_completion": "bounded_exact_for_explicit_metric_and_string_lifts",
        "automatic_anyon_extraction": "unsupported",
        "thermodynamic_completeness": "unsupported",
    }
    return _capability_contract_result(
        request,
        value,
        "finite-boundary-capabilities",
        "Software capability declaration; finite and thermodynamic scopes remain distinct.",
    )


def _relative_homology(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.core import SparseIntMatrix
    from mobility_toolkit.geometry import (
        FiniteCellComplex,
        RelativeCellularPair,
        relative_cellular_homology,
        verify_relative_chain_certificate,
        verify_relative_homology_result,
    )

    data = _input_object(request)
    ambient_data = data["ambient"]
    cells = tuple(
        tuple(level) for level in ambient_data["cell_ids_by_dimension"]
    )
    boundaries = tuple(
        SparseIntMatrix(
            matrix["nrows"],
            matrix["ncols"],
            tuple(tuple(entry) for entry in matrix.get("entries", ())),
        )
        for matrix in ambient_data["boundary_maps"]
    )
    ambient = FiniteCellComplex(
        cells,
        boundaries,
        tuple(ambient_data.get("assumptions", ())),
    )
    pair = RelativeCellularPair.create(
        ambient, data["subcomplex_cell_ids_by_dimension"]
    )
    backend = _finite_backend(data)
    result = relative_cellular_homology(
        pair,
        data["degree"],
        data["coefficient_modulus"],
        backend,
    )
    verify_relative_chain_certificate(
        pair, result.relative_chain_complex.certificate
    )
    verify_relative_homology_result(result, backend)
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=result,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=(
            "Exact cellular relative homology H_degree(X,A;Z/N) for the explicitly "
            "supplied finite boundary-closed cellular pair. This is not a Laurent "
            "half-space computation and not Ext_R(M,R/I)."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate={
            "homology": result.certificate,
            "relative_chain": result.relative_chain_complex.certificate,
        },
        verification=(
            ("boundary_closed_subcomplex_verified", True),
            ("homology_invariant_factors_match_certificate", (
                result.invariant_factors == result.certificate.invariant_factors
            )),
            ("relative_chain_certificate_replayed", True),
            ("relative_homology_semantic_replay_verified", True),
        ),
        backend_provenance=BackendProvenance(
            getattr(backend, "name", backend.__class__.__name__),
            "finite-cellular-relative-homology",
            getattr(backend, "version", ""),
            (("max_dense_entries", getattr(backend, "max_dense_entries", None)),),
        ),
        warnings=(
            "Relative homology classes require a separate code-specific dictionary "
            "before they are called logical operators or boundary excitations.",
        ),
        schema_version=request.schema_version,
    )


def _capability_contract_result(
    request: ServiceRequest,
    value: Any,
    algorithm: str,
    theorem_scope: str,
) -> ComputationResult:
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=theorem_scope,
        certificate_level=CertificateLevel.STANDARD,
        certificate=value,
        verification=(("capability_contract_constructed", True),),
        backend_provenance=BackendProvenance(
            "internal-contract", algorithm, SERVICE_API_VERSION
        ),
        schema_version=request.schema_version,
    )


def _cheshire_capabilities(request: ServiceRequest) -> ComputationResult:
    value = {
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
    return _capability_contract_result(
        request,
        value,
        "cheshire-capabilities",
        "Software capability declaration, not a Cheshire phase theorem.",
    )


def _cheshire_domain(data: Mapping[str, Any], defect_key: str = "defects"):
    from mobility_toolkit.defects import ClosedLoop, OpenSegment
    from mobility_toolkit.geometry import rectangular_cubical_complex

    shape = tuple(data["shape"])
    if len(shape) != 3:
        raise ValueError("shape must contain exactly three lengths")
    complex_ = rectangular_cubical_complex(
        shape, periodic_axes=tuple(data.get("periodic_axes", ()))
    )
    defects = []
    for item in data[defect_key]:
        arguments = (
            complex_,
            item["defect_id"],
            tuple(tuple(base) for base in item["cube_bases"]),
        )
        topology = item["topology"]
        if topology == "open_segment":
            defects.append(OpenSegment.from_cube_bases(*arguments))
        elif topology == "closed_loop":
            defects.append(ClosedLoop.from_cube_bases(*arguments))
        else:
            raise ValueError("topology must be open_segment or closed_loop")
    if not defects:
        raise ValueError("at least one defect is required")
    return complex_, tuple(defects)


def _finite_backend(data: Mapping[str, Any]):
    from mobility_toolkit.finite import FlintIntegerBackend

    return FlintIntegerBackend(
        max_dense_entries=data.get("max_dense_entries", 2_000_000)
    )


def _cheshire_static(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import analyze_toric_cheshire

    data = _input_object(request)
    complex_, defects = _cheshire_domain(data)
    analysis = analyze_toric_cheshire(
        complex_,
        defects,
        _finite_backend(data),
        tube_radius_lattice_steps=data.get("tube_radius_lattice_steps", 0),
    )
    certificate = {
        "defect_transformations": tuple(
            report.transformation_certificate for report in analysis.defect_reports
        ),
        "pinned_elimination": analysis.pinned_elimination_certificate,
        "tube_representation": analysis.tubular_deleted_representation.certificate,
    }
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=analysis,
        exactness=analysis.exactness,
        assumptions=request.assumptions,
        theorem_scope=analysis.theorem_scope,
        certificate_level=analysis.certificate_level,
        certificate=certificate,
        verification=(
            ("source_assumptions", analysis.assumptions),
            ("static_finite_certificates_verified", True),
        ),
        backend_provenance=analysis.backend_provenance,
        schema_version=request.schema_version,
    )


def _cheshire_synthesis(request: ServiceRequest) -> ComputationResult:
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
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=synthesis,
        exactness=synthesis.exactness,
        assumptions=request.assumptions,
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
        backend_provenance=source.backend_provenance,
        schema_version=request.schema_version,
    )


def _cheshire_species(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.defects import (
        enumerate_cheshire_species,
        toric_cheshire_condensation_candidate,
        verify_cheshire_species_enumeration,
    )
    from mobility_toolkit.geometry import rectangular_cubical_complex

    data = _input_object(request)
    shape = tuple(data["shape"])
    complex_ = rectangular_cubical_complex(
        shape, periodic_axes=tuple(data.get("periodic_axes", ()))
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
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=enumeration,
        exactness=Exactness.BOUNDED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=(
            "Complete only for the explicitly supplied finite candidate list and radii."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=enumeration.certificate,
        verification=(("semantic_transcript_replay_verified", verified),),
        backend_provenance=provenance,
        schema_version=request.schema_version,
    )


def _cheshire_fusion(request: ServiceRequest) -> ComputationResult:
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
        tube_radius_lattice_steps=data.get("tube_radius_lattice_steps", 0),
    )
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=fusion,
        exactness=fusion.static_candidate_exactness,
        assumptions=request.assumptions,
        theorem_scope=fusion.theorem_scope,
        certificate_level=fusion.certificate_level,
        certificate=fusion.certificate,
        verification=(
            ("finite_depth_circuit_constructed", False),
            ("static_fusion_certificate_verified", fusion.certificate.structurally_verified),
        ),
        backend_provenance=fusion.before_analysis.backend_provenance,
        schema_version=request.schema_version,
    )


def _xcube_cheshire_reference(request: ServiceRequest) -> ComputationResult:
    from dataclasses import replace

    from mobility_toolkit.boundary_halfspace import PrimitiveNormal
    from mobility_toolkit.defects import (
        analyze_xcube_fracton_line_reference,
        xcube_axial_line_reference_request,
    )

    data = _input_object(request)
    source_request = xcube_axial_line_reference_request(
        data.get("line_length_lattice_steps", 1)
    )
    if "normal" in data:
        source_request = replace(
            source_request,
            normal=PrimitiveNormal.from_integer(tuple(data["normal"])),
        )
    source = analyze_xcube_fracton_line_reference(
        source_request, _finite_backend(data)
    )
    return _reframe_native(request, source)


def _input_object(request: ServiceRequest) -> Mapping[str, Any]:
    if not isinstance(request.input_data, Mapping):
        raise TypeError("operation input_data must be a JSON object")
    return request.input_data


def _registration(
    operation: str,
    summary: str,
    input_schema: Any,
    handler: Callable[[ServiceRequest], ComputationResult],
    exactness: Exactness,
    certificate_level: CertificateLevel,
    reason: str,
    adapter_kind: str,
    cacheable: bool = True,
    constraints: Tuple[Tuple[str, Any], ...] = (),
) -> ServiceRegistration:
    return ServiceRegistration(
        operation=operation,
        handler=handler,
        capability=_capability(
            operation,
            exactness,
            certificate_level,
            reason,
            input_schema,
            constraints,
        ),
        catalog=ServiceCatalogEntry(
            operation=operation,
            summary=summary,
            input_schema=input_schema,
            adapter_kind=adapter_kind,
            cacheable=cacheable,
        ),
    )


def build_default_registry() -> ServiceRegistry:
    """Build a fresh deterministic registry without importing optional backends."""

    homology_schema = _object_schema(
        ("stabilizer", "qudit_dim"),
        {
            "stabilizer": _ARRAY,
            "qudit_dim": _INTEGER,
            "p_ext": _INTEGER,
            "spatial_dim": {"type": ["integer", "null"]},
            "validate_stabilizer": _BOOLEAN,
            "saturated": {"type": ["boolean", "null"]},
        },
    )
    translation_schema = _object_schema(
        ("generators", "qudit_dim"),
        {"generators": _ARRAY, "qudit_dim": _INTEGER, "variables": _ARRAY},
    )
    classify_schema = _object_schema(
        ("krull_dim",),
        {
            "krull_dim": _INTEGER,
            "spatial_dim": _INTEGER,
            "p_ext": _INTEGER,
            "physics_assumptions": {"type": "object"},
        },
    )
    periodic_schema = _object_schema(
        ("stabilizer", "qudit_dim"),
        {
            "stabilizer": _ARRAY,
            "qudit_dim": _INTEGER,
            "Lx": _INTEGER,
            "Ly": _INTEGER,
            "L": _ARRAY,
        },
    )
    fusion_schema = _object_schema(
        ("stabilizer", "qudit_dim", "shifts"),
        {"stabilizer": _ARRAY, "qudit_dim": _INTEGER, "shifts": _ARRAY},
    )
    sset_schema = _object_schema(
        ("poly_f", "poly_g"), {"poly_f": _STRING, "poly_g": _STRING}
    )
    annihilator_schema = _object_schema(
        ("generators", "qudit_dim"),
        {"generators": _ARRAY, "qudit_dim": _INTEGER, "variables": _ARRAY},
    )
    search_schema = _object_schema(
        ("qudit_dim", "target_dim"),
        {
            "qudit_dim": _INTEGER,
            "target_dim": _INTEGER,
            "max_trials": _INTEGER,
        },
    )
    boundary_gauge_schema = _object_schema(
        (
            "dim",
            "Lx",
            "Ly",
            "q",
            "d",
            "wx",
            "wy",
            "stabilizer_generators",
            "qudit_positions",
        ),
        {
            "dim": _INTEGER,
            "Lx": _INTEGER,
            "Ly": _INTEGER,
            "Lz": {"type": ["integer", "null"]},
            "q": _INTEGER,
            "d": _INTEGER,
            "wx": _INTEGER,
            "wy": _INTEGER,
            "wz": {"type": ["integer", "null"]},
            "stabilizer_generators": _ARRAY,
            "qudit_positions": _ARRAY,
            "boundary": {"enum": ["bottom", "top"]},
        },
    )
    empty_schema = _object_schema((), {})
    normal_schema = _object_schema(("normal",), {"normal": _ARRAY})
    completion_schema = _object_schema(
        ("modulus", "boundary_kind"),
        {
            "modulus": _INTEGER,
            "boundary_kind": {"enum": ["rough", "smooth"]},
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_static_schema = _object_schema(
        ("shape", "defects"),
        {
            "shape": _ARRAY,
            "periodic_axes": _ARRAY,
            "defects": _ARRAY,
            "tube_radius_lattice_steps": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_synthesis_schema = _object_schema(
        ("shape", "defects", "radii"),
        {
            "shape": _ARRAY,
            "periodic_axes": _ARRAY,
            "defects": _ARRAY,
            "radii": _ARRAY,
            "candidate_id": _STRING,
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_species_schema = _object_schema(
        ("shape", "candidate_sets", "radii"),
        {
            "shape": _ARRAY,
            "periodic_axes": _ARRAY,
            "candidate_sets": _ARRAY,
            "radii": _ARRAY,
            "max_dense_entries": _INTEGER,
        },
    )
    cheshire_fusion_schema = _object_schema(
        ("fusion_id", "shape", "before_defects", "after_defects"),
        {
            "fusion_id": _STRING,
            "shape": _ARRAY,
            "periodic_axes": _ARRAY,
            "before_defects": _ARRAY,
            "after_defects": _ARRAY,
            "tube_radius_lattice_steps": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )
    xcube_cheshire_schema = _object_schema(
        (),
        {
            "line_length_lattice_steps": _INTEGER,
            "normal": _ARRAY,
            "max_dense_entries": _INTEGER,
        },
    )
    relative_homology_schema = _object_schema(
        (
            "ambient",
            "subcomplex_cell_ids_by_dimension",
            "degree",
            "coefficient_modulus",
        ),
        {
            "ambient": {
                "additionalProperties": False,
                "properties": {
                    "assumptions": _ARRAY,
                    "boundary_maps": _ARRAY,
                    "cell_ids_by_dimension": _ARRAY,
                },
                "required": ["cell_ids_by_dimension", "boundary_maps"],
                "type": "object",
            },
            "subcomplex_cell_ids_by_dimension": _ARRAY,
            "degree": _INTEGER,
            "coefficient_modulus": _INTEGER,
            "max_dense_entries": _INTEGER,
        },
    )

    legacy = "legacy_dict_adapter"
    native = "native"
    registrations = (
        _registration(
            "homology.ext",
            "Ruba--Yang Ext charge-module computation.",
            homology_schema,
            _homology,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter; inspect result fields for theorem scope.",
            legacy,
            constraints=(
                ("requires_macaulay2", True),
                ("uniform_prime_qudit_dimension", True),
            ),
        ),
        _registration(
            "mobility.translation_lattice",
            "Translation lattice for Laurent-binomial annihilators.",
            translation_schema,
            _translation_lattice,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter with domain-dependent exactness.",
            legacy,
        ),
        _registration(
            "mobility.classify",
            "Theorem-scoped interpretation of a charge-module Krull dimension.",
            classify_schema,
            _classify,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter; classification remains theorem scoped.",
            legacy,
        ),
        _registration(
            "periodic.gsd",
            "Finite-torus GSD and periodicity computation.",
            periodic_schema,
            _periodic_gsd,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter backed by Macaulay2.",
            legacy,
            constraints=(("requires_macaulay2", True),),
        ),
        _registration(
            "fusion.interference",
            "Dimension drops under explicit relative shifts.",
            fusion_schema,
            _fusion_interference,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter backed by Macaulay2.",
            legacy,
            constraints=(("requires_macaulay2", True),),
        ),
        _registration(
            "fusion.sset",
            "Polynomial SSET fusion computation.",
            sset_schema,
            _sset_fusion,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter.",
            legacy,
        ),
        _registration(
            "fusion.annihilator",
            "Annihilator-ideal fusion over a prime coefficient field.",
            annihilator_schema,
            _annihilator_fusion,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Legacy dictionary adapter; a uniform prime coefficient field is required.",
            legacy,
            constraints=(
                ("requires_macaulay2", True),
                ("uniform_prime_qudit_dimension", True),
            ),
        ),
        _registration(
            "models.search",
            "Bounded randomized Koszul-model search.",
            search_schema,
            _search_models,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Randomized bounded search; nonexistence is not certified.",
            legacy,
            cacheable=False,
        ),
        _registration(
            "boundary.gauge.algorithm1",
            "Finite 2D/3D Algorithm 1 boundary-gauge truncation.",
            boundary_gauge_schema,
            _boundary_gauge,
            Exactness.EXPERIMENTAL,
            CertificateLevel.NONE,
            "Finite truncation only; no stabilization certificate is synthesized.",
            legacy,
        ),
        _registration(
            "boundary.halfspace.capabilities",
            "Machine-readable half-space capability contract.",
            empty_schema,
            _halfspace_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            native,
        ),
        _registration(
            "boundary.halfspace.toric2d",
            "Certified Z2 toric y>=0 half-space boundary module benchmark.",
            empty_schema,
            _toric2d_halfspace,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Source-locked native benchmark.",
            native,
        ),
        _registration(
            "boundary.halfspace.toric3d_primary",
            "Certified 3D Z2 toric z>=0 primary subquotient benchmark.",
            empty_schema,
            _toric3d_halfspace,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Primary module only; no generic full boundary module is claimed.",
            native,
        ),
        _registration(
            "boundary.halfspace.xcube_orientation",
            "Orientation-sensitive X-cube source-locked benchmark.",
            normal_schema,
            _xcube_orientation,
            Exactness.EXPERIMENTAL,
            CertificateLevel.STANDARD,
            "Only registered source orientations return analytic benchmark data.",
            native,
        ),
        _registration(
            "boundary.symbolic3d.toric_primary_preflight",
            "Refusal/capability preflight for the 3D toric primary module.",
            empty_schema,
            _toric_symbolic3d_preflight,
            Exactness.UNSUPPORTED,
            CertificateLevel.STANDARD,
            "Full free boundary module is unavailable; no E3 search is run.",
            native,
        ),
        _registration(
            "boundary.symbolic3d.xcube_preflight",
            "Orientation-aware refusal/capability preflight for X-cube E3.",
            normal_schema,
            _xcube_symbolic3d_preflight,
            Exactness.UNSUPPORTED,
            CertificateLevel.STANDARD,
            "Full free boundary module is unavailable; no E3 search is run.",
            native,
        ),
        _registration(
            "boundary.completion2d.toric_cut",
            "Finite certified rough/smooth Z_d toric cut completion.",
            completion_schema,
            _toric2d_completion,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Exact on the explicit finite patch and locality window.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "finite.code.capabilities",
            "Machine-readable finite-code arithmetic and solver capabilities.",
            empty_schema,
            _finite_code_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            native,
        ),
        _registration(
            "boundary.finite.capabilities",
            "Machine-readable finite boundary/compiler/enumerator capabilities.",
            empty_schema,
            _finite_boundary_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration with bounded scopes.",
            native,
        ),
        _registration(
            "boundary.enumeration.capabilities",
            "Machine-readable E1/E2/E3 boundary-enumeration capabilities.",
            empty_schema,
            _boundary_enumeration_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software declaration; this operation performs no enumeration.",
            native,
        ),
        _registration(
            "topology.relative_homology",
            "Exact cellular relative homology of an explicit finite pair.",
            relative_homology_schema,
            _relative_homology,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact for the explicitly supplied finite boundary-closed cellular pair.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "defects.capabilities",
            "Machine-readable finite defect and Cheshire capabilities.",
            empty_schema,
            _cheshire_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            native,
        ),
        _registration(
            "defects.cheshire.capabilities",
            "Machine-readable Cheshire static/synthesis/fusion capabilities.",
            empty_schema,
            _cheshire_capabilities,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact software capability declaration.",
            native,
        ),
        _registration(
            "defects.cheshire.static_toric",
            "Finite certified 3+1D Z2 toric Cheshire line analysis.",
            cheshire_static_schema,
            _cheshire_static,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.STANDARD,
            "Exact for the explicitly supplied finite cellulation and defect.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "defects.cheshire.synthesize_toric",
            "Bounded tube-to-line synthesis over explicit finite radii.",
            cheshire_synthesis_schema,
            _cheshire_synthesis,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Finite invariants only; no circuit or phase equivalence is claimed.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "defects.cheshire.enumerate_toric",
            "Bounded enumeration over an explicit finite candidate list and radii.",
            cheshire_species_schema,
            _cheshire_species,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Complete only for the supplied candidate list and finite radii.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "defects.cheshire.fuse_toric_static",
            "Certified finite before/after static Cheshire fusion candidate.",
            cheshire_fusion_schema,
            _cheshire_fusion,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Static finite data only; finite-depth fusion circuit is unsupported.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
        _registration(
            "defects.cheshire.xcube_axial_reference",
            "Experimental X-cube axial line reference with exact finite data.",
            xcube_cheshire_schema,
            _xcube_cheshire_reference,
            Exactness.EXPERIMENTAL,
            CertificateLevel.STANDARD,
            "Finite reference candidate; no condensation or thermodynamic theorem.",
            native,
            constraints=(("requires_python_flint", True),),
        ),
    )
    from mobility_toolkit.services.finite_boundary_operations import (
        finite_boundary_service_registrations,
    )

    registrations = registrations + finite_boundary_service_registrations()
    from mobility_toolkit.services.boundary_usecases import (
        install_boundary_usecase_service_registrations,
    )

    registrations = install_boundary_usecase_service_registrations(
        registrations
    )
    from mobility_toolkit.services.periodic_operations import (
        periodic_service_registrations,
    )

    registrations = registrations + periodic_service_registrations()
    return ServiceRegistry(registrations)


class ServiceExecutor:
    """Caller-owned executor with a validated canonical-result cache."""

    def __init__(
        self,
        registry: Optional[ServiceRegistry] = None,
        cache: Optional[ServiceCache] = None,
    ) -> None:
        self.registry = registry if registry is not None else build_default_registry()
        self.cache = cache if cache is not None else InMemoryServiceCache()

    def execute(self, request: ServiceRequest) -> ServiceExecution:
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be a ServiceRequest")
        self._validate_input_shape(request)
        capability = self.registry.capability(request)
        if capability is None:
            raise RuntimeError(
                f"operation {request.operation!r} lacks a capability contract"
            )
        backend_sensitive = any(
            name.startswith("requires_") and bool(value)
            for name, value in capability.constraints
        )
        cacheable = self.registry.is_cacheable(request.operation) and (
            not backend_sensitive or request.backend_fingerprint is not None
        )
        if cacheable:
            cached = self.cache.get(request)
            if cached is not None:
                self.registry.validate_result(request, cached)
                return ServiceExecution(request, capability, cached, cache_hit=True)
        result = self.registry.dispatch(request)
        if cacheable:
            self.cache.put(request, result)
        return ServiceExecution(request, capability, result, cache_hit=False)

    def _validate_input_shape(self, request: ServiceRequest) -> None:
        entry = self.registry.catalog_entry(request.operation)
        if entry is None or not isinstance(entry.input_schema, Mapping):
            return
        schema = entry.input_schema
        if schema.get("type") != "object":
            return
        data = _input_object(request)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(data) - set(properties))
            if unknown:
                raise ValueError(
                    f"unknown input_data fields for {request.operation}: "
                    + ", ".join(unknown)
                )
        missing = [name for name in schema.get("required", ()) if name not in data]
        if missing:
            raise ValueError(
                f"missing input_data fields for {request.operation}: "
                + ", ".join(missing)
            )

    def catalog(self) -> dict:
        entries = []
        for entry in self.registry.catalog_entries:
            probe = ServiceRequest(entry.operation, {})
            capability = self.registry.capability(probe)
            entries.append(
                {
                    "capability": capability,
                    "operation": entry,
                }
            )
        return json.loads(
            canonical_json(
                {
                    "operations": entries,
                    "schema": SERVICE_CATALOG_SCHEMA_ID,
                    "service_api_version": SERVICE_API_VERSION,
                }
            )
        )


_DEFAULT_EXECUTOR = ServiceExecutor()


def execute_service_request(request: ServiceRequest) -> ServiceExecution:
    """Execute a canonical request through the process-local default executor."""

    return _DEFAULT_EXECUTOR.execute(request)


def execute_service_payload(payload: Mapping[str, Any]) -> dict:
    """Shared JSON adapter used verbatim by the generic CLI and MCP tool."""

    request = ServiceRequest.from_transport_dict(payload)
    return execute_service_request(request).to_transport_dict()


def default_service_catalog() -> dict:
    return _DEFAULT_EXECUTOR.catalog()


__all__ = [
    "SERVICE_API_VERSION",
    "SERVICE_CATALOG_SCHEMA_ID",
    "ServiceExecutor",
    "build_default_registry",
    "default_service_catalog",
    "execute_service_payload",
    "execute_service_request",
]
