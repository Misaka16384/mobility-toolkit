"""Published secondary-operator oracle from Ruba--Yang Example 45."""

from mobility_toolkit.boundary_halfspace.secondary_example import (
    ruba_yang_secondary_boundary_example,
    verify_secondary_example_finite,
)
from mobility_toolkit.core import Exactness


def test_published_example45_has_a_genuine_secondary_generator():
    result = ruba_yang_secondary_boundary_example()
    value = result.value
    assert result.exactness is Exactness.CERTIFIED_EXACT
    assert value.certificate.verified
    assert value.primary_generators[0] != value.secondary_generator
    assert value.full_generators[0] == value.secondary_generator
    assert value.secondary_quotient_annihilator.terms
    assert value.certificate.secondary_relation_verified
    verification = dict(result.verification)
    assert verification["secondary_relation"] == "(1+x)e1_prime=e1"
    assert verification["primary_boundary_charge_module"] == "(A/(1+x))^2"
    assert verification["full_boundary_charge_module"] == "0"


def test_example45_pairing_changes_from_nonunimodular_to_symplectic():
    value = ruba_yang_secondary_boundary_example().value
    primary_entry = value.primary_pairing[0][1]
    full_entry = value.full_pairing[0][1]
    assert {(term.exponents, term.coefficient) for term in primary_entry.terms} == {
        ((-1,), 1),
        ((0,), 1),
    }
    assert {(term.exponents, term.coefficient) for term in full_entry.terms} == {
        ((0,), 1),
    }
    assert value.primary_boundary_charge_multiplicity == 2
    assert value.full_boundary_charge_invariant_factors == ()


def test_example45_literal_source_equations_are_frozen():
    certificate = ruba_yang_secondary_boundary_example().value.certificate
    assert certificate.source_arxiv == "2509.10418"
    assert certificate.source_example == "Example 45"
    assert certificate.source_equations == (114, 115, 116, 117, 118)
    assert certificate.literal_bulk_generator == (
        "(1+x^-1)n^-1 + (1+x)n",
        "1",
    )


def test_finite_period_shadows_detect_the_missing_secondary():
    for period in range(2, 10):
        check = verify_secondary_example_finite(period)
        assert check.verified
        assert check.primary_embedding_rank == 2 * period - 1
        assert check.secondary_quotient_dimension == 1
        assert check.primary_radical_dimension == 2
        assert check.full_radical_dimension == 0
