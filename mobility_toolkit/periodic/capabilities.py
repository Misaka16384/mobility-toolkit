"""Operation-specific capability decisions for periodic Laurent backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mobility_toolkit.core.results import Exactness
from mobility_toolkit.periodic.presentations import QuasiFreePauliModulePresentation
from mobility_toolkit.utils import is_prime


class PeriodicOperation(str, Enum):
    PRESENTATION = "presentation"
    COMMUTATION = "commutation"
    EXT = "ext"
    ANNIHILATOR = "annihilator"
    KRULL_DIMENSION = "krull_dimension"
    SATURATION = "saturation"
    SYZYGY = "syzygy"
    PAPER_RESOLUTION_BENCHMARK = "paper_resolution_benchmark"
    NONUNIFORM_QUASI_FREE_BENCHMARK = "nonuniform_quasi_free_benchmark"


class CoefficientDomain(str, Enum):
    UNIFORM_PRIME = "uniform_prime"
    UNIFORM_COMPOSITE = "uniform_composite"
    NONUNIFORM = "nonuniform"


class SupportTier(str, Enum):
    PRODUCTION = "production"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class CapabilityDecision:
    operation: PeriodicOperation
    coefficient_domain: CoefficientDomain
    tier: SupportTier
    exactness: Exactness
    backend: str
    reason: str

    SCHEMA_ID = "mobility_toolkit.periodic_capability_decision.v1"

    @property
    def production_supported(self) -> bool:
        return self.tier is SupportTier.PRODUCTION

    def to_canonical_dict(self) -> dict:
        return {
            "backend": self.backend,
            "coefficient_domain": self.coefficient_domain,
            "exactness": self.exactness,
            "operation": self.operation,
            "reason": self.reason,
            "schema": self.SCHEMA_ID,
            "tier": self.tier,
        }


def coefficient_domain(
    presentation: QuasiFreePauliModulePresentation,
) -> CoefficientDomain:
    orders = presentation.distinct_local_orders
    if len(orders) != 1:
        return CoefficientDomain.NONUNIFORM
    return (
        CoefficientDomain.UNIFORM_PRIME
        if is_prime(orders[0])
        else CoefficientDomain.UNIFORM_COMPOSITE
    )


class PeriodicSupportMatrix:
    """The Phase-5B promotion gate encoded as executable policy."""

    SCHEMA_ID = "mobility_toolkit.periodic_support_matrix.v1"

    def decide(
        self,
        operation: PeriodicOperation,
        presentation: QuasiFreePauliModulePresentation,
    ) -> CapabilityDecision:
        if not isinstance(operation, PeriodicOperation):
            raise TypeError("operation must be a PeriodicOperation")
        if not isinstance(presentation, QuasiFreePauliModulePresentation):
            raise TypeError("presentation must be QuasiFreePauliModulePresentation")
        domain = coefficient_domain(presentation)
        if operation is PeriodicOperation.PAPER_RESOLUTION_BENCHMARK:
            if domain is CoefficientDomain.UNIFORM_COMPOSITE:
                return CapabilityDecision(
                    operation,
                    domain,
                    SupportTier.EXPERIMENTAL,
                    Exactness.EXPERIMENTAL,
                    "macaulay2-explicit-paper-resolution",
                    "only a fixed machine-verified paper resolution is executable",
                )
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "none",
                "the fixed paper benchmark is defined for its Z4 presentation only",
            )
        if operation is PeriodicOperation.NONUNIFORM_QUASI_FREE_BENCHMARK:
            if domain is CoefficientDomain.NONUNIFORM:
                return CapabilityDecision(
                    operation,
                    domain,
                    SupportTier.EXPERIMENTAL,
                    Exactness.EXPERIMENTAL,
                    "macaulay2-fixed-quasi-free-resolution",
                    "fixed Lemma 20 toy only; no generic nonuniform Ext construction",
                )
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "none",
                "the fixed nonuniform toy requires mixed local orders",
            )
        if operation is PeriodicOperation.PRESENTATION:
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.PRODUCTION,
                Exactness.CERTIFIED_EXACT,
                "internal-canonical-ir",
                "canonical quasi-free presentation and local-order relations are exact",
            )
        if operation is PeriodicOperation.COMMUTATION:
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.EXPERIMENTAL,
                Exactness.EXPERIMENTAL,
                "internal-laurent",
                "mixed-order Laurent pairing validation has not passed the production gate",
            )
        if presentation.translation_group.torsion_invariants:
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "macaulay2-legacy-adapter",
                "the current Macaulay2 Laurent adapter supports free translations only",
            )
        if presentation.translation_group.free_rank < 1:
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "macaulay2-legacy-adapter",
                "the current homology adapter requires a positive spatial dimension",
            )
        if (
            operation
            in {
                PeriodicOperation.EXT,
                PeriodicOperation.ANNIHILATOR,
                PeriodicOperation.KRULL_DIMENSION,
                PeriodicOperation.SATURATION,
                PeriodicOperation.SYZYGY,
            }
            and not presentation.stabilizer_image.columns
        ):
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "macaulay2-legacy-adapter",
                "the current structured adapter requires a nonempty stabilizer image",
            )
        if operation in {
            PeriodicOperation.EXT,
            PeriodicOperation.ANNIHILATOR,
            PeriodicOperation.KRULL_DIMENSION,
        }:
            if domain is CoefficientDomain.UNIFORM_PRIME:
                return CapabilityDecision(
                    operation,
                    domain,
                    SupportTier.PRODUCTION,
                    Exactness.CERTIFIED_EXACT,
                    "macaulay2-uniform-prime",
                    "validated Ruba--Yang uniform-prime charge-module path",
                )
            if domain is CoefficientDomain.UNIFORM_COMPOSITE:
                return CapabilityDecision(
                    operation,
                    domain,
                    SupportTier.EXPERIMENTAL,
                    Exactness.EXPERIMENTAL,
                    "macaulay2-composite-research",
                    "composite resolutions and Ext require literature and cross-backend validation",
                )
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "none",
                "nonuniform quasi-free Ext has no validated execution backend",
            )
        if operation in {PeriodicOperation.SATURATION, PeriodicOperation.SYZYGY}:
            if domain is CoefficientDomain.UNIFORM_PRIME:
                return CapabilityDecision(
                    operation,
                    domain,
                    SupportTier.EXPERIMENTAL,
                    Exactness.EXPERIMENTAL,
                    "macaulay2-research",
                    "structured operation exists but has not passed its production benchmark gate",
                )
            return CapabilityDecision(
                operation,
                domain,
                SupportTier.UNSUPPORTED,
                Exactness.UNSUPPORTED,
                "none",
                "no validated composite or nonuniform backend for this operation",
            )
        raise AssertionError(f"unhandled operation: {operation}")

    def to_canonical_dict(self) -> dict:
        return {
            "policy": "operation-and-coefficient-specific",
            "schema": self.SCHEMA_ID,
        }


__all__ = [
    "CapabilityDecision",
    "CoefficientDomain",
    "PeriodicOperation",
    "PeriodicSupportMatrix",
    "SupportTier",
    "coefficient_domain",
]
