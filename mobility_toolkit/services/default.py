"""Default canonical operation registry and shared Python/CLI/MCP executor.

This module is deliberately only an assembler.  Domain JSON decoding and
algorithm dispatch live beside their native operations; no legacy
polynomial-string, flat-vector, dimension-specific tuple, or compatibility
adapter is registered here.
"""

from __future__ import annotations

import json
from typing import Mapping, Optional

from mobility_toolkit.core import canonical_json
from mobility_toolkit.services.cache import InMemoryServiceCache, ServiceCache
from mobility_toolkit.services.contracts import (
    ServiceExecution,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistry


SERVICE_API_VERSION = "1"
SERVICE_CATALOG_SCHEMA_ID = "mobility_toolkit.service_catalog.v1"


def build_default_registry() -> ServiceRegistry:
    """Build a fresh deterministic registry of canonical operations."""

    from mobility_toolkit.services.boundary_usecases import (
        boundary_usecase_service_registrations,
    )
    from mobility_toolkit.services.capability_operations import (
        capability_service_registrations,
    )
    from mobility_toolkit.services.finite_boundary_operations import (
        finite_boundary_service_registrations,
    )
    from mobility_toolkit.services.periodic_operations import (
        periodic_service_registrations,
    )
    from mobility_toolkit.services.relative_operations import (
        relative_service_registrations,
    )

    registrations = (
        capability_service_registrations()
        + finite_boundary_service_registrations()
        + relative_service_registrations()
        + boundary_usecase_service_registrations()
        + periodic_service_registrations()
    )
    return ServiceRegistry(registrations)


class ServiceExecutor:
    """Caller-owned executor with validated canonical-result caching."""

    def __init__(
        self,
        registry: Optional[ServiceRegistry] = None,
        cache: Optional[ServiceCache] = None,
    ) -> None:
        self.registry = (
            registry if registry is not None else build_default_registry()
        )
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
                return ServiceExecution(
                    request, capability, cached, cache_hit=True
                )
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
        if not isinstance(request.input_data, Mapping):
            raise TypeError("operation input_data must be a JSON object")
        data = request.input_data
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(data) - set(properties))
            if unknown:
                raise ValueError(
                    f"unknown input_data fields for {request.operation}: "
                    + ", ".join(unknown)
                )
        missing = [
            name for name in schema.get("required", ()) if name not in data
        ]
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
            entries.append({"capability": capability, "operation": entry})
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
    """Execute one canonical request through the process-local executor."""

    return _DEFAULT_EXECUTOR.execute(request)


def execute_service_payload(payload: Mapping[str, object]) -> dict:
    """Shared JSON adapter used verbatim by CLI, MCP, and every skill."""

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
