"""Caller-owned persistence for resumable service enumeration checkpoints.

Importing this module never opens or creates a database.  Persistence begins
only when a caller explicitly constructs :class:`SQLiteCheckpointStore`.
The store records incomplete, canonical streaming pages; it does not execute
operations, choose a default path, or create process-global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Optional, Tuple, Union

from mobility_toolkit.core import canonical_hash, canonical_json
from mobility_toolkit.services.contracts import ServiceExecution, ServiceRequest
from mobility_toolkit.services.streaming import streamable_operations


_STORE_SCHEMA = "mobility_toolkit.sqlite_checkpoint_store.v1"
_STORE_VERSION = "1"
_BASE_REQUEST_SCHEMA = "mobility_toolkit.checkpoint_base_request.v1"
_EXECUTION_SCHEMA = ServiceExecution.SCHEMA_ID
_RESULT_SCHEMA = "mobility_toolkit.computation_result.v1"
_REQUEST_FIELDS = frozenset(
    (
        "assumptions",
        "backend_fingerprint",
        "equivalence_relation",
        "input_data",
        "operation",
        "requested_certificate_level",
        "schema",
        "schema_version",
        "search_domain",
    )
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _session_id(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("session_id must be a nonempty string")
    return value


def _canonical_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    # Canonicalization rejects floats, non-string keys, and implicit dataclass
    # traversal.  Round-tripping also detaches mutable caller-owned objects.
    return json.loads(canonical_json(value))


def _request_from_execution(payload: Mapping[str, Any]) -> ServiceRequest:
    request_payload = _canonical_mapping(payload.get("request"), "execution.request")
    unknown = sorted(set(request_payload) - (_REQUEST_FIELDS | {"canonical_input_hash"}))
    if unknown:
        raise ValueError(
            "unknown execution.request fields: " + ", ".join(unknown)
        )
    decoded_payload = {
        key: value for key, value in request_payload.items() if key in _REQUEST_FIELDS
    }
    request = ServiceRequest.from_transport_dict(decoded_payload)
    recorded_hash = request_payload.get("canonical_input_hash")
    if recorded_hash != request.canonical_input_hash:
        raise ValueError("execution request canonical_input_hash is missing or invalid")
    return request


def _transport_request(request: ServiceRequest) -> dict:
    """Return a payload accepted by ``ServiceRequest.from_transport_dict``."""

    canonical = request.to_transport_dict()
    return {key: canonical[key] for key in _REQUEST_FIELDS if key in canonical}


def _base_request(request: ServiceRequest) -> Tuple[dict, str]:
    if not isinstance(request.input_data, Mapping):
        raise TypeError("streamable operation input_data must be an object")
    input_data = dict(request.input_data)
    input_data.pop("checkpoint", None)
    input_data.pop("max_pages", None)
    base = ServiceRequest(
        operation=request.operation,
        input_data=input_data,
        requested_certificate_level=request.requested_certificate_level,
        assumptions=request.assumptions,
        backend_fingerprint=request.backend_fingerprint,
        equivalence_relation=request.equivalence_relation,
        search_domain=request.search_domain,
        schema_version=request.schema_version,
    )
    payload = _transport_request(base)
    return payload, canonical_hash(_BASE_REQUEST_SCHEMA, payload)


def _validated_page(
    execution: Union[ServiceExecution, Mapping[str, Any]]
) -> Tuple[dict, ServiceRequest, dict, str, dict]:
    if isinstance(execution, ServiceExecution):
        payload = execution.to_transport_dict()
    elif isinstance(execution, Mapping):
        payload = json.loads(canonical_json(execution))
    else:
        raise TypeError("execution must be a ServiceExecution or transport object")

    allowed = {"cache", "capability", "request", "result", "schema"}
    if set(payload) != allowed:
        missing = sorted(allowed - set(payload))
        unknown = sorted(set(payload) - allowed)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise ValueError("invalid service execution envelope: " + "; ".join(details))
    if payload["schema"] != _EXECUTION_SCHEMA:
        raise ValueError("unsupported service execution schema")

    request = _request_from_execution(payload)
    if request.operation not in streamable_operations():
        raise ValueError(f"operation {request.operation!r} is not streamable")

    cache = _canonical_mapping(payload["cache"], "execution.cache")
    if set(cache) != {"hit", "key"} or not isinstance(cache["hit"], bool):
        raise ValueError("execution.cache must contain exactly boolean hit and key")
    if cache["key"] != request.cache_key:
        raise ValueError("execution cache key does not match its request")

    capability = _canonical_mapping(
        payload["capability"], "execution.capability"
    )
    if capability.get("operation") != request.operation:
        raise ValueError("execution capability operation differs from request")

    result = _canonical_mapping(payload["result"], "execution.result")
    if result.get("schema") != _RESULT_SCHEMA:
        raise ValueError("unsupported computation result schema")
    if result.get("operation") != request.operation:
        raise ValueError("execution result operation differs from request")
    if result.get("canonical_input_hash") != request.canonical_input_hash:
        raise ValueError("execution result canonical_input_hash differs from request")
    if result.get("schema_version") != request.schema_version:
        raise ValueError("execution result schema_version differs from request")
    if sorted(result.get("assumptions", ())) != list(request.assumptions):
        raise ValueError("execution result assumptions differ from request")

    value = _canonical_mapping(result.get("value"), "execution.result.value")
    if "next_checkpoint" not in value:
        raise ValueError("streaming result omitted value.next_checkpoint")
    checkpoint = value["next_checkpoint"]
    if checkpoint is None:
        raise ValueError("completed streaming pages have no checkpoint to persist")
    checkpoint = dict(_canonical_mapping(checkpoint, "next_checkpoint"))
    if not isinstance(checkpoint.get("schema"), str) or not checkpoint["schema"]:
        raise ValueError("next_checkpoint must contain a nonempty schema")

    base_payload, base_hash = _base_request(request)
    return payload, request, base_payload, base_hash, checkpoint


@dataclass(frozen=True)
class CheckpointRecord:
    """Public metadata for one active caller-owned resume chain."""

    session_id: str
    operation: str
    base_request_hash: str
    sequence: int
    updated_at: str


class SQLiteCheckpointStore:
    """Explicit SQLite persistence for canonical stream checkpoint chains."""

    SCHEMA_ID = _STORE_SCHEMA

    def __init__(self, path: Union[str, Path]) -> None:
        if not isinstance(path, (str, Path)):
            raise TypeError("path must be a string or pathlib.Path")
        if str(path) == "":
            raise ValueError("path must not be empty")
        self.path = Path(path)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._closed = False
        try:
            self._initialize()
        except Exception:
            self._connection.close()
            self._closed = True
            raise

    def _initialize(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoint_store_metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    schema_id TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                )
                """
            )
            row = self._connection.execute(
                """
                SELECT schema_id, schema_version
                FROM checkpoint_store_metadata
                WHERE singleton = ?
                """,
                (1,),
            ).fetchone()
            if row is None:
                self._connection.execute(
                    """
                    INSERT INTO checkpoint_store_metadata (
                        singleton, schema_id, schema_version
                    ) VALUES (?, ?, ?)
                    """,
                    (1, self.SCHEMA_ID, _STORE_VERSION),
                )
            elif (
                row["schema_id"] != self.SCHEMA_ID
                or row["schema_version"] != _STORE_VERSION
            ):
                raise ValueError(
                    "unsupported checkpoint database schema/version "
                    f"{row['schema_id']!r}/{row['schema_version']!r}; expected "
                    f"{self.SCHEMA_ID!r}/{_STORE_VERSION!r}"
                )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS service_checkpoints (
                    session_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    base_request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence > 0),
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, operation, base_request_hash)
                )
                """
            )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("checkpoint store is closed")

    def save_page(
        self,
        session_id: str,
        execution: Union[ServiceExecution, Mapping[str, Any]],
        *,
        sequence: Optional[int] = None,
    ) -> CheckpointRecord:
        """Persist the next sealed checkpoint in one streaming execution page.

        Pages must form a contiguous chain.  After the first save, the
        checkpoint used by the incoming page must exactly equal the checkpoint
        stored by the preceding page.
        """

        self._ensure_open()
        session_id = _session_id(session_id)
        _, request, base_payload, base_hash, checkpoint = _validated_page(execution)
        request_json = canonical_json(base_payload)
        checkpoint_json = canonical_json(checkpoint)
        incoming_checkpoint = request.input_data.get("checkpoint")
        if incoming_checkpoint is not None:
            incoming_checkpoint = canonical_json(
                _canonical_mapping(incoming_checkpoint, "request checkpoint")
            )
        if sequence is not None and (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 1
        ):
            raise ValueError("sequence must be a positive integer")

        now = _utc_timestamp()
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute(
                """
                SELECT request_json, checkpoint_json, sequence
                FROM service_checkpoints
                WHERE session_id = ? AND operation = ? AND base_request_hash = ?
                """,
                (session_id, request.operation, base_hash),
            ).fetchone()
            if row is None:
                foreign = self._connection.execute(
                    """
                    SELECT operation, base_request_hash
                    FROM service_checkpoints
                    WHERE session_id = ?
                    LIMIT 1
                    """,
                    (session_id,),
                ).fetchone()
                if foreign is not None:
                    raise ValueError(
                        "session_id is already bound to a foreign operation "
                        "or base request identity"
                    )
                if incoming_checkpoint is not None:
                    raise ValueError(
                        "cannot start a checkpoint chain from an unverified resume page"
                    )
                next_sequence = 1
                if sequence is not None and sequence != next_sequence:
                    raise ValueError(
                        f"sequence regression or gap: expected {next_sequence}"
                    )
                self._connection.execute(
                    """
                    INSERT INTO service_checkpoints (
                        session_id, operation, base_request_hash, request_json,
                        checkpoint_json, sequence, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        request.operation,
                        base_hash,
                        request_json,
                        checkpoint_json,
                        next_sequence,
                        now,
                    ),
                )
            else:
                if row["request_json"] != request_json:
                    raise ValueError("stored base request identity is inconsistent")
                if incoming_checkpoint is None:
                    raise ValueError("sequence regression: resume page omitted checkpoint")
                if incoming_checkpoint != row["checkpoint_json"]:
                    raise ValueError(
                        "resume page checkpoint does not match the stored sequence"
                    )
                if checkpoint_json == row["checkpoint_json"]:
                    raise ValueError("checkpoint sequence made no forward progress")
                next_sequence = int(row["sequence"]) + 1
                if sequence is not None and sequence != next_sequence:
                    raise ValueError(
                        f"sequence regression or gap: expected {next_sequence}"
                    )
                updated = self._connection.execute(
                    """
                    UPDATE service_checkpoints
                    SET checkpoint_json = ?, sequence = ?, updated_at = ?
                    WHERE session_id = ? AND operation = ?
                      AND base_request_hash = ? AND sequence = ?
                    """,
                    (
                        checkpoint_json,
                        next_sequence,
                        now,
                        session_id,
                        request.operation,
                        base_hash,
                        int(row["sequence"]),
                    ),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("concurrent checkpoint sequence update")
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

        return CheckpointRecord(
            session_id=session_id,
            operation=request.operation,
            base_request_hash=base_hash,
            sequence=next_sequence,
            updated_at=now,
        )

    def _load_rows(self, session_id: str):
        return self._connection.execute(
            """
            SELECT session_id, operation, base_request_hash, request_json,
                   checkpoint_json, sequence, updated_at
            FROM service_checkpoints
            WHERE session_id = ?
            ORDER BY operation, base_request_hash
            """,
            (session_id,),
        ).fetchall()

    def load_resume_payload(self, session_id: str) -> dict:
        """Return the unique active session as a valid streaming request."""

        self._ensure_open()
        session_id = _session_id(session_id)
        rows = self._load_rows(session_id)
        if not rows:
            raise KeyError(f"no checkpoint for session {session_id!r}")
        if len(rows) != 1:
            raise ValueError(
                "session has multiple checkpoint chains; clear or use distinct session_ids"
            )
        row = rows[0]
        try:
            request_payload = json.loads(row["request_json"])
            checkpoint = json.loads(row["checkpoint_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("stored checkpoint JSON is invalid") from exc
        if canonical_json(request_payload) != row["request_json"]:
            raise ValueError("stored request JSON is not canonical")
        if canonical_json(checkpoint) != row["checkpoint_json"]:
            raise ValueError("stored checkpoint JSON is not canonical")
        request = ServiceRequest.from_transport_dict(request_payload)
        if request.operation != row["operation"]:
            raise ValueError("stored operation differs from canonical request")
        if request.operation not in streamable_operations():
            raise ValueError("stored operation is no longer streamable")
        _, expected_hash = _base_request(request)
        if expected_hash != row["base_request_hash"]:
            raise ValueError("stored base request hash is invalid")
        if not isinstance(checkpoint, Mapping):
            raise ValueError("stored checkpoint must be an object")
        if not isinstance(checkpoint.get("schema"), str) or not checkpoint["schema"]:
            raise ValueError("stored checkpoint schema is invalid")

        input_data = dict(request.input_data)
        input_data["checkpoint"] = checkpoint
        resumed = ServiceRequest(
            operation=request.operation,
            input_data=input_data,
            requested_certificate_level=request.requested_certificate_level,
            assumptions=request.assumptions,
            backend_fingerprint=request.backend_fingerprint,
            equivalence_relation=request.equivalence_relation,
            search_domain=request.search_domain,
            schema_version=request.schema_version,
        )
        payload = _transport_request(resumed)
        # This is an executable public transport payload, not a stored internal
        # envelope.  Validate it with the same decoder used by the stream API.
        ServiceRequest.from_transport_dict(payload)
        return payload

    def list(self, session_id: Optional[str] = None) -> Tuple[CheckpointRecord, ...]:
        """List active resume chains without exposing checkpoint contents."""

        self._ensure_open()
        if session_id is None:
            rows = self._connection.execute(
                """
                SELECT session_id, operation, base_request_hash, sequence, updated_at
                FROM service_checkpoints
                ORDER BY session_id, operation, base_request_hash
                """
            ).fetchall()
        else:
            session_id = _session_id(session_id)
            rows = self._connection.execute(
                """
                SELECT session_id, operation, base_request_hash, sequence, updated_at
                FROM service_checkpoints
                WHERE session_id = ?
                ORDER BY operation, base_request_hash
                """,
                (session_id,),
            ).fetchall()
        return tuple(
            CheckpointRecord(
                session_id=row["session_id"],
                operation=row["operation"],
                base_request_hash=row["base_request_hash"],
                sequence=int(row["sequence"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        )

    def list_checkpoints(
        self, session_id: Optional[str] = None
    ) -> Tuple[CheckpointRecord, ...]:
        """Named alias for callers that avoid the compact ``list`` API."""

        return self.list(session_id)

    def clear(self, session_id: str) -> int:
        """Explicitly remove every active chain owned by ``session_id``."""

        self._ensure_open()
        session_id = _session_id(session_id)
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM service_checkpoints WHERE session_id = ?",
                (session_id,),
            )
        return int(cursor.rowcount)

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> "SQLiteCheckpointStore":
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


__all__ = ["CheckpointRecord", "SQLiteCheckpointStore"]
