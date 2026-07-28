"""Exact free boundary-pairing invariants and published physics oracles."""

import pytest

from mobility_toolkit.boundary_halfspace.boundary_module import (
    toric_z2_y_nonnegative_boundary_module,
)
from mobility_toolkit.boundary_halfspace.quasi_symplectic import (
    FreeBoundaryPairingPresentation,
    analyze_free_boundary_pairing,
)
from mobility_toolkit.boundary_halfspace.secondary_example import (
    ruba_yang_secondary_boundary_example,
)
from mobility_toolkit.core import Exactness
from mobility_toolkit.engine import describe_m2_backend


M2_AVAILABLE = bool(describe_m2_backend()["available"])


def _presentation(pairing, labels, scope):
    entry = pairing[0][0]
    return FreeBoundaryPairingPresentation(
        coefficient_modulus=entry.coefficient_modulus,
        tangent_rank=entry.tangent_rank,
        pairing_matrix=pairing,
        generator_labels=labels,
        source_scope=scope,
    )


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_toric_free_boundary_pairing_has_two_charge_classes():
    boundary = toric_z2_y_nonnegative_boundary_module().value
    presentation = _presentation(
        boundary.quasi_symplectic_pairing,
        ("e_X", "e_Z"),
        "standard Z2 toric y>=0 full analytic boundary module",
    )
    result = analyze_free_boundary_pairing(presentation)
    invariants = result.value
    assert result.exactness is Exactness.CERTIFIED_EXACT
    assert invariants.certificate.verified
    assert invariants.radical_zero
    assert not invariants.boundary_charge_zero
    assert not invariants.pairing_unimodular
    assert invariants.boundary_charge_krull_dimension == 0
    assert len(invariants.boundary_charge_annihilator) == 1
    assert {
        term.exponents
        for term in invariants.boundary_charge_annihilator[0].terms
    } == {(0,), (1,)}


@pytest.mark.skipif(not M2_AVAILABLE, reason="Macaulay2 backend not available")
def test_example45_primary_and_full_pairings_have_different_charge_modules():
    example = ruba_yang_secondary_boundary_example().value
    primary = analyze_free_boundary_pairing(
        _presentation(
            example.primary_pairing,
            ("e1", "e2"),
            "Ruba--Yang Example 45 primary module",
        )
    ).value
    full = analyze_free_boundary_pairing(
        _presentation(
            example.full_pairing,
            ("e1_prime", "e2"),
            "Ruba--Yang Example 45 full module",
        )
    ).value
    assert primary.radical_zero
    assert not primary.boundary_charge_zero
    assert primary.boundary_charge_krull_dimension == 0
    assert full.radical_zero
    assert full.boundary_charge_zero
    assert full.boundary_charge_krull_dimension == -1
    assert full.pairing_unimodular


def test_non_antihermitian_pairing_is_rejected_before_backend():
    example = ruba_yang_secondary_boundary_example().value
    bad = (
        example.full_pairing[0],
        (
            example.full_pairing[1][0],
            example.full_pairing[0][1],
        ),
    )
    with pytest.raises(ValueError, match="not alternating"):
        _presentation(bad, ("a", "b"), "malformed test")


def test_composite_coefficients_are_explicitly_unsupported():
    example = ruba_yang_secondary_boundary_example().value
    zero = example.full_pairing[0][0]
    from mobility_toolkit.boundary_halfspace.boundary_module import (
        TangentLaurentPolynomial,
        TangentLaurentTerm,
    )

    one4 = TangentLaurentPolynomial(
        4,
        zero.tangent_rank,
        (TangentLaurentTerm(1, (0,)),),
    )
    minus_one4 = TangentLaurentPolynomial(
        4,
        zero.tangent_rank,
        (TangentLaurentTerm(3, (0,)),),
    )
    zero4 = TangentLaurentPolynomial(4, zero.tangent_rank, ())
    presentation = FreeBoundaryPairingPresentation(
        4,
        1,
        ((zero4, one4), (minus_one4, zero4)),
    )
    with pytest.raises(NotImplementedError, match="uniform prime"):
        analyze_free_boundary_pairing(presentation)


def test_mocked_backend_output_is_fully_parsed_and_bound_to_presentation():
    example = ruba_yang_secondary_boundary_example().value
    presentation = _presentation(
        example.primary_pairing,
        ("e1", "e2"),
        "mock parser contract",
    )

    def execute(script, timeout):
        assert "E = coker Omega" in script
        assert "Rad = trim kernel Omega" in script
        assert timeout == 7.0
        return {
            "exit_code": 0,
            "stdout": "\n".join(
                (
                    "MT_QS:RADICAL_GENERATORS:0",
                    "MT_QS:CHARGE_DIM:0",
                    "MT_QS:ANN_COLS:1",
                    "MT_QS:ANN_ENTRY:0:x1 + 1",
                    "MT_QS:BACKEND_COMPLETE:true",
                )
            ),
            "stderr": "",
        }

    result = analyze_free_boundary_pairing(
        presentation,
        timeout_seconds=7,
        execute=execute,
    )
    assert result.value.certificate.presentation_hash
    assert result.value.boundary_charge_krull_dimension == 0
    assert result.value.radical_zero
