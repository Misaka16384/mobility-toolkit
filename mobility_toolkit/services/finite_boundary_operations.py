"""Canonical finite-code and finite-boundary service operations.

The JSON representation is semantic and phase aware:

* every local system is ``{"site_id": ..., "dimension": ...}``;
* every generator has an explicit central ``phase``;
* every sparse local term is ``{"site_id": ..., "x": ..., "z": ...}``.

There is deliberately no flat Pauli vector, uniform ``qudit_dim``, or
``prime_bypass`` option.  Different sites may have different composite cyclic
dimensions.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    LocalPauliTerm,
    LocalSystem,
    PauliModule,
)
from mobility_toolkit.services.contracts import (
    ServiceCapability,
    ServiceCatalogEntry,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistration


# JSON-schema fragments are descriptive as well as enforced by the strict
# recursive decoders below.
SITE_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "dimension": {"minimum": 2, "type": "integer"},
        "site_id": {"minLength": 1, "type": "string"},
    },
    "required": ["site_id", "dimension"],
    "type": "object",
}
TERM_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "site_id": {"minLength": 1, "type": "string"},
        "x": {"type": "integer"},
        "z": {"type": "integer"},
    },
    "required": ["site_id", "x", "z"],
    "type": "object",
}
GENERATOR_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "phase": {"type": "integer"},
        "terms": {"items": TERM_SCHEMA, "type": "array"},
    },
    "required": ["phase", "terms"],
    "type": "object",
}
WINDOW_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "search_extent": {
            "items": {
                "additionalProperties": False,
                "properties": {
                    "name": {"minLength": 1, "type": "string"},
                    "value": {"type": "integer"},
                },
                "required": ["name", "value"],
                "type": "object",
            },
            "type": "array",
        },
        "site_ids": {"items": {"type": "string"}, "type": "array"},
        "window_id": {"minLength": 1, "type": "string"},
    },
    "required": ["window_id", "site_ids"],
    "type": "object",
}
BUDGET_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "max_elements": {"minimum": 1, "type": "integer"},
        "max_phase_assignments": {"minimum": 1, "type": "integer"},
        "max_results": {"minimum": 1, "type": "integer"},
        "max_subgroups": {"minimum": 1, "type": "integer"},
        "max_work_units": {"minimum": 1, "type": "integer"},
    },
    "type": "object",
}


def _object_schema(required: Sequence[str], properties: Mapping[str, Any]) -> dict:
    return {
        "additionalProperties": False,
        "properties": dict(properties),
        "required": list(required),
        "type": "object",
    }


FINITE_CODE_INPUT_SCHEMA = _object_schema(
    ("sites", "generators"),
    {
        "generators": {"items": GENERATOR_SCHEMA, "type": "array"},
        "max_dense_entries": {"minimum": 1, "type": "integer"},
        "sites": {"items": SITE_SCHEMA, "minItems": 1, "type": "array"},
    },
)
FINITE_BOUNDARY_INPUT_SCHEMA = _object_schema(
    ("sites", "generators", "window"),
    {
        "generators": {"items": GENERATOR_SCHEMA, "type": "array"},
        "max_dense_entries": {"minimum": 1, "type": "integer"},
        "sites": {"items": SITE_SCHEMA, "minItems": 1, "type": "array"},
        "window": WINDOW_SCHEMA,
    },
)
E1_INPUT_SCHEMA = _object_schema(
    ("sites", "generators", "window"),
    {
        "budget": BUDGET_SCHEMA,
        "generators": {"items": GENERATOR_SCHEMA, "type": "array"},
        "max_dense_entries": {"minimum": 1, "type": "integer"},
        "sites": {"items": SITE_SCHEMA, "minItems": 1, "type": "array"},
        "window": WINDOW_SCHEMA,
    },
)
E2_REFERENCE_INPUT_SCHEMA = _object_schema(
    (),
    {
        "budget": BUDGET_SCHEMA,
        "max_dense_entries": {"minimum": 1, "type": "integer"},
    },
)


def _strict_object(
    value: Any,
    *,
    name: str,
    allowed: Sequence[str],
    required: Sequence[str] = (),
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {name} fields: " + ", ".join(unknown))
    missing = [field for field in required if field not in value]
    if missing:
        raise ValueError(f"missing {name} fields: " + ", ".join(missing))
    return value


def _plain_int(value: Any, name: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _sequence(value: Any, name: str) -> Tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be an array")
    return tuple(value)


def _backend(data: Mapping[str, Any]):
    from mobility_toolkit.finite import FlintIntegerBackend

    maximum = _plain_int(
        data.get("max_dense_entries", 2_000_000),
        "max_dense_entries",
        minimum=1,
    )
    return FlintIntegerBackend(max_dense_entries=maximum)


def _decode_code(
    data: Mapping[str, Any], *, allowed_extras: Sequence[str] = ()
):
    allowed = ("sites", "generators", "max_dense_entries") + tuple(allowed_extras)
    data = _strict_object(
        data,
        name="input_data",
        allowed=allowed,
        required=("sites", "generators"),
    )
    site_payloads = _sequence(data["sites"], "sites")
    if not site_payloads:
        raise ValueError("sites must contain at least one local system")
    systems = []
    for index, payload in enumerate(site_payloads):
        item = _strict_object(
            payload,
            name=f"sites[{index}]",
            allowed=("site_id", "dimension"),
            required=("site_id", "dimension"),
        )
        site_id = item["site_id"]
        if not isinstance(site_id, str) or not site_id:
            raise ValueError(f"sites[{index}].site_id must be nonempty")
        dimension = _plain_int(
            item["dimension"], f"sites[{index}].dimension", minimum=2
        )
        systems.append(LocalSystem.cyclic(site_id, dimension))
    site_ids = tuple(system.site_id for system in systems)
    if site_ids != tuple(sorted(set(site_ids))):
        raise ValueError("sites must be sorted by unique site_id")
    module = PauliModule(tuple(systems))

    generator_payloads = _sequence(data["generators"], "generators")
    generators = []
    for generator_index, payload in enumerate(generator_payloads):
        item = _strict_object(
            payload,
            name=f"generators[{generator_index}]",
            allowed=("phase", "terms"),
            required=("phase", "terms"),
        )
        phase = _plain_int(item["phase"], f"generators[{generator_index}].phase")
        terms = []
        seen_sites = set()
        for term_index, raw_term in enumerate(
            _sequence(item["terms"], f"generators[{generator_index}].terms")
        ):
            term = _strict_object(
                raw_term,
                name=f"generators[{generator_index}].terms[{term_index}]",
                allowed=("site_id", "x", "z"),
                required=("site_id", "x", "z"),
            )
            site_id = term["site_id"]
            if not isinstance(site_id, str) or not site_id:
                raise ValueError("generator term site_id must be nonempty")
            if site_id in seen_sites:
                raise ValueError(
                    f"generator {generator_index} repeats local site {site_id!r}"
                )
            seen_sites.add(site_id)
            terms.append(
                LocalPauliTerm.cyclic(
                    site_id,
                    x=_plain_int(term["x"], "local X exponent"),
                    z=_plain_int(term["z"], "local Z exponent"),
                )
            )
        generators.append(module.operator(terms, phase=phase))
        term_site_ids = tuple(term.site_id for term in terms)
        if term_site_ids != tuple(sorted(term_site_ids)):
            raise ValueError(
                f"generator {generator_index} terms must be sorted by site_id"
            )
    return data, module, tuple(generators)


def _decode_budget(payload: Any):
    from mobility_toolkit.boundary import EnumerationBudget

    if payload is None:
        return EnumerationBudget()
    data = _strict_object(
        payload,
        name="budget",
        allowed=(
            "max_work_units",
            "max_results",
            "max_phase_assignments",
            "max_elements",
            "max_subgroups",
        ),
    )
    defaults = EnumerationBudget()
    values = {
        name: _plain_int(data.get(name, getattr(defaults, name)), name, minimum=1)
        for name in (
            "max_work_units",
            "max_results",
            "max_phase_assignments",
            "max_elements",
            "max_subgroups",
        )
    }
    return EnumerationBudget(**values)


def _decode_boundary(data: Mapping[str, Any], *, allow_budget: bool = False):
    from mobility_toolkit.boundary import (
        analyze_finite_boundary_algebra,
        support_window_from_sites,
    )
    from mobility_toolkit.finite import analyze_finite_stabilizer

    extras = ("window", "budget") if allow_budget else ("window",)
    data, module, generators = _decode_code(data, allowed_extras=extras)
    window_data = _strict_object(
        data["window"],
        name="window",
        allowed=("window_id", "site_ids", "search_extent"),
        required=("window_id", "site_ids"),
    )
    window_id = window_data["window_id"]
    if not isinstance(window_id, str) or not window_id:
        raise ValueError("window.window_id must be nonempty")
    site_ids = _sequence(window_data["site_ids"], "window.site_ids")
    if any(not isinstance(site_id, str) or not site_id for site_id in site_ids):
        raise ValueError("window.site_ids must contain nonempty strings")
    if site_ids != tuple(sorted(set(site_ids))):
        raise ValueError("window.site_ids must be sorted and unique")
    extent = []
    for index, payload in enumerate(window_data.get("search_extent", ())):
        item = _strict_object(
            payload,
            name=f"window.search_extent[{index}]",
            allowed=("name", "value"),
            required=("name", "value"),
        )
        label = item["name"]
        if not isinstance(label, str) or not label:
            raise ValueError("search-extent names must be nonempty")
        extent.append((label, _plain_int(item["value"], "search-extent value")))
    if tuple(name for name, _ in extent) != tuple(
        sorted({name for name, _ in extent})
    ):
        raise ValueError("window.search_extent must be sorted by unique name")

    backend = _backend(data)
    analysis = analyze_finite_stabilizer(module, generators, backend)
    window = support_window_from_sites(
        analysis,
        site_ids,
        backend,
        window_id=window_id,
        search_extent=tuple(extent),
    )
    algebra = analyze_finite_boundary_algebra(analysis, window, backend)
    return data, backend, analysis, window, algebra


def _provenance(backend, algorithm: str, parameters: Tuple[Tuple[str, Any], ...] = ()):
    return BackendProvenance(
        getattr(backend, "name", backend.__class__.__name__),
        algorithm,
        getattr(backend, "version", ""),
        parameters,
    )


def analyze_finite_code_service(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.finite import analyze_finite_stabilizer

    data, module, generators = _decode_code(request.input_data)
    backend = _backend(data)
    analysis = analyze_finite_stabilizer(module, generators, backend)
    dimensions = tuple(system.hilbert_dimension for system in module.local_systems)
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=analysis,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=(
            "Exact finite generalized-Pauli stabilizer analysis for the explicitly "
            "supplied phase-aware generators and cyclic local dimensions."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=analysis.validation,
        verification=(
            ("generator_relations_scalar_free", not any(
                analysis.validation.relation_scalar_phases
            )),
            ("mixed_local_dimensions", len(set(dimensions)) > 1),
            ("phase_modulus", module.phase_modulus),
            ("stabilizer_validation_valid", analysis.validation.valid),
        ),
        backend_provenance=_provenance(
            backend,
            "phase-aware-finite-stabilizer-analysis",
            (("local_dimensions", dimensions),),
        ),
        resource_usage=(
            ("generator_count", len(generators)),
            ("site_count", len(module.local_systems)),
        ),
        schema_version=request.schema_version,
    )


def analyze_finite_boundary_service(request: ServiceRequest) -> ComputationResult:
    _, backend, analysis, window, algebra = _decode_boundary(request.input_data)
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=algebra,
        exactness=Exactness.BOUNDED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=algebra.theorem_scope,
        certificate_level=CertificateLevel.STANDARD,
        certificate={
            "finite_stabilizer_validation": analysis.validation,
            "support_window": window,
        },
        verification=(
            ("bulk_trivial_contained_in_local_centralizer", True),
            ("bulk_trivial_contained_in_radical", True),
            ("finite_window_only", True),
            ("thermodynamic_completeness", False),
        ),
        backend_provenance=_provenance(
            backend,
            "finite-boundary-paired-quotient",
            (("window_id", window.window_id),),
        ),
        schema_version=request.schema_version,
    )


def enumerate_finite_e1_service(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.boundary import enumerate_e1_subgroups

    data, backend, _, window, algebra = _decode_boundary(
        request.input_data, allow_budget=True
    )
    page = enumerate_e1_subgroups(
        algebra, backend, budget=_decode_budget(data.get("budget"))
    )
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=page,
        exactness=page.certificate.exactness,
        assumptions=request.assumptions,
        theorem_scope=page.certificate.theorem_scope,
        certificate_level=CertificateLevel.FULL,
        certificate=page.certificate,
        verification=(
            ("certified_complete", page.certificate.certified_complete),
            ("finite_window_only", True),
            ("thermodynamic_completeness", False),
        ),
        backend_provenance=_provenance(
            backend,
            "finite-e1-isotropic-subgroup-enumeration",
            (("window_id", window.window_id),),
        ),
        resource_usage=(
            ("page_work_units", page.certificate.page_work_units),
            ("result_count", len(page.candidates)),
        ),
        diagnostics=(
            ()
            if page.certificate.certified_complete
            else ("Enumeration is resumable but this service operation exposes one page only.",)
        ),
        schema_version=request.schema_version,
    )


def e2_z2_swap_reference_service(request: ServiceRequest) -> ComputationResult:
    """Run the source-locked two-site Z2 tangent-swap E2 reference."""

    from mobility_toolkit.boundary import (
        E2SiteCoordinate,
        E2TangentAction,
        analyze_finite_boundary_algebra,
        bounded_periodic_search_extent,
        enumerate_e2_bounded_periodic,
        paired_boundary_presentation,
        support_window_from_sites,
    )
    from mobility_toolkit.boundary_halfspace import (
        AncillaBound,
        BoundedPeriodicSearchDomain,
        GeneratorSupportBound,
        OrientedHalfSpace,
        PrimitiveNormal,
    )
    from mobility_toolkit.core import SparseIntMatrix
    from mobility_toolkit.finite import (
        FiniteGroupHomomorphism,
        analyze_finite_stabilizer,
    )

    data = _strict_object(
        request.input_data,
        name="input_data",
        allowed=("budget", "max_dense_entries"),
    )
    backend = _backend(data)
    domain = BoundedPeriodicSearchDomain(
        half_space=OrientedHalfSpace(PrimitiveNormal((0, 1))),
        unit_cell_period=(1,),
        support_bound=GeneratorSupportBound(
            tangent_radii=(1,),
            max_inward_depth=0,
            max_sites_per_term=2,
        ),
        completion_depth=0,
        ancilla_bound=AncillaBound(max_sites_per_unit_cell=0),
        coefficient_domain="finite_fga:uniform_z2",
        candidate_families=("translation_compatible_submodules",),
    )
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    analysis = analyze_finite_stabilizer(module, (), backend)
    window = support_window_from_sites(
        analysis,
        ("a", "b"),
        backend,
        "source-locked-z2-tangent-swap",
        bounded_periodic_search_extent(domain),
    )
    algebra = analyze_finite_boundary_algebra(analysis, window, backend)
    paired = paired_boundary_presentation(algebra, backend)
    swap = SparseIntMatrix.from_rows(
        (
            (0, 0, 1, 0),
            (0, 0, 0, 1),
            (1, 0, 0, 0),
            (0, 1, 0, 0),
        )
    )
    action = E2TangentAction(
        "tangent-step",
        FiniteGroupHomomorphism.create(
            paired.group, paired.group, swap, backend
        ),
    )
    coordinates = (
        E2SiteCoordinate("a", (0,), 0),
        E2SiteCoordinate("b", (1,), 0),
    )
    page = enumerate_e2_bounded_periodic(
        algebra,
        domain,
        (action,),
        backend,
        coordinates,
        budget=_decode_budget(data.get("budget")),
    )
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=page,
        exactness=page.certificate.exactness,
        assumptions=request.assumptions,
        theorem_scope=page.certificate.theorem_scope,
        certificate_level=CertificateLevel.FULL,
        certificate=page.certificate,
        verification=(
            ("bounded_complete", page.certificate.bounded_complete),
            ("source_locked_reference", True),
            ("thermodynamic_completeness", False),
        ),
        backend_provenance=_provenance(
            backend,
            "source-locked-z2-tangent-swap-e2",
        ),
        resource_usage=(
            ("page_work_units", page.certificate.page_work_units),
            ("result_count", len(page.candidates)),
        ),
        warnings=(
            "This is a two-site finite paired-algebra shadow with a fixed swap "
            "translation, not an automatically extracted toric-code boundary.",
            "The generic E2 Python API remains available for explicitly constructed "
            "actions and search domains; this transport does not guess those data.",
        ),
        schema_version=request.schema_version,
    )


def _capability(
    operation: str,
    exactness: Exactness,
    certificate_level: CertificateLevel,
    reason: str,
    input_schema: Any,
    constraints: Tuple[Tuple[str, Any], ...] = (),
):
    def report(request: ServiceRequest) -> ServiceCapability:
        return ServiceCapability(
            operation,
            True,
            exactness,
            request.backend_fingerprint,
            reason,
            certificate_level,
            input_schema,
            constraints,
        )

    return report


def _registration(
    operation: str,
    summary: str,
    schema: Any,
    handler,
    exactness: Exactness,
    certificate_level: CertificateLevel,
    reason: str,
) -> ServiceRegistration:
    constraints = (("requires_python_flint", True),)
    return ServiceRegistration(
        operation,
        handler,
        _capability(
            operation,
            exactness,
            certificate_level,
            reason,
            schema,
            constraints,
        ),
        ServiceCatalogEntry(
            operation,
            summary,
            schema,
            adapter_kind="native",
            cacheable=True,
        ),
    )


def finite_boundary_service_registrations() -> Tuple[ServiceRegistration, ...]:
    return (
        _registration(
            "finite.code.analyze",
            "Exact phase-aware finite stabilizer analysis with mixed cyclic dimensions.",
            FINITE_CODE_INPUT_SCHEMA,
            analyze_finite_code_service,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Exact for the explicit finite phase-aware generalized-Pauli input.",
        ),
        _registration(
            "boundary.finite.analyze",
            "Exact paired boundary algebra on an explicit finite support window.",
            FINITE_BOUNDARY_INPUT_SCHEMA,
            analyze_finite_boundary_service,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.STANDARD,
            "Exact only for the supplied finite system and support window.",
        ),
        _registration(
            "boundary.finite.enumerate_e1",
            "Resumable E1 isotropic-subgroup enumeration of a finite boundary algebra.",
            E1_INPUT_SCHEMA,
            enumerate_finite_e1_service,
            Exactness.CERTIFIED_EXACT,
            CertificateLevel.FULL,
            "Complete only when the returned finite-group certificate says so.",
        ),
        _registration(
            "boundary.finite.e2.reference_z2_swap",
            "Source-locked two-site Z2 tangent-swap bounded-periodic E2 reference.",
            E2_REFERENCE_INPUT_SCHEMA,
            e2_z2_swap_reference_service,
            Exactness.BOUNDED_EXACT,
            CertificateLevel.FULL,
            "Bounded exact only for the fixed finite reference domain when exhausted.",
        ),
    )


__all__ = [
    "E1_INPUT_SCHEMA",
    "E2_REFERENCE_INPUT_SCHEMA",
    "FINITE_BOUNDARY_INPUT_SCHEMA",
    "FINITE_CODE_INPUT_SCHEMA",
    "analyze_finite_boundary_service",
    "analyze_finite_code_service",
    "e2_z2_swap_reference_service",
    "enumerate_finite_e1_service",
    "finite_boundary_service_registrations",
]
