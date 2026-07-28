"""Canonical serialization helpers for mathematical IR objects."""

from __future__ import annotations

import hashlib
import json
from dataclasses import is_dataclass
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping


def canonicalize(value: Any) -> Any:
    """Return a JSON-compatible canonical representation.

    Mathematical identity must never depend on dictionary insertion order,
    backend pretty-printing, or floating-point formatting. Objects in the core
    expose ``to_canonical_dict`` explicitly; arbitrary dataclass traversal is
    intentionally rejected so new fields cannot silently enter a cache key.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("floating-point values are not allowed in canonical mathematical data")
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if isinstance(value, Fraction):
        return {"denominator": value.denominator, "numerator": value.numerator}
    if hasattr(value, "to_canonical_dict"):
        return canonicalize(value.to_canonical_dict())
    if is_dataclass(value):
        raise TypeError(
            f"dataclass {type(value).__name__} must define to_canonical_dict explicitly"
        )
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mapping keys must be strings")
            result[key] = canonicalize(item)
        return result
    if isinstance(value, (tuple, list)):
        return [canonicalize(item) for item in value]
    raise TypeError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize canonical mathematical data as compact UTF-8 JSON text."""

    return json.dumps(
        canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_hash(schema_id: str, value: Any) -> str:
    """Hash ``schema_id`` and canonical mathematical JSON with SHA-256."""

    if not isinstance(schema_id, str) or not schema_id:
        raise ValueError("schema_id must be a nonempty string")
    payload = schema_id.encode("utf-8") + b"\0" + canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = ["canonical_hash", "canonical_json", "canonicalize"]
