"""Explicit in-memory cache protocol for canonical service results."""

from __future__ import annotations

from typing import Dict, Optional, Protocol

from mobility_toolkit.core import ComputationResult
from mobility_toolkit.services.contracts import ServiceRequest


class ServiceCache(Protocol):
    def get(self, request: ServiceRequest) -> Optional[ComputationResult]:
        ...

    def put(self, request: ServiceRequest, result: ComputationResult) -> None:
        ...


class InMemoryServiceCache:
    """A deterministic test/reference cache with no implicit persistence."""

    def __init__(self) -> None:
        self._values: Dict[str, ComputationResult] = {}

    def get(self, request: ServiceRequest) -> Optional[ComputationResult]:
        return self._values.get(request.cache_key)

    def put(self, request: ServiceRequest, result: ComputationResult) -> None:
        if result.operation != request.operation:
            raise ValueError("cannot cache a result for a different operation")
        if result.canonical_input_hash != request.canonical_input_hash:
            raise ValueError("cannot cache a result for different input data")
        if result.schema_version != request.schema_version:
            raise ValueError("cannot cache a result for a different schema version")
        if set(result.assumptions) != set(request.assumptions):
            raise ValueError("cannot cache a result with different assumptions")
        self._values[request.cache_key] = result

    def clear(self) -> None:
        self._values.clear()


__all__ = ["InMemoryServiceCache", "ServiceCache"]
