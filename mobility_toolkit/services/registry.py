"""Explicit service registration and dispatch without hidden global state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from mobility_toolkit.core import CertificateLevel, ComputationResult
from mobility_toolkit.services.contracts import ServiceCapability, ServiceRequest


ServiceHandler = Callable[[ServiceRequest], ComputationResult]
CapabilityHandler = Callable[[ServiceRequest], ServiceCapability]


_CERTIFICATE_RANK = {
    CertificateLevel.NONE: 0,
    CertificateLevel.STANDARD: 1,
    CertificateLevel.FULL: 2,
}


@dataclass(frozen=True)
class ServiceRegistration:
    operation: str
    handler: ServiceHandler
    capability: Optional[CapabilityHandler] = None

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("operation must be a nonempty string")
        if not callable(self.handler):
            raise TypeError("handler must be callable")
        if self.capability is not None and not callable(self.capability):
            raise TypeError("capability must be callable")


class ServiceRegistry:
    """A caller-owned registry; construction and dispatch have no I/O effects."""

    def __init__(self, registrations: Tuple[ServiceRegistration, ...] = ()) -> None:
        self._registrations: Dict[str, ServiceRegistration] = {}
        for registration in registrations:
            self.register(registration)

    @property
    def operations(self) -> Tuple[str, ...]:
        return tuple(sorted(self._registrations))

    def register(self, registration: ServiceRegistration) -> None:
        if not isinstance(registration, ServiceRegistration):
            raise TypeError("registration must be ServiceRegistration")
        if registration.operation in self._registrations:
            raise ValueError(f"operation is already registered: {registration.operation}")
        self._registrations[registration.operation] = registration

    def capability(self, request: ServiceRequest) -> Optional[ServiceCapability]:
        registration = self._registration(request)
        if registration.capability is None:
            return None
        result = registration.capability(request)
        if not isinstance(result, ServiceCapability):
            raise TypeError("capability handler must return ServiceCapability")
        if result.operation != request.operation:
            raise ArithmeticError("capability operation differs from request")
        return result

    def dispatch(self, request: ServiceRequest) -> ComputationResult:
        registration = self._registration(request)
        capability = self.capability(request)
        if capability is not None and not capability.supported:
            raise ValueError(
                f"operation {request.operation!r} is unsupported: {capability.reason}"
            )
        result = registration.handler(request)
        if not isinstance(result, ComputationResult):
            raise TypeError("service handler must return ComputationResult")
        if result.operation != request.operation:
            raise ArithmeticError("result operation differs from request")
        if result.canonical_input_hash != request.canonical_input_hash:
            raise ArithmeticError("result input differs from the canonical request input")
        if set(result.assumptions) != set(request.assumptions):
            raise ArithmeticError("result assumptions differ from the request")
        if (
            _CERTIFICATE_RANK[result.certificate_level]
            < _CERTIFICATE_RANK[request.requested_certificate_level]
        ):
            raise ArithmeticError("result does not satisfy the requested certificate level")
        return result

    def _registration(self, request: ServiceRequest) -> ServiceRegistration:
        if not isinstance(request, ServiceRequest):
            raise TypeError("request must be ServiceRequest")
        try:
            return self._registrations[request.operation]
        except KeyError as exc:
            raise KeyError(f"unknown service operation: {request.operation}") from exc


__all__ = [
    "CapabilityHandler",
    "ServiceHandler",
    "ServiceRegistration",
    "ServiceRegistry",
]
