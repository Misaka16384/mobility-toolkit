"""Canonical service operations for periodic Laurent presentations.

The public transport in this module is the canonical mathematical IR.  In
particular, Laurent polynomials are arrays of structured terms; polynomial
strings and legacy flat Pauli matrices are not accepted.  Every Pauli basis
coordinate also carries its local order, and the corresponding order
relations must be supplied explicitly.

The Macaulay2 bridge remains deliberately narrow.  The support decision is
delegated to :class:`~mobility_toolkit.periodic.PeriodicSupportMatrix` through
``StructuredMacaulay2Backend``.  Composite and nonuniform requests therefore
produce the backend's structured experimental/unsupported result instead of
being coerced into a uniform-prime computation.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from mobility_toolkit.core import (
    CertificateLevel,
    ComputationResult,
    Exactness,
    LaurentPolynomial,
    LaurentTerm,
    TranslationGroup,
)
from mobility_toolkit.periodic import (
    LaurentModuleElement,
    LocalOrderRelation,
    PauliAxis,
    PauliBasisElement,
    PeriodicBackendRequest,
    PeriodicOperation,
    QuasiFreePauliModulePresentation,
    StabilizerImage,
    StabilizerImageColumn,
    StructuredMacaulay2Backend,
    SupportTier,
)
from mobility_toolkit.services.contracts import (
    ServiceCapability,
    ServiceCatalogEntry,
    ServiceRequest,
)
from mobility_toolkit.services.registry import ServiceRegistration


def _object_schema(
    required: Sequence[str], properties: Mapping[str, Any]
) -> dict:
    return {
        "additionalProperties": False,
        "properties": dict(properties),
        "required": list(required),
        "type": "object",
    }


_INTEGER = {"type": "integer"}
_NONNEGATIVE_INTEGER = {"minimum": 0, "type": "integer"}
_POSITIVE_ORDER = {"minimum": 2, "type": "integer"}
_STRING = {"minLength": 1, "type": "string"}
_SCHEMA = {"minLength": 1, "type": "string"}

TRANSLATION_GROUP_SCHEMA = _object_schema(
    ("free_rank", "torsion_invariants", "free_generator_names"),
    {
        "free_generator_names": {"items": _STRING, "type": "array"},
        "free_rank": _NONNEGATIVE_INTEGER,
        "schema": _SCHEMA,
        "torsion_invariants": {"items": _POSITIVE_ORDER, "type": "array"},
    },
)
LAURENT_TERM_SCHEMA = _object_schema(
    ("coefficient", "free_exponents", "torsion_exponents"),
    {
        "coefficient": _INTEGER,
        "free_exponents": {"items": _INTEGER, "type": "array"},
        "schema": _SCHEMA,
        "torsion_exponents": {"items": _INTEGER, "type": "array"},
    },
)
LAURENT_POLYNOMIAL_SCHEMA = _object_schema(
    ("coefficient_modulus", "translation_group", "terms"),
    {
        "coefficient_modulus": _POSITIVE_ORDER,
        "schema": _SCHEMA,
        "terms": {"items": LAURENT_TERM_SCHEMA, "type": "array"},
        "translation_group": TRANSLATION_GROUP_SCHEMA,
    },
)
PAULI_BASIS_SCHEMA = _object_schema(
    ("axis", "basis_id", "species_id", "component", "local_order"),
    {
        "axis": {"enum": ("X", "Z")},
        "basis_id": _STRING,
        "component": _NONNEGATIVE_INTEGER,
        "local_order": _POSITIVE_ORDER,
        "schema": _SCHEMA,
        "species_id": _STRING,
    },
)
LOCAL_ORDER_RELATION_SCHEMA = _object_schema(
    ("basis_id", "order"),
    {
        "basis_id": _STRING,
        "order": _POSITIVE_ORDER,
        "schema": _SCHEMA,
    },
)
LAURENT_ENTRY_SCHEMA = {
    "items": (_STRING, LAURENT_POLYNOMIAL_SCHEMA),
    "maxItems": 2,
    "minItems": 2,
    "type": "array",
}
LAURENT_MODULE_ELEMENT_SCHEMA = _object_schema(
    ("entries",),
    {
        "entries": {"items": LAURENT_ENTRY_SCHEMA, "type": "array"},
        "schema": _SCHEMA,
    },
)
STABILIZER_COLUMN_SCHEMA = _object_schema(
    ("generator_id", "phase", "image"),
    {
        "generator_id": _STRING,
        "image": LAURENT_MODULE_ELEMENT_SCHEMA,
        "phase": _INTEGER,
        "schema": _SCHEMA,
    },
)
STABILIZER_IMAGE_SCHEMA = _object_schema(
    ("columns",),
    {
        "columns": {"items": STABILIZER_COLUMN_SCHEMA, "type": "array"},
        "schema": _SCHEMA,
    },
)
PERIODIC_PRESENTATION_SCHEMA = _object_schema(
    (
        "translation_group",
        "coefficient_modulus",
        "basis",
        "local_order_relations",
        "stabilizer_image",
        "phase_modulus",
    ),
    {
        "basis": {"items": PAULI_BASIS_SCHEMA, "type": "array"},
        "coefficient_modulus": _POSITIVE_ORDER,
        "local_order_relations": {
            "items": LOCAL_ORDER_RELATION_SCHEMA,
            "type": "array",
        },
        "phase_modulus": _POSITIVE_ORDER,
        "schema": _SCHEMA,
        "stabilizer_image": STABILIZER_IMAGE_SCHEMA,
        "translation_group": TRANSLATION_GROUP_SCHEMA,
    },
)
PERIODIC_PRESENTATION_INPUT_SCHEMA = _object_schema(
    ("presentation",),
    {"presentation": PERIODIC_PRESENTATION_SCHEMA},
)
PERIODIC_EXT_INPUT_SCHEMA = _object_schema(
    ("presentation",),
    {
        "charge_degree": _NONNEGATIVE_INTEGER,
        "presentation": PERIODIC_PRESENTATION_SCHEMA,
        "validate_stabilizer": {"type": "boolean"},
    },
)


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


def _sequence(value: Any, name: str) -> Tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{name} must be an array")
    return tuple(value)


def _integer(value: Any, name: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")
    return value


def _check_schema(
    value: Mapping[str, Any], expected: str, name: str
) -> None:
    if "schema" in value and value["schema"] != expected:
        raise ValueError(
            f"{name}.schema must be {expected!r}, got {value['schema']!r}"
        )


def decode_translation_group(value: Any) -> TranslationGroup:
    """Decode one canonical finitely generated translation group."""

    data = _strict_object(
        value,
        name="translation_group",
        allowed=(
            "schema",
            "free_rank",
            "torsion_invariants",
            "free_generator_names",
        ),
        required=("free_rank", "torsion_invariants", "free_generator_names"),
    )
    _check_schema(data, TranslationGroup.SCHEMA_ID, "translation_group")
    names = tuple(
        _string(item, f"free_generator_names[{index}]")
        for index, item in enumerate(
            _sequence(data["free_generator_names"], "free_generator_names")
        )
    )
    torsion = tuple(
        _integer(item, f"torsion_invariants[{index}]", minimum=2)
        for index, item in enumerate(
            _sequence(data["torsion_invariants"], "torsion_invariants")
        )
    )
    return TranslationGroup(
        _integer(data["free_rank"], "free_rank", minimum=0),
        torsion,
        names,
    )


def _decode_term(
    value: Any,
    group: TranslationGroup,
    *,
    name: str,
) -> LaurentTerm:
    data = _strict_object(
        value,
        name=name,
        allowed=("schema", "coefficient", "free_exponents", "torsion_exponents"),
        required=("coefficient", "free_exponents", "torsion_exponents"),
    )
    _check_schema(data, LaurentTerm.SCHEMA_ID, name)
    free = tuple(
        _integer(item, f"{name}.free_exponents[{index}]")
        for index, item in enumerate(
            _sequence(data["free_exponents"], f"{name}.free_exponents")
        )
    )
    torsion = tuple(
        _integer(item, f"{name}.torsion_exponents[{index}]")
        for index, item in enumerate(
            _sequence(data["torsion_exponents"], f"{name}.torsion_exponents")
        )
    )
    if len(free) != group.free_rank:
        raise ValueError(f"{name}.free_exponents does not match free_rank")
    if len(torsion) != len(group.torsion_invariants):
        raise ValueError(
            f"{name}.torsion_exponents does not match torsion_invariants"
        )
    return LaurentTerm(_integer(data["coefficient"], f"{name}.coefficient"), free, torsion)


def _decode_polynomial(
    value: Any,
    group: TranslationGroup,
    coefficient_modulus: int,
    *,
    name: str,
) -> LaurentPolynomial:
    if isinstance(value, str):
        raise TypeError(
            f"{name} must be a structured Laurent-polynomial object, not a string"
        )
    data = _strict_object(
        value,
        name=name,
        allowed=("schema", "coefficient_modulus", "translation_group", "terms"),
        required=("coefficient_modulus", "translation_group", "terms"),
    )
    _check_schema(data, LaurentPolynomial.SCHEMA_ID, name)
    declared_modulus = _integer(
        data["coefficient_modulus"],
        f"{name}.coefficient_modulus",
        minimum=2,
    )
    if declared_modulus != coefficient_modulus:
        raise ValueError(f"{name} coefficient_modulus differs from presentation")
    declared_group = decode_translation_group(data["translation_group"])
    if declared_group != group:
        raise ValueError(f"{name} translation_group differs from presentation")
    terms = tuple(
        _decode_term(item, group, name=f"{name}.terms[{index}]")
        for index, item in enumerate(_sequence(data["terms"], f"{name}.terms"))
    )
    return LaurentPolynomial(coefficient_modulus, group, terms)


def decode_periodic_presentation(
    value: Any,
) -> QuasiFreePauliModulePresentation:
    """Decode the canonical quasi-free presentation with recursive checks."""

    data = _strict_object(
        value,
        name="presentation",
        allowed=(
            "schema",
            "translation_group",
            "coefficient_modulus",
            "basis",
            "local_order_relations",
            "stabilizer_image",
            "phase_modulus",
        ),
        required=(
            "translation_group",
            "coefficient_modulus",
            "basis",
            "local_order_relations",
            "stabilizer_image",
            "phase_modulus",
        ),
    )
    _check_schema(
        data, QuasiFreePauliModulePresentation.SCHEMA_ID, "presentation"
    )
    group = decode_translation_group(data["translation_group"])
    modulus = _integer(
        data["coefficient_modulus"], "coefficient_modulus", minimum=2
    )

    basis = []
    for index, raw in enumerate(_sequence(data["basis"], "basis")):
        name = f"basis[{index}]"
        item = _strict_object(
            raw,
            name=name,
            allowed=(
                "schema",
                "axis",
                "basis_id",
                "species_id",
                "component",
                "local_order",
            ),
            required=(
                "axis",
                "basis_id",
                "species_id",
                "component",
                "local_order",
            ),
        )
        _check_schema(item, PauliBasisElement.SCHEMA_ID, name)
        try:
            axis = PauliAxis(item["axis"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name}.axis must be 'X' or 'Z'") from exc
        element = PauliBasisElement(
            axis,
            _string(item["species_id"], f"{name}.species_id"),
            _integer(item["component"], f"{name}.component", minimum=0),
            _integer(item["local_order"], f"{name}.local_order", minimum=2),
        )
        if item["basis_id"] != element.basis_id:
            raise ValueError(
                f"{name}.basis_id must equal the derived ID {element.basis_id!r}"
            )
        basis.append(element)

    relations = []
    for index, raw in enumerate(
        _sequence(data["local_order_relations"], "local_order_relations")
    ):
        name = f"local_order_relations[{index}]"
        item = _strict_object(
            raw,
            name=name,
            allowed=("schema", "basis_id", "order"),
            required=("basis_id", "order"),
        )
        _check_schema(item, LocalOrderRelation.SCHEMA_ID, name)
        relations.append(
            LocalOrderRelation(
                _string(item["basis_id"], f"{name}.basis_id"),
                _integer(item["order"], f"{name}.order", minimum=2),
            )
        )

    stabilizer_data = _strict_object(
        data["stabilizer_image"],
        name="stabilizer_image",
        allowed=("schema", "columns"),
        required=("columns",),
    )
    _check_schema(stabilizer_data, StabilizerImage.SCHEMA_ID, "stabilizer_image")
    columns = []
    for column_index, raw_column in enumerate(
        _sequence(stabilizer_data["columns"], "stabilizer_image.columns")
    ):
        column_name = f"stabilizer_image.columns[{column_index}]"
        column_data = _strict_object(
            raw_column,
            name=column_name,
            allowed=("schema", "generator_id", "phase", "image"),
            required=("generator_id", "phase", "image"),
        )
        _check_schema(
            column_data, StabilizerImageColumn.SCHEMA_ID, column_name
        )
        image_name = f"{column_name}.image"
        image_data = _strict_object(
            column_data["image"],
            name=image_name,
            allowed=("schema", "entries"),
            required=("entries",),
        )
        _check_schema(image_data, LaurentModuleElement.SCHEMA_ID, image_name)
        entries = []
        for entry_index, raw_entry in enumerate(
            _sequence(image_data["entries"], f"{image_name}.entries")
        ):
            entry_name = f"{image_name}.entries[{entry_index}]"
            entry = _sequence(raw_entry, entry_name)
            if len(entry) != 2:
                raise ValueError(
                    f"{entry_name} must be [basis_id, LaurentPolynomial]"
                )
            basis_id = _string(entry[0], f"{entry_name}[0]")
            polynomial = _decode_polynomial(
                entry[1],
                group,
                modulus,
                name=f"{entry_name}[1]",
            )
            entries.append((basis_id, polynomial))
        columns.append(
            StabilizerImageColumn(
                _string(
                    column_data["generator_id"],
                    f"{column_name}.generator_id",
                ),
                _integer(column_data["phase"], f"{column_name}.phase"),
                LaurentModuleElement(tuple(entries)),
            )
        )

    orders = tuple(element.local_order for element in basis)
    if orders and any(modulus % order for order in orders):
        raise ValueError("every local_order must divide coefficient_modulus")
    if orders and math.lcm(*orders) != modulus:
        raise ValueError(
            "coefficient_modulus must be the least common multiple of local orders"
        )
    return QuasiFreePauliModulePresentation(
        translation_group=group,
        coefficient_modulus=modulus,
        basis=tuple(basis),
        local_order_relations=tuple(relations),
        stabilizer_image=StabilizerImage(tuple(columns)),
        phase_modulus=_integer(
            data["phase_modulus"], "phase_modulus", minimum=2
        ),
    )


def _decode_backend_request(
    request: ServiceRequest, operation: PeriodicOperation
) -> PeriodicBackendRequest:
    allowed = ("presentation",)
    if operation is not PeriodicOperation.PRESENTATION:
        allowed += ("charge_degree", "validate_stabilizer")
    data = _strict_object(
        request.input_data,
        name="input_data",
        allowed=allowed,
        required=("presentation",),
    )
    presentation = decode_periodic_presentation(data["presentation"])
    charge_degree = (
        0
        if operation is PeriodicOperation.PRESENTATION
        else _integer(data.get("charge_degree", 0), "charge_degree", minimum=0)
    )
    validate = (
        True
        if operation is PeriodicOperation.PRESENTATION
        else _boolean(
            data.get("validate_stabilizer", True), "validate_stabilizer"
        )
    )
    return PeriodicBackendRequest(
        operation,
        presentation,
        charge_degree=charge_degree,
        validate_stabilizer=validate,
    )


def _reframe_backend_result(
    request: ServiceRequest, source: ComputationResult
) -> ComputationResult:
    """Bind a backend-native result to the public service request identity."""

    return ComputationResult(
        operation=request.operation,
        input_data=request.input_data,
        value=source.value,
        exactness=source.exactness,
        assumptions=request.assumptions,
        theorem_scope=source.theorem_scope,
        certificate_level=source.certificate_level,
        certificate=source.certificate,
        verification=tuple(source.verification)
        + (
            ("source_assumptions", source.assumptions),
            ("source_input_hash", source.canonical_input_hash),
            ("source_operation", source.operation),
        ),
        backend_provenance=source.backend_provenance,
        resource_usage=source.resource_usage,
        diagnostics=source.diagnostics,
        warnings=source.warnings,
        schema_version=request.schema_version,
    )


def _handler(
    backend: StructuredMacaulay2Backend,
    operation: PeriodicOperation,
) -> Callable[[ServiceRequest], ComputationResult]:
    def execute(request: ServiceRequest) -> ComputationResult:
        backend_request = _decode_backend_request(request, operation)
        response = backend.execute(backend_request)
        return _reframe_backend_result(request, response.computation)

    return execute


def _capability(
    backend: StructuredMacaulay2Backend,
    operation: PeriodicOperation,
    input_schema: Any,
) -> Callable[[ServiceRequest], ServiceCapability]:
    def report(request: ServiceRequest) -> ServiceCapability:
        backend_request = _decode_backend_request(request, operation)
        decision = backend.supports(backend_request)
        if decision.tier is SupportTier.PRODUCTION:
            certificate_level = (
                CertificateLevel.FULL
                if operation is PeriodicOperation.PRESENTATION
                else CertificateLevel.STANDARD
            )
            execution_mode = "computed"
        else:
            certificate_level = CertificateLevel.NONE
            execution_mode = "structured_refusal"
        return ServiceCapability(
            operation=request.operation,
            # The service operation itself is supported for every decoded
            # coefficient domain: unsupported mathematics is represented as a
            # structured ComputationResult instead of a dispatch exception.
            supported=True,
            maximum_exactness=decision.exactness,
            backend_fingerprint=request.backend_fingerprint,
            reason=decision.reason,
            maximum_certificate_level=certificate_level,
            input_schema=input_schema,
            constraints=(
                ("backend", decision.backend),
                ("coefficient_domain", decision.coefficient_domain.value),
                ("execution_mode", execution_mode),
                ("support_tier", decision.tier.value),
            ),
        )

    return report


def periodic_service_registrations(
    backend: Optional[StructuredMacaulay2Backend] = None,
) -> Tuple[ServiceRegistration, ...]:
    """Return isolated registrations for the canonical periodic service."""

    actual_backend = backend or StructuredMacaulay2Backend()
    specifications = (
        (
            "periodic.presentation",
            PeriodicOperation.PRESENTATION,
            PERIODIC_PRESENTATION_INPUT_SCHEMA,
            "Decode and certify a canonical quasi-free periodic Pauli presentation.",
        ),
        (
            "periodic.charge_module",
            PeriodicOperation.EXT,
            PERIODIC_EXT_INPUT_SCHEMA,
            "Compute Ruba--Yang charge-module invariants when the coefficient domain is supported.",
        ),
        (
            "periodic.ext",
            PeriodicOperation.EXT,
            PERIODIC_EXT_INPUT_SCHEMA,
            "Compute the validated uniform-prime periodic Ext invariant.",
        ),
    )
    return tuple(
        ServiceRegistration(
            public_operation,
            _handler(actual_backend, backend_operation),
            _capability(actual_backend, backend_operation, schema),
            ServiceCatalogEntry(
                public_operation,
                summary,
                schema,
                adapter_kind="native",
                cacheable=False,
            ),
        )
        for public_operation, backend_operation, schema, summary in specifications
    )


__all__ = [
    "LAURENT_POLYNOMIAL_SCHEMA",
    "PERIODIC_EXT_INPUT_SCHEMA",
    "PERIODIC_PRESENTATION_INPUT_SCHEMA",
    "PERIODIC_PRESENTATION_SCHEMA",
    "TRANSLATION_GROUP_SCHEMA",
    "decode_periodic_presentation",
    "decode_translation_group",
    "periodic_service_registrations",
]
