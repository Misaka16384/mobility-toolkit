"""Structured request/response adapter for the Laurent Macaulay2 backend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from mobility_toolkit.core.canonical import canonical_json
from mobility_toolkit.core.laurent import LaurentPolynomial
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.engine import describe_m2_backend, run_macaulay2
from mobility_toolkit.periodic.capabilities import (
    CapabilityDecision,
    PeriodicOperation,
    PeriodicSupportMatrix,
    SupportTier,
)
from mobility_toolkit.periodic.laurent import parse_legacy_laurent
from mobility_toolkit.periodic.presentations import QuasiFreePauliModulePresentation


@dataclass(frozen=True)
class PeriodicBackendRequest:
    """Canonical request; there is intentionally no ``prime_bypass`` field."""

    operation: PeriodicOperation
    presentation: QuasiFreePauliModulePresentation
    charge_degree: int = 0
    validate_stabilizer: bool = True

    SCHEMA_ID = "mobility_toolkit.periodic_backend_request.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, PeriodicOperation):
            raise TypeError("operation must be a PeriodicOperation")
        if not isinstance(self.presentation, QuasiFreePauliModulePresentation):
            raise TypeError("presentation must be QuasiFreePauliModulePresentation")
        if isinstance(self.charge_degree, bool) or not isinstance(self.charge_degree, int):
            raise TypeError("charge_degree must be an integer")
        if self.charge_degree < 0:
            raise ValueError("charge_degree must be nonnegative")
        if not isinstance(self.validate_stabilizer, bool):
            raise TypeError("validate_stabilizer must be a boolean")

    def to_canonical_dict(self) -> dict:
        return {
            "charge_degree": self.charge_degree,
            "operation": self.operation,
            "presentation": self.presentation,
            "schema": self.SCHEMA_ID,
            "validate_stabilizer": self.validate_stabilizer,
        }


@dataclass(frozen=True)
class ChargeModuleInvariants:
    """Canonical part of the legacy uniform-prime M2 response."""

    charge_degree: int
    ext_degree: int
    krull_dimension: int
    annihilator_generators: Tuple[LaurentPolynomial, ...]
    zero_module: bool

    SCHEMA_ID = "mobility_toolkit.charge_module_invariants.v1"

    def __post_init__(self) -> None:
        generators = tuple(self.annihilator_generators)
        if any(not isinstance(item, LaurentPolynomial) for item in generators):
            raise TypeError("annihilator_generators must be LaurentPolynomial objects")
        canonical = {canonical_json(generator): generator for generator in generators}
        object.__setattr__(
            self,
            "annihilator_generators",
            tuple(canonical[key] for key in sorted(canonical)),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "annihilator_generators": self.annihilator_generators,
            "charge_degree": self.charge_degree,
            "ext_degree": self.ext_degree,
            "krull_dimension": self.krull_dimension,
            "schema": self.SCHEMA_ID,
            "zero_module": self.zero_module,
        }


@dataclass(frozen=True)
class PeriodicBackendResponse:
    capability: CapabilityDecision
    computation: ComputationResult

    SCHEMA_ID = "mobility_toolkit.periodic_backend_response.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "capability": self.capability,
            "computation": self.computation,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class Macaulay2Probe:
    available: bool
    strategy: str
    command: Tuple[str, ...]
    version: str
    version_checked: bool
    operations: Tuple[Tuple[str, str], ...]
    diagnostics: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.macaulay2_periodic_probe.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "available": self.available,
            "command": self.command,
            "diagnostics": self.diagnostics,
            "operations": self.operations,
            "schema": self.SCHEMA_ID,
            "strategy": self.strategy,
            "version": self.version,
            "version_checked": self.version_checked,
        }


def probe_macaulay2(execute_version: bool = False) -> Macaulay2Probe:
    """Report invocation, version, and semantic operation capabilities."""

    if not isinstance(execute_version, bool):
        raise TypeError("execute_version must be a boolean")
    description = describe_m2_backend()
    command = tuple(description.get("command") or ())
    available = bool(description.get("available"))
    diagnostics = []
    version = "unprobed"
    checked = False
    if execute_version and available:
        checked = True
        result = run_macaulay2('print "VALUE:VERSION_START"\nprint version\n')
        if result["exit_code"] == 0:
            payload = result["stdout"].split("VALUE:VERSION_START", 1)[-1]
            lines = [line.strip() for line in payload.splitlines() if line.strip()]
            if lines:
                version = re.sub(r"^[io]\d+\s*[:=]\s*", "", lines[0])
            else:
                diagnostics.append("Macaulay2 returned no version payload")
                version = "unknown"
        else:
            diagnostics.append(result["stderr"] or result["stdout"] or "version probe failed")
            version = "unknown"
    elif not available:
        version = "unavailable"
    operations = (
        ("uniform_prime.ext", "production"),
        ("uniform_prime.annihilator", "production"),
        ("uniform_prime.krull_dimension", "production"),
        ("uniform_prime.saturation", "experimental"),
        ("uniform_composite.ext", "experimental"),
        ("nonuniform.ext", "unsupported"),
        ("fixed_z4_paper_resolution.homology", "experimental"),
        ("fixed_nonuniform_quasi_free_toy.homology", "experimental"),
    )
    return Macaulay2Probe(
        available=available,
        strategy=str(description.get("strategy", "")),
        command=command,
        version=version,
        version_checked=checked,
        operations=operations,
        diagnostics=tuple(diagnostics),
    )


class StructuredMacaulay2Backend:
    """Adapt canonical requests to the validated uniform-prime implementation."""

    def __init__(
        self,
        legacy_compute: Optional[Callable[..., dict]] = None,
        support_matrix: Optional[PeriodicSupportMatrix] = None,
    ) -> None:
        self._legacy_compute = legacy_compute
        self._support_matrix = support_matrix or PeriodicSupportMatrix()

    def supports(self, request: PeriodicBackendRequest) -> CapabilityDecision:
        if not isinstance(request, PeriodicBackendRequest):
            raise TypeError("request must be a PeriodicBackendRequest")
        return self._support_matrix.decide(request.operation, request.presentation)

    def _unsupported_response(
        self,
        request: PeriodicBackendRequest,
        capability: CapabilityDecision,
    ) -> PeriodicBackendResponse:
        computation = ComputationResult(
            operation=f"periodic.{request.operation.value}",
            input_data=request,
            value=None,
            exactness=capability.exactness,
            theorem_scope="No periodic invariant was computed.",
            diagnostics=(capability.reason,),
            warnings=(
                "Experimental capability is not executed by the production adapter."
                if capability.tier is SupportTier.EXPERIMENTAL
                else "The requested coefficient/operation combination is unsupported.",
            ),
        )
        return PeriodicBackendResponse(capability, computation)

    def execute(self, request: PeriodicBackendRequest) -> PeriodicBackendResponse:
        capability = self.supports(request)
        if capability.tier is not SupportTier.PRODUCTION:
            return self._unsupported_response(request, capability)
        if request.operation is PeriodicOperation.PRESENTATION:
            computation = ComputationResult(
                operation="periodic.presentation",
                input_data=request,
                value=request.presentation,
                exactness=Exactness.CERTIFIED_EXACT,
                theorem_scope="Canonical quasi-free periodic Pauli-module presentation.",
                certificate_level=CertificateLevel.FULL,
                certificate={
                    "basis_relations_complete": True,
                    "stabilizer_entries_are_canonical_ast": True,
                },
                verification=(
                    (
                        "local_order_relation_count",
                        len(request.presentation.local_order_relations),
                    ),
                ),
                backend_provenance=BackendProvenance(
                    backend="internal",
                    algorithm="canonical-periodic-presentation",
                    version="1",
                ),
            )
            return PeriodicBackendResponse(capability, computation)
        if request.operation not in {
            PeriodicOperation.EXT,
            PeriodicOperation.ANNIHILATOR,
            PeriodicOperation.KRULL_DIMENSION,
        }:
            return self._unsupported_response(
                request,
                CapabilityDecision(
                    request.operation,
                    capability.coefficient_domain,
                    SupportTier.UNSUPPORTED,
                    Exactness.UNSUPPORTED,
                    capability.backend,
                    "this structured adapter does not execute the requested operation",
                ),
            )
        presentation = request.presentation
        rows = [list(row) for row in presentation.to_legacy_generator_rows()]
        if self._legacy_compute is None:
            from mobility_toolkit.homology import compute_ext_krull

            legacy_compute = compute_ext_krull
        else:
            legacy_compute = self._legacy_compute
        # No prime_bypass argument exists in this adapter.  A production
        # capability decision has already proved the coefficient is prime.
        legacy = legacy_compute(
            rows,
            presentation.distinct_local_orders[0],
            p_ext=request.charge_degree,
            spatial_dim=presentation.translation_group.free_rank,
            validate_stabilizer=request.validate_stabilizer,
        )
        annihilator = tuple(
            parse_legacy_laurent(
                expression,
                presentation.coefficient_modulus,
                presentation.translation_group,
            )
            for expression in legacy.get("annihilator_generators", ())
        )
        krull_dimension = int(legacy["krull_dimension"])
        value = ChargeModuleInvariants(
            charge_degree=request.charge_degree,
            ext_degree=request.charge_degree + 1,
            krull_dimension=krull_dimension,
            annihilator_generators=annihilator,
            zero_module=krull_dimension < 0,
        )
        provenance = BackendProvenance(
            backend="Macaulay2",
            algorithm="ruba-yang-uniform-prime-legacy-adapter",
            version=str(legacy.get("backend_version", "unreported")),
            parameters=(
                ("coefficient_modulus", presentation.coefficient_modulus),
                ("charge_degree", request.charge_degree),
                ("spatial_dim", presentation.translation_group.free_rank),
            ),
        )
        computation = ComputationResult(
            operation=f"periodic.{request.operation.value}",
            input_data=request,
            value=value,
            exactness=Exactness.CERTIFIED_EXACT,
            assumptions=("uniform prime local order", "free translation lattice"),
            theorem_scope="Ruba--Yang Q^p = Ext_R^(p+1)(bar(P/L), R)",
            certificate_level=CertificateLevel.STANDARD,
            certificate={
                "annihilator_ast_parsed": True,
                "legacy_matrix_rendered_from_canonical_ast": True,
            },
            verification=(
                ("legacy_stabilizer_validation_requested", request.validate_stabilizer),
                ("operation_capability", capability.tier.value),
            ),
            backend_provenance=provenance,
            diagnostics=(
                "Macaulay2 pretty-printed Ext text is excluded from canonical response identity.",
            ),
        )
        return PeriodicBackendResponse(capability, computation)


__all__ = [
    "ChargeModuleInvariants",
    "Macaulay2Probe",
    "PeriodicBackendRequest",
    "PeriodicBackendResponse",
    "StructuredMacaulay2Backend",
    "probe_macaulay2",
]
