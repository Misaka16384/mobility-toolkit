import pytest

from mobility_toolkit.core import canonical_hash
from mobility_toolkit.periodic import (
    GroupRingMonomial,
    LaurentPolynomial,
    TranslationGroup,
    parse_legacy_laurent,
    polynomial_from_terms,
    render_m2_laurent,
)


def test_group_ring_monomial_normalizes_torsion_and_has_inverse():
    group = TranslationGroup(2, (4,), ("x", "y"))
    monomial = GroupRingMonomial(group, (3, -2), (5,))
    assert monomial.torsion_exponents == (1,)
    assert monomial * monomial.inverse() == GroupRingMonomial.identity(group)


def test_laurent_ast_canonicalization_is_not_text_dependent():
    group = TranslationGroup(2, free_generator_names=("x", "y"))
    x = GroupRingMonomial(group, (1, 0))
    y_inverse = GroupRingMonomial(group, (0, -1))
    first = polynomial_from_terms(5, group, ((1, x), (2, y_inverse), (5, x)))
    second = polynomial_from_terms(5, group, ((2, y_inverse), (1, x)))
    assert first == second
    assert canonical_hash(LaurentPolynomial.SCHEMA_ID, first) == canonical_hash(
        LaurentPolynomial.SCHEMA_ID, second
    )


def test_legacy_text_is_only_a_round_trip_backend_adapter():
    group = TranslationGroup(3)
    polynomial = parse_legacy_laurent("x1 + 2*t2*x3^2", 5, group)
    rendered = render_m2_laurent(polynomial)
    assert parse_legacy_laurent(rendered, 5, group) == polynomial
    assert all(not isinstance(term, str) for term in polynomial.terms)


def test_torsion_translation_is_rejected_by_legacy_m2_renderer():
    group = TranslationGroup(1, (3,))
    polynomial = GroupRingMonomial(group, (1,), (1,)).as_polynomial(2)
    with pytest.raises(ValueError, match="torsion translations"):
        render_m2_laurent(polynomial)


def test_polynomial_builder_rejects_monomials_from_another_group():
    group = TranslationGroup(1, free_generator_names=("x",))
    renamed_group = TranslationGroup(1, free_generator_names=("u",))
    with pytest.raises(ValueError, match="different translation group"):
        polynomial_from_terms(
            3,
            group,
            ((1, GroupRingMonomial(renamed_group, (1,))),),
        )
