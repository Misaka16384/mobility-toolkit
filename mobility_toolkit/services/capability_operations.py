"""Native software-capability declarations for canonical finite operations."""

from __future__ import annotations

from typing import Any, Tuple

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.services.contracts import (
    ServiceCapability,
    ServiceCatalogEntry,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistration


SERVICE_HANDLER_VERSION = "1"
EMPTY_OBJECT_SCHEMA = {
    "additionalProperties": False,
    "properties": {},
    "required": [],
    "type": "object",
}


def _result(
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
            "internal-contract", algorithm, SERVICE_HANDLER_VERSION
        ),
        schema_version=request.schema_version,
    )


def finite_code_capabilities(request: ServiceRequest) -> ComputationResult:
    return _result(
        request,
        {
            "finite_abelian_groups": "certified_exact_with_python_flint",
            "composite_modulus": True,
            "mixed_local_dimensions": True,
            "finite_stabilizer_analysis": "certified_exact",
            "phase_aware_pauli_arithmetic": True,
            "dense_materialization_guard": True,
            "optional_backend": "python-flint",
            "registered_operations": ("finite.code.analyze",),
            "transport_semantics": (
                "site-labelled sparse x/z terms with explicit central phase"
            ),
        },
        "finite-code-capabilities",
        (
            "Software capability declaration for exact finite Abelian and "
            "phase-aware stabilizer operations."
        ),
    )


def finite_boundary_capabilities(request: ServiceRequest) -> ComputationResult:
    return _result(
        request,
        {
            "finite_boundary_algebra": (
                "bounded_exact_for_supplied_finite_code_and_support_window"
            ),
            "primary_projection_compiler": "certified_exact_finite",
            "e1_subgroups": (
                "certified_exact_when_the_returned_finite_domain_is_exhausted"
            ),
            "e2_bounded_periodic": (
                "bounded_exact_for_declared_support_period_and_ancilla_domain"
            ),
            "registered_operations": (
                "boundary.finite.analyze",
                "boundary.finite.enumerate_e1",
                "boundary.finite.e2.reference_z2_swap",
            ),
            "generic_e2_transport_decoder": False,
            "e2_transport_reference": (
                "source_locked_two_site_z2_tangent_swap"
            ),
            "automatic_anyon_extraction": "unsupported",
            "thermodynamic_completeness": "unsupported",
        },
        "finite-boundary-capabilities",
        (
            "Software capability declaration; finite-window and "
            "thermodynamic scopes remain distinct."
        ),
    )


def boundary_enumeration_capabilities(
    request: ServiceRequest,
) -> ComputationResult:
    return _result(
        request,
        {
            "e1_finite_subgroups": {
                "operation": "boundary.finite.enumerate_e1",
                "exactness": (
                    "certified_exact_only_when_the_recorded_domain_is_exhausted"
                ),
            },
            "e2_bounded_periodic": {
                "operation": "boundary.finite.e2.reference_z2_swap",
                "exactness": "bounded_exact_for_the_source_locked_domain",
                "generic_transport": "unsupported",
            },
            "e3_symbolic3d": {
                "operation": "boundary.symbolic3d.enumerate",
                "exactness": (
                    "bounded_exact_only_when_the_recorded_seed_domain_is_exhausted"
                ),
                "checkpoint_resume": True,
                "equivalence": (
                    "constant_generator_change_and_common_monomial_translation"
                ),
            },
            "unsupported": (
                "thermodynamic completeness",
                "generic saturation",
                "automatic anomaly cancellation",
                "automatic local completion",
            ),
        },
        "boundary-enumeration-capabilities",
        (
            "Software capability declaration for E1/E2/E3 search domains; "
            "this operation performs no enumeration."
        ),
    )


def _capability(
    operation: str,
) -> Any:
    def report(request: ServiceRequest) -> ServiceCapability:
        return ServiceCapability(
            operation=operation,
            supported=True,
            maximum_exactness=Exactness.CERTIFIED_EXACT,
            backend_fingerprint=request.backend_fingerprint,
            reason="Exact machine-readable software capability declaration.",
            maximum_certificate_level=CertificateLevel.STANDARD,
            input_schema=EMPTY_OBJECT_SCHEMA,
        )

    return report


def _registration(
    operation: str,
    summary: str,
    handler: Any,
) -> ServiceRegistration:
    return ServiceRegistration(
        operation=operation,
        handler=handler,
        capability=_capability(operation),
        catalog=ServiceCatalogEntry(
            operation=operation,
            summary=summary,
            input_schema=EMPTY_OBJECT_SCHEMA,
            adapter_kind="native",
            cacheable=True,
        ),
    )


def capability_service_registrations() -> Tuple[ServiceRegistration, ...]:
    return (
        _registration(
            "finite.code.capabilities",
            "Machine-readable exact finite-code capability contract.",
            finite_code_capabilities,
        ),
        _registration(
            "boundary.finite.capabilities",
            "Machine-readable finite boundary-algebra capability contract.",
            finite_boundary_capabilities,
        ),
        _registration(
            "boundary.enumeration.capabilities",
            "Machine-readable E1/E2/E3 enumeration capability contract.",
            boundary_enumeration_capabilities,
        ),
    )


__all__ = [
    "boundary_enumeration_capabilities",
    "capability_service_registrations",
    "finite_boundary_capabilities",
    "finite_code_capabilities",
]
