import inspect

import pytest

from mobility_toolkit.core import (
    Exactness,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
    canonical_json,
)
from mobility_toolkit.periodic import (
    CoefficientDomain,
    PeriodicBackendRequest,
    PeriodicOperation,
    PeriodicSupportMatrix,
    QuasiFreePauliModulePresentation,
    StructuredMacaulay2Backend,
    SupportTier,
    probe_macaulay2,
)
from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit.translate import translate_stabilizers


def _presentation(dimensions, torsion=()):
    group = TranslationGroup(1, torsion)
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


def test_operation_specific_uniform_prime_composite_and_nonuniform_support():
    matrix = PeriodicSupportMatrix()
    prime = matrix.decide(PeriodicOperation.EXT, _presentation((2, 2)))
    composite = matrix.decide(PeriodicOperation.EXT, _presentation((4, 4)))
    nonuniform = matrix.decide(PeriodicOperation.EXT, _presentation((2, 4)))
    assert (prime.coefficient_domain, prime.tier, prime.exactness) == (
        CoefficientDomain.UNIFORM_PRIME,
        SupportTier.PRODUCTION,
        Exactness.CERTIFIED_EXACT,
    )
    assert composite.tier is SupportTier.EXPERIMENTAL
    assert composite.exactness is Exactness.EXPERIMENTAL
    assert nonuniform.tier is SupportTier.UNSUPPORTED
    assert nonuniform.exactness is Exactness.UNSUPPORTED


def test_saturation_has_a_separate_promotion_gate():
    decision = PeriodicSupportMatrix().decide(
        PeriodicOperation.SATURATION, _presentation((3,))
    )
    assert decision.tier is SupportTier.EXPERIMENTAL
    assert "production benchmark gate" in decision.reason


def test_torsion_translation_is_structurally_unsupported_by_m2_adapter():
    decision = PeriodicSupportMatrix().decide(
        PeriodicOperation.KRULL_DIMENSION,
        _presentation((2,), torsion=(3,)),
    )
    assert decision.tier is SupportTier.UNSUPPORTED
    assert "free translations only" in decision.reason


def test_new_backend_request_has_no_prime_bypass_semantics():
    assert "prime_bypass" not in inspect.signature(PeriodicBackendRequest).parameters


def test_presentation_operation_returns_the_canonical_ir_without_m2():
    presentation = _presentation((2, 4))
    request = PeriodicBackendRequest(PeriodicOperation.PRESENTATION, presentation)
    response = StructuredMacaulay2Backend().execute(request)
    assert response.computation.exactness is Exactness.CERTIFIED_EXACT
    assert response.computation.value == presentation
    assert response.computation.certificate["basis_relations_complete"] is True


def test_nonuniform_request_returns_structured_unsupported_without_execution():
    called = []

    def should_not_run(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("unsupported backend was executed")

    request = PeriodicBackendRequest(
        PeriodicOperation.EXT,
        _presentation((2, 4)),
    )
    response = StructuredMacaulay2Backend(legacy_compute=should_not_run).execute(request)
    assert response.computation.exactness is Exactness.UNSUPPORTED
    assert response.computation.value is None
    assert called == []
    assert "unsupported" in canonical_json(response)


def test_uniform_prime_adapter_renders_ast_and_parses_annihilator_to_ast():
    calls = []

    def fake_compute(matrix, qudit_dim, **kwargs):
        calls.append((matrix, qudit_dim, kwargs))
        return {
            "krull_dimension": 0,
            "annihilator_generators": ["1 + x1", "t1 + x1^2"],
            "backend_version": "test-double",
        }

    request = PeriodicBackendRequest(
        PeriodicOperation.KRULL_DIMENSION,
        _presentation((2,)),
    )
    response = StructuredMacaulay2Backend(legacy_compute=fake_compute).execute(request)
    assert response.computation.exactness is Exactness.CERTIFIED_EXACT
    assert response.computation.value.krull_dimension == 0
    assert len(response.computation.value.annihilator_generators) == 2
    assert calls[0][1] == 2
    assert "prime_bypass" not in calls[0][2]
    assert calls[0][2]["spatial_dim"] == 1


def test_annihilator_generator_order_is_canonicalized_at_adapter_boundary():
    def fake_compute(*args, **kwargs):
        return {
            "krull_dimension": 0,
            "annihilator_generators": ["x1", "1 + x1", "x1"],
        }

    request = PeriodicBackendRequest(PeriodicOperation.ANNIHILATOR, _presentation((2,)))
    value = StructuredMacaulay2Backend(legacy_compute=fake_compute).execute(
        request
    ).computation.value
    assert len(value.annihilator_generators) == 2
    assert tuple(canonical_json(item) for item in value.annihilator_generators) == tuple(
        sorted(canonical_json(item) for item in value.annihilator_generators)
    )


def test_unified_renderer_is_accepted_by_real_legacy_translator_boundary():
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(
            TranslationGroup(1),
            (LocalSystem.cyclic("q", 2),),
            (
                OperatorTemplate(
                    0,
                    (OperatorTerm.cyclic((1,), "q", x=1),),
                ),
            ),
        )
    )
    rows = [list(row) for row in presentation.to_legacy_generator_rows()]
    translated = translate_stabilizers(
        rows,
        2,
        spatial_dim=1,
        validate_stabilizer=True,
    )
    assert translated["variable_pairs"] == [["x1", "t1"]]
    assert "x1" in translated["matrix_definition"]


@pytest.mark.skipif(
    not describe_m2_backend()["available"],
    reason="Macaulay2 backend not available",
)
def test_uniform_prime_structured_adapter_reaches_real_m2_backend():
    request = PeriodicBackendRequest(
        PeriodicOperation.KRULL_DIMENSION,
        _presentation((2,)),
    )
    response = StructuredMacaulay2Backend().execute(request)
    assert response.computation.exactness is Exactness.CERTIFIED_EXACT
    assert response.computation.value.ext_degree == 1


def test_probe_is_structured_even_when_version_execution_is_skipped():
    probe = probe_macaulay2(execute_version=False)
    assert probe.version_checked is False
    assert dict(probe.operations)["uniform_prime.ext"] == "production"
    assert dict(probe.operations)["nonuniform.ext"] == "unsupported"


def test_ruba_yang_z4_fixture_does_not_promote_composite_ext():
    presentation = _presentation((4, 4))
    response = StructuredMacaulay2Backend(
        legacy_compute=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("experimental composite Ext must not execute")
        )
    ).execute(PeriodicBackendRequest(PeriodicOperation.EXT, presentation))
    assert response.capability.tier is SupportTier.EXPERIMENTAL
    assert response.computation.exactness is Exactness.EXPERIMENTAL
    assert response.computation.value is None
