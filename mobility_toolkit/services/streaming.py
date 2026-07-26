"""Incremental page transport for resumable canonical enumerations.

Each yielded item is a complete ``ServiceExecution`` envelope.  The request in
that envelope contains the exact checkpoint used for the page, and the result
contains the next sealed checkpoint.  A caller may stop after any yielded item
and resume by putting that checkpoint back into the original input.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, Mapping

from mobility_toolkit.services.contracts import ServiceRequest


_STREAMABLE_OPERATIONS = frozenset(
    (
        "boundary.completion2d.enumerate",
        "boundary.symbolic3d.enumerate",
    )
)


def streamable_operations():
    return tuple(sorted(_STREAMABLE_OPERATIONS))


def _page_request(
    source: ServiceRequest,
    input_data: Mapping[str, Any],
) -> ServiceRequest:
    return ServiceRequest(
        operation=source.operation,
        input_data=dict(input_data),
        requested_certificate_level=source.requested_certificate_level,
        assumptions=source.assumptions,
        backend_fingerprint=source.backend_fingerprint,
        equivalence_relation=source.equivalence_relation,
        search_domain=source.search_domain,
        schema_version=source.schema_version,
    )


def stream_service_payload(
    payload: Mapping[str, Any],
    *,
    max_pages: int = 1000,
) -> Iterator[Dict[str, Any]]:
    """Yield resumable enumeration pages as canonical execution envelopes.

    ``max_pages`` is a transport resource ceiling, not a completeness claim.
    If it is reached, the last yielded result still contains a sealed
    ``next_checkpoint`` that can be supplied to a later stream request.
    """

    if (
        isinstance(max_pages, bool)
        or not isinstance(max_pages, int)
        or max_pages < 1
    ):
        raise ValueError("max_pages must be a positive integer")
    source = ServiceRequest.from_transport_dict(payload)
    if source.operation not in _STREAMABLE_OPERATIONS:
        raise ValueError(
            f"operation {source.operation!r} is not streamable; choose one of "
            + ", ".join(streamable_operations())
        )
    if not isinstance(source.input_data, Mapping):
        raise TypeError("streamable operation input_data must be an object")

    # Import lazily to avoid a default-registry import cycle.
    from mobility_toolkit.services.default import execute_service_request

    current_input = dict(source.input_data)
    current_input["max_pages"] = 1
    for _ in range(max_pages):
        execution = execute_service_request(
            _page_request(source, current_input)
        )
        transport = execution.to_transport_dict()
        yield transport
        value = transport["result"]["value"]
        if not isinstance(value, Mapping) or "next_checkpoint" not in value:
            raise ArithmeticError(
                "streamable operation omitted result.value.next_checkpoint"
            )
        checkpoint = value["next_checkpoint"]
        if checkpoint is None:
            return
        current_input["checkpoint"] = checkpoint


__all__ = ["stream_service_payload", "streamable_operations"]
