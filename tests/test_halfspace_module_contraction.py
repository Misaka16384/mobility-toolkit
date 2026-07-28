"""Exact oracles for one-sided Laurent submodule contraction."""

import pytest

from mobility_toolkit.boundary_halfspace import (
    LaurentHalfSpaceSubmodule,
    PrimitiveNormal,
    TangentDepthPolynomial,
    TangentDepthTerm,
    clear_submodule_columns,
    contract_laurent_submodule,
)
from mobility_toolkit.engine import describe_m2_backend


M2_AVAILABLE = bool(describe_m2_backend()["available"])


def _poly(normal, terms, modulus=2):
    return TangentDepthPolynomial(
        modulus,
        normal,
        (),
        tuple(
            TangentDepthTerm(coefficient, tangent, depth, ())
            for coefficient, tangent, depth in terms
        ),
    )


def _zero(normal, modulus=2):
    return _poly(normal, (), modulus)


def _scalar_terms(result):
    assert result.value.ambient_rank == 1
    return {
        (
            tuple(
                (term.tangent_exponents, term.depth, term.coefficient)
                for term in column[0].terms
            )
        )
        for column in result.value.generator_columns
    }


def test_column_clearing_is_explicitly_not_saturation():
    normal = PrimitiveNormal.from_integer((1,))
    n = _poly(normal, ((1, (), 1),))
    module = LaurentHalfSpaceSubmodule(2, normal, 1, ((n,),))
    columns, shifts = clear_submodule_columns(module)
    assert shifts == (0,)
    assert columns == ((n,),)
    assert "not" in clear_submodule_columns.__doc__


def test_uniform_prime_and_free_tangent_scope_is_enforced():
    normal = PrimitiveNormal.from_integer((0, 1))
    with pytest.raises(ValueError, match="prime"):
        LaurentHalfSpaceSubmodule(
            4,
            normal,
            1,
            ((_poly(normal, ((1, (0,), 0),), modulus=4),),),
        )
    torsion = TangentDepthPolynomial(
        2,
        normal,
        (2,),
        (TangentDepthTerm(1, (0,), 0, (0,)),),
    )
    with pytest.raises(ValueError, match="free tangent"):
        LaurentHalfSpaceSubmodule(2, normal, 1, ((torsion,),))


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_zero_laurent_submodule_contracts_to_zero():
    normal = PrimitiveNormal.from_integer((1,))
    result = contract_laurent_submodule(
        LaurentHalfSpaceSubmodule(3, normal, 2, ())
    )
    assert result.value.generator_columns == ()
    assert result.value.certificate.saturation_generator_count == 0
    assert result.value.certificate.verified


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_1d_oracle_saturation_of_n_is_the_unit_module():
    """In F2[n,n^-1], (n) is all of R, so (n) cap F2[n] = F2[n]."""

    normal = PrimitiveNormal.from_integer((1,))
    module = LaurentHalfSpaceSubmodule(
        2,
        normal,
        1,
        ((_poly(normal, ((1, (), 1),)),),),
    )
    result = contract_laurent_submodule(module)
    assert result.value.certificate.verified
    assert result.value.certificate.column_depth_shifts == (0,)
    assert _scalar_terms(result) == {(((), 0, 1),)}
    assert result.verification == (
        ("clearing_is_saturation", False),
        ("localization_equal", True),
        ("saturation_idempotent", True),
    )


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_2d_oracle_removes_only_the_normal_factor():
    """(n(1+x))R cap F2[x^+-1,n] = (1+x)S."""

    normal = PrimitiveNormal.from_integer((0, 1))
    generator = _poly(
        normal,
        (
            (1, (0,), 1),
            (1, (1,), 1),
        ),
    )
    result = contract_laurent_submodule(
        LaurentHalfSpaceSubmodule(2, normal, 1, ((generator,),))
    )
    assert _scalar_terms(result) == {
        (
            ((0,), 0, 1),
            ((1,), 0, 1),
        )
    }
    assert result.value.certificate.localization_equal


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_negative_depth_clearing_preserves_laurent_localization():
    normal = PrimitiveNormal.from_integer((1,))
    generator = _poly(
        normal,
        (
            (1, (), -1),
            (1, (), 0),
        ),
    )
    result = contract_laurent_submodule(
        LaurentHalfSpaceSubmodule(2, normal, 1, ((generator,),))
    )
    assert result.value.certificate.column_depth_shifts == (1,)
    assert result.value.certificate.localization_equal
    assert _scalar_terms(result) == {
        (
            ((), 0, 1),
            ((), 1, 1),
        )
    }


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_toric_code_cut_stabilizers_give_expected_one_sided_generators():
    """Standard Z2 toric-code star/plaquette columns for the y >= 0 cut.

    Coordinates are ``(X_h, X_v, Z_h, Z_v)``.  The star column is
    ``(1+x^-1, 1+y^-1, 0, 0)`` and the plaquette column is
    ``(0, 0, 1+y, 1+x)``.  Clearing the star by ``y`` produces the known
    truncated one-sided generators.  Neither column has a common normal
    factor, so saturation adds no generator.
    """

    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _zero(normal)
    one_plus_x_inverse = _poly(
        normal,
        ((1, (0,), 0), (1, (-1,), 0)),
    )
    one_plus_y_inverse = _poly(
        normal,
        ((1, (0,), 0), (1, (0,), -1)),
    )
    one_plus_y = _poly(
        normal,
        ((1, (0,), 0), (1, (0,), 1)),
    )
    one_plus_x = _poly(
        normal,
        ((1, (0,), 0), (1, (1,), 0)),
    )
    star = (one_plus_x_inverse, one_plus_y_inverse, zero, zero)
    plaquette = (zero, zero, one_plus_y, one_plus_x)
    result = contract_laurent_submodule(
        LaurentHalfSpaceSubmodule(2, normal, 4, (star, plaquette))
    )
    assert result.value.certificate.column_depth_shifts == (1, 0)
    assert result.value.certificate.saturation_generator_count == 2
    supports = {
        tuple(
            tuple(
                (term.tangent_exponents, term.depth)
                for term in entry.terms
            )
            for entry in column
        )
        for column in result.value.generator_columns
    }
    expected_star = (
        (((-1,), 1), ((0,), 1)),
        (((0,), 0), ((0,), 1)),
        (),
        (),
    )
    expected_plaquette = (
        (),
        (),
        (((0,), 0), ((0,), 1)),
        (((0,), 0), ((1,), 0)),
    )
    assert supports == {expected_star, expected_plaquette}
    assert "P_boundary" in result.warnings[1]
