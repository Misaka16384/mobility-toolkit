import json

import pytest

from mobility_toolkit.core import (
    CertificateLevel,
    Exactness,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
    canonical_json,
)
from mobility_toolkit.periodic import (
    QuasiFreePauliModulePresentation,
    StructuredMacaulay2Backend,
)
from mobility_toolkit.services.contracts import ServiceRequest
from mobility_toolkit.services.periodic_operations import (
    decode_periodic_presentation,
    decode_translation_group,
    periodic_service_registrations,
)
from mobility_toolkit.services.registry import ServiceRegistry


def _presentation(dimensions=(2,), torsion=()):
    group = TranslationGroup(
        1,
        torsion,
        free_generator_names=("x",),
    )
    species = tuple(
        LocalSystem.cyclic(f"q{index}", dimension)
        for index, dimension in enumerate(dimensions)
    )
    template = OperatorTemplate(
        0,
        tuple(
            OperatorTerm.cyclic(
                (index,),
                f"q{index}",
                x=1,
                torsion_offset=(0,) * len(torsion),
            )
            for index in range(len(dimensions))
        ),
    )
    return QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(group, species, (template,))
    )


def _transport(presentation):
    return json.loads(canonical_json(presentation))


def _request(operation, presentation, **extra):
    payload = {"presentation": _transport(presentation)}
    payload.update(extra)
    return ServiceRequest(operation, payload)


def test_canonical_presentation_and_translation_group_roundtrip():
    presentation = _presentation((2, 4), torsion=(3,))
    transport = _transport(presentation)
    decoded = decode_periodic_presentation(transport)
    assert decoded == presentation
    assert decode_translation_group(transport["translation_group"]) == (
        presentation.translation_group
    )

    registry = ServiceRegistry(
        periodic_service_registrations(StructuredMacaulay2Backend())
    )
    request = _request("periodic.presentation", presentation)
    capability = registry.capability(request)
    result = registry.dispatch(request)
    assert dict(capability.constraints)["coefficient_domain"] == "nonuniform"
    assert dict(capability.constraints)["support_tier"] == "production"
    assert result.value == presentation
    assert result.exactness is Exactness.CERTIFIED_EXACT
    assert result.certificate_level is CertificateLevel.FULL
    assert result.canonical_input_hash == request.canonical_input_hash


@pytest.mark.parametrize(
    "dimensions,expected_domain,expected_tier,expected_exactness",
    (
        ((4,), "uniform_composite", "experimental", Exactness.EXPERIMENTAL),
        ((2, 4), "nonuniform", "unsupported", Exactness.UNSUPPORTED),
    ),
)
def test_composite_and_nonuniform_ext_return_honest_structured_refusal(
    dimensions, expected_domain, expected_tier, expected_exactness
):
    calls = []

    def should_not_run(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("unsupported or experimental backend was executed")

    registry = ServiceRegistry(
        periodic_service_registrations(
            StructuredMacaulay2Backend(legacy_compute=should_not_run)
        )
    )
    request = _request("periodic.ext", _presentation(dimensions))
    capability = registry.capability(request)
    result = registry.dispatch(request)
    constraints = dict(capability.constraints)
    assert capability.supported is True
    assert constraints["coefficient_domain"] == expected_domain
    assert constraints["support_tier"] == expected_tier
    assert constraints["execution_mode"] == "structured_refusal"
    assert result.exactness is expected_exactness
    assert result.value is None
    assert result.diagnostics
    assert calls == []


@pytest.mark.parametrize("operation", ("periodic.ext", "periodic.charge_module"))
def test_uniform_prime_service_uses_ast_boundary_and_reframes_fake_m2_result(
    operation,
):
    calls = []

    def fake_compute(matrix, coefficient_modulus, **kwargs):
        calls.append((matrix, coefficient_modulus, kwargs))
        return {
            "annihilator_generators": ["1 + x1"],
            "backend_version": "fake-m2",
            "krull_dimension": 0,
        }

    registry = ServiceRegistry(
        periodic_service_registrations(
            StructuredMacaulay2Backend(legacy_compute=fake_compute)
        )
    )
    request = _request(
        operation,
        _presentation((2,)),
        charge_degree=1,
        validate_stabilizer=False,
    )
    capability = registry.capability(request)
    result = registry.dispatch(request)
    assert dict(capability.constraints)["support_tier"] == "production"
    assert result.operation == operation
    assert result.canonical_input_hash == request.canonical_input_hash
    assert result.value.charge_degree == 1
    assert result.value.ext_degree == 2
    assert result.value.krull_dimension == 0
    assert result.value.annihilator_generators[0].terms
    assert calls[0][1] == 2
    assert calls[0][2] == {
        "p_ext": 1,
        "spatial_dim": 1,
        "validate_stabilizer": False,
    }


@pytest.mark.parametrize(
    "mutate,error",
    (
        (
            lambda payload: payload.update({"prime_bypass": True}),
            "unknown input_data fields: prime_bypass",
        ),
        (
            lambda payload: payload.update({"qudit_dim": 2}),
            "unknown input_data fields: qudit_dim",
        ),
        (
            lambda payload: payload["presentation"]["stabilizer_image"]["columns"][
                0
            ]["image"]["entries"][0].__setitem__(1, "1 + x"),
            "structured Laurent-polynomial object",
        ),
        (
            lambda payload: payload["presentation"]["basis"][0].update(
                {"blocked_vector": [1, 0]}
            ),
            "unknown basis\\[0\\] fields: blocked_vector",
        ),
        (
            lambda payload: payload["presentation"]["stabilizer_image"]["columns"][
                0
            ]["image"]["entries"][0][1]["terms"][0].update({"expression": "x"}),
            "unknown .* fields: expression",
        ),
    ),
)
def test_periodic_schema_recursively_rejects_legacy_strings_and_switches(
    mutate, error
):
    request = _request("periodic.ext", _presentation((2,)))
    mutate(request.input_data)
    registration = periodic_service_registrations()[2]
    with pytest.raises((TypeError, ValueError), match=error):
        registration.handler(request)


def test_repeated_polynomial_ring_declarations_must_match_the_presentation():
    payload = _transport(_presentation((2,)))
    polynomial = payload["stabilizer_image"]["columns"][0]["image"]["entries"][0][1]
    polynomial["translation_group"]["free_generator_names"] = ["not-x"]
    with pytest.raises(ValueError, match="translation_group differs"):
        decode_periodic_presentation(payload)
