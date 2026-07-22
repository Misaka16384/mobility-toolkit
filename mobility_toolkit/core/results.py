"""Uniform exactness and provenance metadata for core computations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Tuple

from mobility_toolkit.core.canonical import canonical_hash


class Exactness(str, Enum):
    CERTIFIED_EXACT = "certified_exact"
    BOUNDED_EXACT = "bounded_exact"
    STABILIZED_EMPIRICALLY = "stabilized_empirically"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class CertificateLevel(str, Enum):
    NONE = "none"
    STANDARD = "standard"
    FULL = "full"


@dataclass(frozen=True)
class BackendProvenance:
    backend: str
    algorithm: str
    version: str = ""
    parameters: Tuple[Tuple[str, Any], ...] = ()

    SCHEMA_ID = "mobility_toolkit.backend_provenance.v1"

    def __post_init__(self) -> None:
        if not self.backend or not self.algorithm:
            raise ValueError("backend and algorithm must be nonempty")
        normalized = tuple(sorted(tuple(item) for item in self.parameters))
        if any(len(item) != 2 or not isinstance(item[0], str) for item in normalized):
            raise ValueError("backend parameters must be (string, value) pairs")
        if len({item[0] for item in normalized}) != len(normalized):
            raise ValueError("backend parameter names must be unique")
        object.__setattr__(self, "parameters", normalized)

    def to_canonical_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "backend": self.backend,
            "parameters": self.parameters,
            "schema": self.SCHEMA_ID,
            "version": self.version,
        }


@dataclass(frozen=True)
class ComputationResult:
    """Versioned result wrapper shared by Python, CLI, MCP, and skills."""

    operation: str
    input_data: Any
    value: Any
    exactness: Exactness
    assumptions: Tuple[str, ...] = ()
    theorem_scope: str = ""
    certificate_level: CertificateLevel = CertificateLevel.NONE
    certificate: Any = None
    verification: Tuple[Tuple[str, Any], ...] = ()
    backend_provenance: Optional[BackendProvenance] = None
    resource_usage: Tuple[Tuple[str, Any], ...] = ()
    diagnostics: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    schema_version: str = "1"

    SCHEMA_ID = "mobility_toolkit.computation_result.v1"

    def __post_init__(self) -> None:
        if not self.operation:
            raise ValueError("operation must be nonempty")
        object.__setattr__(self, "assumptions", tuple(sorted(set(self.assumptions))))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        for field_name in ("verification", "resource_usage"):
            values = tuple(sorted(tuple(item) for item in getattr(self, field_name)))
            if any(len(item) != 2 or not isinstance(item[0], str) for item in values):
                raise ValueError(f"{field_name} must contain (string, value) pairs")
            if len({item[0] for item in values}) != len(values):
                raise ValueError(f"{field_name} names must be unique")
            object.__setattr__(self, field_name, values)

    @property
    def canonical_input_hash(self) -> str:
        return canonical_hash(f"operation:{self.operation}:schema:{self.schema_version}", self.input_data)

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "backend_provenance": self.backend_provenance,
            "canonical_input_hash": self.canonical_input_hash,
            "certificate": self.certificate,
            "certificate_level": self.certificate_level,
            "diagnostics": self.diagnostics,
            "exactness": self.exactness,
            "operation": self.operation,
            "resource_usage": self.resource_usage,
            "schema": self.SCHEMA_ID,
            "schema_version": self.schema_version,
            "theorem_scope": self.theorem_scope,
            "value": self.value,
            "verification": self.verification,
            "warnings": self.warnings,
        }


__all__ = [
    "BackendProvenance",
    "CertificateLevel",
    "ComputationResult",
    "Exactness",
]
