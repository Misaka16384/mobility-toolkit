"""Versioned, transport-neutral service contracts.

The service layer carries canonical mathematical objects.  JSON decoding is a
transport concern for the CLI, MCP server, and skills; algorithms never parse
transport dictionaries themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Optional, Tuple

from mobility_toolkit.core import CertificateLevel, ComputationResult, Exactness
from mobility_toolkit.core.canonical import canonical_hash, canonical_json


def _named_values(values, name: str) -> Tuple[Tuple[str, Any], ...]:
    result = tuple(sorted(tuple(item) for item in values))
    if any(len(item) != 2 or not isinstance(item[0], str) or not item[0] for item in result):
        raise ValueError(f"{name} must contain (nonempty string, value) pairs")
    if len({item[0] for item in result}) != len(result):
        raise ValueError(f"{name} names must be unique")
    return result


@dataclass(frozen=True)
class BackendFingerprint:
    """The backend identity that participates in a service cache key."""

    backend: str
    version: str
    algorithm_family: str
    capabilities: Tuple[Tuple[str, Any], ...] = ()

    SCHEMA_ID = "mobility_toolkit.service_backend_fingerprint.v1"

    def __post_init__(self) -> None:
        for value, name in (
            (self.backend, "backend"),
            (self.algorithm_family, "algorithm_family"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a nonempty string")
        if not isinstance(self.version, str):
            raise TypeError("version must be a string")
        object.__setattr__(
            self, "capabilities", _named_values(self.capabilities, "capabilities")
        )

    def to_canonical_dict(self) -> dict:
        return {
            "algorithm_family": self.algorithm_family,
            "backend": self.backend,
            "capabilities": self.capabilities,
            "schema": self.SCHEMA_ID,
            "version": self.version,
        }

    @classmethod
    def from_transport_dict(cls, payload: Mapping[str, Any]) -> "BackendFingerprint":
        if not isinstance(payload, Mapping):
            raise TypeError("backend_fingerprint must be an object")
        return cls(
            backend=payload["backend"],
            version=payload.get("version", ""),
            algorithm_family=payload["algorithm_family"],
            capabilities=tuple(
                (name, value)
                for name, value in payload.get("capabilities", {}).items()
            )
            if isinstance(payload.get("capabilities", ()), Mapping)
            else tuple(tuple(item) for item in payload.get("capabilities", ())),
        )


@dataclass(frozen=True)
class ServiceRequest:
    """One canonical operation request shared by every public transport."""

    operation: str
    input_data: Any
    requested_certificate_level: CertificateLevel = CertificateLevel.NONE
    assumptions: Tuple[str, ...] = ()
    backend_fingerprint: Optional[BackendFingerprint] = None
    equivalence_relation: str = "raw"
    search_domain: Any = None
    schema_version: str = "1"

    SCHEMA_ID = "mobility_toolkit.service_request.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("operation must be a nonempty string")
        if not isinstance(self.requested_certificate_level, CertificateLevel):
            raise TypeError("requested_certificate_level must be a CertificateLevel")
        assumptions = tuple(sorted(set(self.assumptions)))
        if any(not isinstance(value, str) or not value for value in assumptions):
            raise ValueError("assumptions must be nonempty strings")
        if not isinstance(self.equivalence_relation, str) or not self.equivalence_relation:
            raise ValueError("equivalence_relation must be a nonempty string")
        if not isinstance(self.schema_version, str) or not self.schema_version:
            raise ValueError("schema_version must be a nonempty string")
        object.__setattr__(self, "assumptions", assumptions)

    @property
    def canonical_input_hash(self) -> str:
        return canonical_hash(
            f"operation:{self.operation}:schema:{self.schema_version}",
            self.input_data,
        )

    @property
    def cache_key(self) -> str:
        return canonical_hash(self.SCHEMA_ID, self)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "backend_fingerprint": self.backend_fingerprint,
            "canonical_input_hash": self.canonical_input_hash,
            "equivalence_relation": self.equivalence_relation,
            "input_data": self.input_data,
            "operation": self.operation,
            "requested_certificate_level": self.requested_certificate_level,
            "schema": self.SCHEMA_ID,
            "schema_version": self.schema_version,
            "search_domain": self.search_domain,
        }

    @classmethod
    def from_transport_dict(cls, payload: Mapping[str, Any]) -> "ServiceRequest":
        """Decode the one public JSON request schema.

        Unknown keys are rejected deliberately.  In particular, removed
        compatibility switches such as ``prime_bypass`` cannot silently alter
        the coefficient domain selected by an operation adapter.
        """

        if not isinstance(payload, Mapping):
            raise TypeError("service request must be a JSON object")
        allowed = {
            "assumptions",
            "backend_fingerprint",
            "equivalence_relation",
            "input_data",
            "operation",
            "requested_certificate_level",
            "schema",
            "schema_version",
            "search_domain",
        }
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ValueError("unknown service request fields: " + ", ".join(unknown))
        schema = payload.get("schema", cls.SCHEMA_ID)
        if schema != cls.SCHEMA_ID:
            raise ValueError(
                f"unsupported service request schema {schema!r}; expected {cls.SCHEMA_ID!r}"
            )
        try:
            level = CertificateLevel(
                payload.get("requested_certificate_level", CertificateLevel.NONE.value)
            )
        except ValueError as exc:
            raise ValueError("invalid requested_certificate_level") from exc
        fingerprint_payload = payload.get("backend_fingerprint")
        fingerprint = (
            None
            if fingerprint_payload is None
            else BackendFingerprint.from_transport_dict(fingerprint_payload)
        )
        return cls(
            operation=payload["operation"],
            input_data=payload.get("input_data", {}),
            requested_certificate_level=level,
            assumptions=tuple(payload.get("assumptions", ())),
            backend_fingerprint=fingerprint,
            equivalence_relation=payload.get("equivalence_relation", "raw"),
            search_domain=payload.get("search_domain"),
            schema_version=payload.get("schema_version", "1"),
        )

    def to_transport_dict(self) -> dict:
        return json.loads(canonical_json(self))


@dataclass(frozen=True)
class ServiceCapability:
    operation: str
    supported: bool
    maximum_exactness: Exactness
    backend_fingerprint: Optional[BackendFingerprint]
    reason: str
    maximum_certificate_level: CertificateLevel = CertificateLevel.NONE
    input_schema: Any = None
    constraints: Tuple[Tuple[str, Any], ...] = ()

    SCHEMA_ID = "mobility_toolkit.service_capability.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("operation must be a nonempty string")
        if not isinstance(self.supported, bool):
            raise TypeError("supported must be boolean")
        if not isinstance(self.maximum_exactness, Exactness):
            raise TypeError("maximum_exactness must be an Exactness")
        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a nonempty string")
        if not isinstance(self.maximum_certificate_level, CertificateLevel):
            raise TypeError("maximum_certificate_level must be a CertificateLevel")
        if not self.supported and self.maximum_exactness is not Exactness.UNSUPPORTED:
            raise ValueError("unsupported capability must have unsupported exactness")
        object.__setattr__(
            self, "constraints", _named_values(self.constraints, "constraints")
        )

    def to_canonical_dict(self) -> dict:
        return {
            "backend_fingerprint": self.backend_fingerprint,
            "maximum_exactness": self.maximum_exactness,
            "maximum_certificate_level": self.maximum_certificate_level,
            "operation": self.operation,
            "reason": self.reason,
            "schema": self.SCHEMA_ID,
            "supported": self.supported,
            "input_schema": self.input_schema,
            "constraints": self.constraints,
        }


@dataclass(frozen=True)
class ServiceCatalogEntry:
    """Transport-neutral description of one registered operation."""

    operation: str
    summary: str
    input_schema: Any
    output_schema: str = ComputationResult.SCHEMA_ID
    adapter_kind: str = "native"
    cacheable: bool = True

    SCHEMA_ID = "mobility_toolkit.service_catalog_entry.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or not self.operation:
            raise ValueError("operation must be a nonempty string")
        if not isinstance(self.summary, str) or not self.summary:
            raise ValueError("summary must be a nonempty string")
        if not isinstance(self.output_schema, str) or not self.output_schema:
            raise ValueError("output_schema must be a nonempty string")
        if self.adapter_kind != "native":
            raise ValueError("adapter_kind must be native")
        if not isinstance(self.cacheable, bool):
            raise TypeError("cacheable must be boolean")

    def to_canonical_dict(self) -> dict:
        return {
            "adapter_kind": self.adapter_kind,
            "cacheable": self.cacheable,
            "input_schema": self.input_schema,
            "operation": self.operation,
            "output_schema": self.output_schema,
            "schema": self.SCHEMA_ID,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class ServiceExecution:
    """The common Python/CLI/MCP response envelope."""

    request: ServiceRequest
    capability: ServiceCapability
    result: ComputationResult
    cache_hit: bool = False

    SCHEMA_ID = "mobility_toolkit.service_execution.v1"

    def __post_init__(self) -> None:
        if self.request.operation != self.capability.operation:
            raise ValueError("capability operation differs from request")
        if self.request.operation != self.result.operation:
            raise ValueError("result operation differs from request")
        if not isinstance(self.cache_hit, bool):
            raise TypeError("cache_hit must be boolean")

    def to_canonical_dict(self) -> dict:
        return {
            "cache": {
                "hit": self.cache_hit,
                "key": self.request.cache_key,
            },
            "capability": self.capability,
            "request": self.request,
            "result": self.result,
            "schema": self.SCHEMA_ID,
        }

    def to_transport_dict(self) -> dict:
        return json.loads(canonical_json(self))


__all__ = [
    "BackendFingerprint",
    "ServiceCatalogEntry",
    "ServiceCapability",
    "ServiceExecution",
    "ServiceRequest",
]
