"""Versioned, transport-neutral service contracts.

The service layer carries canonical mathematical objects.  JSON decoding is a
transport concern for the CLI, MCP server, and skills; algorithms never parse
transport dictionaries themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from mobility_toolkit.core import CertificateLevel, Exactness
from mobility_toolkit.core.canonical import canonical_hash


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


@dataclass(frozen=True)
class ServiceRequest:
    """One canonical operation request shared by every public transport."""

    operation: str
    input_data: Any
    requested_certificate_level: CertificateLevel = CertificateLevel.STANDARD
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


@dataclass(frozen=True)
class ServiceCapability:
    operation: str
    supported: bool
    maximum_exactness: Exactness
    backend_fingerprint: Optional[BackendFingerprint]
    reason: str

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
        if not self.supported and self.maximum_exactness is not Exactness.UNSUPPORTED:
            raise ValueError("unsupported capability must have unsupported exactness")

    def to_canonical_dict(self) -> dict:
        return {
            "backend_fingerprint": self.backend_fingerprint,
            "maximum_exactness": self.maximum_exactness,
            "operation": self.operation,
            "reason": self.reason,
            "schema": self.SCHEMA_ID,
            "supported": self.supported,
        }


__all__ = [
    "BackendFingerprint",
    "ServiceCapability",
    "ServiceRequest",
]
