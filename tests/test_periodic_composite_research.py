import pytest

from mobility_toolkit.core import (
    Exactness,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
    canonical_hash,
)
from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit.periodic import (
    CoefficientDomain,
    PeriodicBackendRequest,
    PeriodicOperation,
    PeriodicSupportMatrix,
    QuasiFreePauliModulePresentation,
    StructuredMacaulay2Backend,
    SupportTier,
    finite_resolution_check,
    ruba_yang_z4_resolution,
    run_nonuniform_quasi_free_toy_benchmark,
    run_ruba_yang_z4_resolution_benchmark,
)


def _presentation(dimensions):
    group = TranslationGroup(2)
    species = tuple(
        LocalSystem.cyclic(f"q{index}", dimension)
        for index, dimension in enumerate(dimensions)
    )
    template = OperatorTemplate(
        0,
        tuple(
            OperatorTerm.cyclic((index, 0), f"q{index}", x=1)
            for index in range(len(dimensions))
        ),
    )
    return QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(group, species, (template,))
    )


def test_paper_resolution_is_canonical_and_squares_to_zero_without_m2():
    first = ruba_yang_z4_resolution()
    second = ruba_yang_z4_resolution()
    assert dict(first.chain_identities()) == {
        "sigma_tau": True,
        "tau_tau": True,
        "tau_dagger_epsilon": True,
        "tau_dagger_squared": True,
    }
    assert canonical_hash(first.SCHEMA_ID, first) == canonical_hash(second.SCHEMA_ID, second)


@pytest.mark.parametrize("periods", ((1, 1), (2, 1), (2, 2)))
def test_independent_finite_fga_specializations_reproduce_z2_plus_z2(periods):
    check = finite_resolution_check(ruba_yang_z4_resolution(), periods)
    assert check.chain_squared_zero
    assert check.h1_invariant_factors == (2, 2)


def test_fixed_research_operations_do_not_promote_generic_ext():
    matrix = PeriodicSupportMatrix()
    composite = _presentation((4, 4))
    paper = matrix.decide(PeriodicOperation.PAPER_RESOLUTION_BENCHMARK, composite)
    generic = matrix.decide(PeriodicOperation.EXT, composite)
    nonuniform = _presentation((2, 4))
    toy = matrix.decide(
        PeriodicOperation.NONUNIFORM_QUASI_FREE_BENCHMARK,
        nonuniform,
    )
    generic_nonuniform = matrix.decide(PeriodicOperation.EXT, nonuniform)
    assert (paper.coefficient_domain, paper.tier) == (
        CoefficientDomain.UNIFORM_COMPOSITE,
        SupportTier.EXPERIMENTAL,
    )
    assert generic.tier is SupportTier.EXPERIMENTAL
    assert toy.tier is SupportTier.EXPERIMENTAL
    assert generic_nonuniform.tier is SupportTier.UNSUPPORTED


def test_generic_composite_adapter_still_refuses_execution():
    called = []

    def should_not_run(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("generic composite Ext must remain non-executable")

    response = StructuredMacaulay2Backend(legacy_compute=should_not_run).execute(
        PeriodicBackendRequest(PeriodicOperation.EXT, _presentation((4, 4)))
    )
    assert response.computation.exactness is Exactness.EXPERIMENTAL
    assert response.computation.value is None
    assert called == []


@pytest.mark.skipif(
    not describe_m2_backend()["available"],
    reason="Macaulay2 backend not available",
)
def test_live_m2_paper_resolution_reproduces_charge_group_and_higher_vanishing():
    result = run_ruba_yang_z4_resolution_benchmark()
    assert result.exactness is Exactness.EXPERIMENTAL
    assert result.value.additive_invariant_factors == (2, 2)
    assert result.value.explicit_generators_are_cycles
    assert result.value.explicit_nonzero_classes == ("e", "m", "e+m")
    assert result.value.explicit_generators_span_h1
    assert result.value.higher_charge_degrees_tested_zero == (1,)
    assert result.value.all_higher_zero_conditional_on_paper_resolution
    assert isinstance(result.value.native_composite_polynomial_ring_supported, bool)
    assert result.value.integer_quotient_ring_workaround
    assert not result.value.generic_composite_ext_promoted
    assert all(
        check.h1_invariant_factors == (2, 2)
        for check in result.value.finite_specializations
    )


@pytest.mark.skipif(
    not describe_m2_backend()["available"],
    reason="Macaulay2 backend not available",
)
def test_live_nonuniform_quasi_free_toy_is_verified_but_generic_path_blocked():
    result = run_nonuniform_quasi_free_toy_benchmark()
    assert result.exactness is Exactness.EXPERIMENTAL
    assert result.value.local_orders == (2, 4)
    assert result.value.ext_degrees_tested_zero == (1, 2)
    assert not result.value.generic_nonuniform_ext_supported
    assert "No validated algorithm" in result.value.blocker
    assert result.certificate["finite_fga_h1_invariants"] == ()
