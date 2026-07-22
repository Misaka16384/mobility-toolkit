import itertools

import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import (
    FiniteAbelianGroup,
    FlintIntegerBackend,
    HowellFormResult,
    crt_recombine,
    howell_form,
    primary_decomposition,
    prime_power_factors,
    verify_howell_form,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _row_span_mod(matrix, modulus):
    rows = matrix.to_rows()
    return {
        tuple(
            sum(coefficients[row] * rows[row][column] for row in range(matrix.nrows))
            % modulus
            for column in range(matrix.ncols)
        )
        for coefficients in itertools.product(range(modulus), repeat=matrix.nrows)
    }


@pytest.mark.parametrize(
    "matrix,modulus",
    (
        (SparseIntMatrix.from_rows(((2, 0),)), 4),
        (SparseIntMatrix.from_rows(((2, 1),)), 4),
        (SparseIntMatrix.from_rows(((2, 3), (4, 0))), 6),
        (SparseIntMatrix.from_rows(((4, 2, 0), (0, 3, 3))), 12),
    ),
)
def test_howell_form_preserves_modular_row_span(backend, matrix, modulus):
    result = howell_form(matrix, modulus, backend)
    assert _row_span_mod(result.form, modulus) == _row_span_mod(matrix, modulus)
    verify_howell_form(matrix, result)
    assert all(0 <= value < modulus for _, _, value in result.form.entries)


def test_howell_form_contains_torsion_consequence(backend):
    result = howell_form(SparseIntMatrix.from_rows(((2, 1),)), 4, backend)
    assert result.form.to_rows() == ((2, 1), (0, 2))


def test_howell_form_is_invariant_under_row_reordering_and_redundancy(backend):
    first = howell_form(SparseIntMatrix.from_rows(((2, 1), (0, 2))), 4, backend)
    second = howell_form(
        SparseIntMatrix.from_rows(((0, 2), (2, 1), (2, 3))), 4, backend
    )
    assert first.form == second.form
    assert first.lifted_preimage_basis == second.lifted_preimage_basis


def test_corrupted_howell_certificate_is_rejected(backend):
    matrix = SparseIntMatrix.from_rows(((2, 1),))
    result = howell_form(matrix, 4, backend)
    corrupted = HowellFormResult(
        result.modulus,
        SparseIntMatrix.from_rows(((1, 0),)),
        result.lifted_preimage_basis,
        result.preimage_certificate,
    )
    with pytest.raises(ArithmeticError, match="Howell rows"):
        verify_howell_form(matrix, corrupted)


def test_crt_recombination_and_validation():
    assert prime_power_factors(360) == ((2, 3, 8), (3, 2, 9), (5, 1, 5))
    value = crt_recombine((3, 4, 2), (8, 9, 5))
    assert tuple(value % modulus for modulus in (8, 9, 5)) == (3, 4, 2)
    with pytest.raises(ValueError, match="coprime"):
        crt_recombine((1, 2), (4, 6))


def test_primary_decomposition_of_mixed_composite_group(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((12, 18), backend)
    decomposition = primary_decomposition(group, backend)
    assert group.invariant_factors == (6, 36)
    assert decomposition.exponent == 36
    by_prime = {component.prime: component for component in decomposition.components}
    assert by_prime[2].projector == 9
    assert by_prime[2].invariant_factors == (2, 4)
    assert by_prime[2].subgroup.order(backend) == 8
    assert by_prime[3].projector == 28
    assert by_prime[3].invariant_factors == (3, 9)
    assert by_prime[3].subgroup.order(backend) == 27


def test_primary_decomposition_matches_explicit_projector_images(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((6, 6), backend)
    decomposition = primary_decomposition(group, backend)
    for component in decomposition.components:
        explicit = {
            (
                component.projector * x % 6,
                component.projector * y % 6,
            )
            for x, y in itertools.product(range(6), repeat=2)
        }
        observed = {
            (x, y)
            for x, y in itertools.product(range(6), repeat=2)
            if component.subgroup.contains((x, y), backend)
        }
        assert observed == explicit
