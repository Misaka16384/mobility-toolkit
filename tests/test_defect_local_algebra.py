import pytest

from mobility_toolkit.core import LocalPauliTerm, PauliModule
from mobility_toolkit.defects import defect_local_algebra
from mobility_toolkit.finite import FlintIntegerBackend, analyze_finite_stabilizer


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def test_windowed_centralizer_quotient_retains_only_supported_logical_pair(backend):
    module = PauliModule.from_dimensions((2, 2), ("left", "right"))
    analysis = analyze_finite_stabilizer(module, (), backend)
    local = defect_local_algebra(analysis, ("left",), backend)
    assert local.invariant_factors == (2, 2)
    assert local.order == 4
    assert local.radical_invariant_factors == ()


def test_windowed_stabilizer_is_quotiented_with_pairing_descent(backend):
    module = PauliModule.from_dimensions((2, 2), ("left", "right"))
    zz = module.operator(
        (
            LocalPauliTerm.cyclic("left", z=1),
            LocalPauliTerm.cyclic("right", z=1),
        )
    )
    analysis = analyze_finite_stabilizer(module, (zz,), backend)
    left = defect_local_algebra(analysis, ("left",), backend)
    both = defect_local_algebra(analysis, ("left", "right"), backend)
    assert left.invariant_factors == (2,)
    assert left.order == 2
    assert left.radical_invariant_factors == (2,)
    assert both.invariant_factors == (2, 2)


def test_window_rejects_unknown_sites(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    with pytest.raises(ValueError, match="unknown defect-window"):
        defect_local_algebra(analysis, ("missing",), backend)


def test_empty_window_has_trivial_local_algebra(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    analysis = analyze_finite_stabilizer(module, (), backend)
    local = defect_local_algebra(analysis, (), backend)
    assert local.invariant_factors == ()
    assert local.radical_invariant_factors == ()


def test_stabilizer_intersection_finds_products_not_present_as_input_generators(backend):
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    xaxb = module.operator(
        (
            LocalPauliTerm.cyclic("a", x=1),
            LocalPauliTerm.cyclic("b", x=1),
        )
    )
    xb = module.operator((LocalPauliTerm.cyclic("b", x=1),))
    analysis = analyze_finite_stabilizer(module, (xaxb, xb), backend)
    local = defect_local_algebra(analysis, ("a",), backend)
    assert local.local_stabilizer.order(backend) == 2
    assert local.invariant_factors == ()
