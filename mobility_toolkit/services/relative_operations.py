"""Canonical service operation for exact finite cellular relative homology."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
    SparseIntMatrix,
)
from mobility_toolkit.services.contracts import (
    ServiceCapability,
    ServiceCatalogEntry,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistration


_INTEGER = {"type": "integer"}
RELATIVE_HOMOLOGY_INPUT_SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "ambient": {
            "additionalProperties": False,
            "properties": {
                "assumptions": {"items": {"type": "string"}, "type": "array"},
                "boundary_maps": {"type": "array"},
                "cell_ids_by_dimension": {"type": "array"},
            },
            "required": ["cell_ids_by_dimension", "boundary_maps"],
            "type": "object",
        },
        "coefficient_modulus": _INTEGER,
        "degree": _INTEGER,
        "max_dense_entries": _INTEGER,
        "subcomplex_cell_ids_by_dimension": {"type": "array"},
    },
    "required": [
        "ambient",
        "subcomplex_cell_ids_by_dimension",
        "degree",
        "coefficient_modulus",
    ],
    "type": "object",
}


def _strict_object(
    value: Any,
    *,
    name: str,
    allowed: Sequence[str],
    required: Sequence[str] = (),
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    unknown = sorted(set(value) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {name} fields: " + ", ".join(unknown))
    missing = [field for field in required if field not in value]
    if missing:
        raise ValueError(f"missing {name} fields: " + ", ".join(missing))
    return value


def _array(value: Any, name: str) -> Tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be an array")
    return tuple(value)


def _integer(value: Any, name: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _decode_matrix(value: Any, index: int) -> SparseIntMatrix:
    name = f"ambient.boundary_maps[{index}]"
    data = _strict_object(
        value,
        name=name,
        allowed=("nrows", "ncols", "entries"),
        required=("nrows", "ncols", "entries"),
    )
    entries = []
    for entry_index, raw in enumerate(_array(data["entries"], f"{name}.entries")):
        entry = _array(raw, f"{name}.entries[{entry_index}]")
        if len(entry) != 3:
            raise ValueError(f"{name}.entries[{entry_index}] must have length 3")
        entries.append(
            (
                _integer(entry[0], "matrix row", minimum=0),
                _integer(entry[1], "matrix column", minimum=0),
                _integer(entry[2], "matrix coefficient"),
            )
        )
    return SparseIntMatrix(
        _integer(data["nrows"], f"{name}.nrows", minimum=0),
        _integer(data["ncols"], f"{name}.ncols", minimum=0),
        tuple(entries),
    )


def relative_homology_service(request: ServiceRequest) -> ComputationResult:
    from mobility_toolkit.finite import FlintIntegerBackend
    from mobility_toolkit.geometry import (
        FiniteCellComplex,
        RelativeCellularPair,
        relative_cellular_homology,
        verify_relative_chain_certificate,
        verify_relative_homology_result,
    )

    data = _strict_object(
        request.input_data,
        name="input_data",
        allowed=(
            "ambient",
            "subcomplex_cell_ids_by_dimension",
            "degree",
            "coefficient_modulus",
            "max_dense_entries",
        ),
        required=(
            "ambient",
            "subcomplex_cell_ids_by_dimension",
            "degree",
            "coefficient_modulus",
        ),
    )
    ambient_data = _strict_object(
        data["ambient"],
        name="ambient",
        allowed=("cell_ids_by_dimension", "boundary_maps", "assumptions"),
        required=("cell_ids_by_dimension", "boundary_maps"),
    )
    cells = tuple(
        tuple(_array(level, f"ambient.cell_ids_by_dimension[{index}]"))
        for index, level in enumerate(
            _array(
                ambient_data["cell_ids_by_dimension"],
                "ambient.cell_ids_by_dimension",
            )
        )
    )
    boundaries = tuple(
        _decode_matrix(matrix, index)
        for index, matrix in enumerate(
            _array(ambient_data["boundary_maps"], "ambient.boundary_maps")
        )
    )
    assumptions = tuple(
        str(value)
        for value in _array(ambient_data.get("assumptions", ()), "assumptions")
    )
    ambient = FiniteCellComplex(cells, boundaries, assumptions)
    subcomplex = tuple(
        tuple(_array(level, f"subcomplex[{index}]"))
        for index, level in enumerate(
            _array(
                data["subcomplex_cell_ids_by_dimension"],
                "subcomplex_cell_ids_by_dimension",
            )
        )
    )
    pair = RelativeCellularPair.create(ambient, subcomplex)
    backend = FlintIntegerBackend(
        max_dense_entries=_integer(
            data.get("max_dense_entries", 2_000_000),
            "max_dense_entries",
            minimum=1,
        )
    )
    result = relative_cellular_homology(
        pair,
        _integer(data["degree"], "degree", minimum=0),
        _integer(
            data["coefficient_modulus"],
            "coefficient_modulus",
            minimum=2,
        ),
        backend,
    )
    verify_relative_chain_certificate(
        pair, result.relative_chain_complex.certificate
    )
    verify_relative_homology_result(result, backend)
    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=result,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=request.assumptions,
        theorem_scope=(
            "Exact cellular relative homology H_degree(X,A;Z/N) for the "
            "explicitly supplied finite boundary-closed cellular pair. This "
            "is neither a Laurent half-space computation nor Ext_R(M,R/I)."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate={
            "homology": result.certificate,
            "relative_chain": result.relative_chain_complex.certificate,
        },
        verification=(
            ("boundary_closed_subcomplex_verified", True),
            (
                "homology_invariant_factors_match_certificate",
                result.invariant_factors
                == result.certificate.invariant_factors,
            ),
            ("relative_chain_certificate_replayed", True),
            ("relative_homology_semantic_replay_verified", True),
        ),
        backend_provenance=BackendProvenance(
            getattr(backend, "name", backend.__class__.__name__),
            "finite-cellular-relative-homology",
            getattr(backend, "version", ""),
            (
                (
                    "max_dense_entries",
                    getattr(backend, "max_dense_entries", None),
                ),
            ),
        ),
        warnings=(
            "A code-specific dictionary is required before relative homology "
            "classes are called logical operators or boundary excitations.",
        ),
        schema_version=request.schema_version,
    )


def _capability(request: ServiceRequest) -> ServiceCapability:
    return ServiceCapability(
        operation=request.operation,
        supported=True,
        maximum_exactness=Exactness.CERTIFIED_EXACT,
        backend_fingerprint=request.backend_fingerprint,
        reason=(
            "Exact for the explicitly supplied finite boundary-closed "
            "cellular pair."
        ),
        maximum_certificate_level=CertificateLevel.FULL,
        input_schema=RELATIVE_HOMOLOGY_INPUT_SCHEMA,
        constraints=(("requires_python_flint", True),),
    )


def relative_service_registrations() -> Tuple[ServiceRegistration, ...]:
    operation = "topology.relative_homology"
    return (
        ServiceRegistration(
            operation=operation,
            handler=relative_homology_service,
            capability=_capability,
            catalog=ServiceCatalogEntry(
                operation=operation,
                summary=(
                    "Exact cellular relative homology of an explicit finite pair."
                ),
                input_schema=RELATIVE_HOMOLOGY_INPUT_SCHEMA,
                adapter_kind="native",
                cacheable=True,
            ),
        ),
    )


__all__ = [
    "RELATIVE_HOMOLOGY_INPUT_SCHEMA",
    "relative_homology_service",
    "relative_service_registrations",
]
