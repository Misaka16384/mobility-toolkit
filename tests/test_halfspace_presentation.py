import pytest

from mobility_toolkit.boundary_halfspace import (
    PrimitiveNormal,
    UnimodularBasisChange,
    adapt_laurent_polynomial,
    clear_negative_depth,
)
from mobility_toolkit.core import LaurentPolynomial, LaurentTerm, TranslationGroup
from mobility_toolkit.core.canonical import canonical_hash


def _polynomial(group, terms, modulus=5):
    return LaurentPolynomial(modulus, group, tuple(LaurentTerm(*term) for term in terms))


def test_axial_basis_splits_tangent_and_depth_exactly():
    group = TranslationGroup(3)
    polynomial = _polynomial(
        group,
        (
            (1, (2, -3, 4), ()),
            (2, (-1, 5, -2), ()),
        ),
    )
    normal = PrimitiveNormal.from_integer((0, 0, 1))
    basis = UnimodularBasisChange.adapted_to(normal)
    adapted = adapt_laurent_polynomial(polynomial, basis)
    assert sorted(term.depth for term in adapted.terms) == [-2, 4]
    reconstructed = {
        basis.from_boundary_coordinates(term.tangent_exponents + (term.depth,))
        for term in adapted.terms
    }
    assert reconstructed == {(2, -3, 4), (-1, 5, -2)}


def test_generic_normal_depth_is_the_normal_dot_product_and_round_trips():
    normal = PrimitiveNormal.from_integer((1, 1, 1))
    basis = UnimodularBasisChange.adapted_to(normal)
    group = TranslationGroup(3)
    exponents = ((2, -5, 7), (-4, 3, 9), (0, 0, 0))
    polynomial = _polynomial(
        group,
        tuple((index + 1, exponent, ()) for index, exponent in enumerate(exponents)),
        modulus=7,
    )
    adapted = adapt_laurent_polynomial(polynomial, basis)
    for source, term in zip(sorted(exponents), adapted.terms):
        # Canonical term ordering need not preserve input ordering; reconstruct
        # every source exponent from its adapted coordinate instead.
        ambient = basis.from_boundary_coordinates(
            term.tangent_exponents + (term.depth,)
        )
        assert ambient in exponents
        assert term.depth == normal.dot(ambient)
    assert {basis.from_boundary_coordinates(t.tangent_exponents + (t.depth,)) for t in adapted.terms} == set(exponents)


def test_depth_clearing_is_minimal_and_does_not_claim_module_saturation():
    group = TranslationGroup(2)
    polynomial = _polynomial(
        group,
        ((1, (-3, 2), ()), (4, (1, -1), ())),
    )
    adapted = adapt_laurent_polynomial(polynomial, (0, 1))
    clearing = clear_negative_depth(adapted)
    assert adapted.depth_interval == (-1, 2)
    assert clearing.depth_shift == 1
    assert clearing.cleared.depth_interval == (0, 3)
    assert "saturation" in clear_negative_depth.__doc__


def test_involution_negates_tangent_depth_and_torsion_coordinates():
    group = TranslationGroup(2, (4,))
    polynomial = _polynomial(
        group,
        ((3, (2, -5), (1,)),),
        modulus=6,
    )
    adapted = adapt_laurent_polynomial(polynomial, (1, 1))
    term = adapted.terms[0]
    inverse = adapted.involution().terms[0]
    assert inverse.tangent_exponents == tuple(-value for value in term.tangent_exponents)
    assert inverse.depth == -term.depth
    assert inverse.torsion_exponents == (3,)


def test_canonicalization_combines_duplicate_adapted_terms():
    group = TranslationGroup(2)
    first = _polynomial(group, ((1, (1, 2), ()), (2, (1, 2), ())))
    second = _polynomial(group, ((3, (1, 2), ()),))
    assert canonical_hash("adapted", adapt_laurent_polynomial(first, (2, 1))) == canonical_hash(
        "adapted", adapt_laurent_polynomial(second, (2, 1))
    )


def test_rank_mismatch_is_rejected():
    polynomial = _polynomial(TranslationGroup(2), ((1, (0, 0), ()),))
    with pytest.raises(ValueError, match="free rank"):
        adapt_laurent_polynomial(polynomial, (1, 0, 0))
