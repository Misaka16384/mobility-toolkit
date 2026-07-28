import numpy as np
import pytest

from mobility_toolkit.core import (
    LocalPauliTerm,
    LocalSystem,
    PauliModule,
    PauliOperator,
    canonical_hash,
)


def _single_axis_matrix(dimension, x_exponent, z_exponent):
    omega = np.exp(2j * np.pi / dimension)
    x_matrix = np.zeros((dimension, dimension), dtype=complex)
    for basis in range(dimension):
        x_matrix[(basis + 1) % dimension, basis] = 1
    z_matrix = np.diag([omega**basis for basis in range(dimension)])
    return np.linalg.matrix_power(x_matrix, x_exponent) @ np.linalg.matrix_power(
        z_matrix, z_exponent
    )


def _dense_operator(operator):
    matrices = []
    terms = {term.site_id: term for term in operator.terms}
    for system in operator.module.local_systems:
        term = terms.get(system.site_id)
        for index, factor in enumerate(system.invariant_factors):
            x_value = term.x_exponents[index] if term is not None else 0
            z_value = term.z_exponents[index] if term is not None else 0
            matrices.append(_single_axis_matrix(factor, x_value, z_value))
    result = np.array([[1.0 + 0.0j]])
    for matrix in matrices:
        result = np.kron(result, matrix)
    phase = np.exp(2j * np.pi * operator.phase / operator.module.phase_modulus)
    return phase * result


def test_local_systems_are_canonical_and_support_general_invariant_factors():
    local = LocalSystem("q", (2, 4))
    assert local.hilbert_dimension == 8
    with pytest.raises(ValueError):
        LocalSystem("bad", (4, 6))

    first = PauliModule((LocalSystem.cyclic("b", 4), LocalSystem.cyclic("a", 2)))
    second = PauliModule((LocalSystem.cyclic("a", 2), LocalSystem.cyclic("b", 4)))
    assert first == second
    assert first.phase_modulus == 8
    assert first.hilbert_dimension == 8
    assert first.projective_order == 64


def test_terms_are_combined_reduced_and_canonically_sorted():
    module = PauliModule.from_dimensions((2, 4), ("a", "b"))
    operator = module.operator(
        (
            LocalPauliTerm.cyclic("b", x=5, z=-1),
            LocalPauliTerm.cyclic("a", x=1),
            LocalPauliTerm.cyclic("b", x=-1, z=1),
        ),
        phase=9,
    )
    assert operator.phase == 1
    assert operator.terms == (LocalPauliTerm.cyclic("a", x=1),)


def test_x_and_z_multiply_with_the_declared_normal_order_cocycle():
    module = PauliModule.from_dimensions((4,), ("q",))
    x = module.operator((LocalPauliTerm.cyclic("q", x=1),))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    assert (x * z).phase == 0
    assert (z * x).phase == 2
    assert x.projective_pairing(z) == 6
    assert not x.commutes_with(z)
    np.testing.assert_allclose(_dense_operator(x * z), _dense_operator(x) @ _dense_operator(z))
    np.testing.assert_allclose(_dense_operator(z * x), _dense_operator(z) @ _dense_operator(x))


def test_cross_site_operators_commute_for_mixed_dimensions():
    module = PauliModule.from_dimensions((2, 4), ("qubit", "ququart"))
    left = module.operator((LocalPauliTerm.cyclic("qubit", x=1, z=1),))
    right = module.operator((LocalPauliTerm.cyclic("ququart", x=1, z=1),))
    assert left.commutes_with(right)
    assert left * right == right * left


def test_even_dimension_raw_xz_has_scalar_obstruction_and_lift_fixes_it():
    module = PauliModule.from_dimensions((4,), ("q",))
    raw = module.operator((LocalPauliTerm.cyclic("q", x=1, z=1),))
    assert raw.projective_element_order == 4
    assert raw.power(4).is_projective_identity
    assert raw.scalar_obstruction == 4  # -I in the order-eight phase group
    assert not raw.power(4).is_identity

    lifted = raw.with_phase(1)
    assert lifted.power(4).is_identity
    assert lifted.scalar_obstruction == 0
    np.testing.assert_allclose(
        np.linalg.matrix_power(_dense_operator(raw), 4),
        -np.eye(4),
        atol=1e-10,
    )
    np.testing.assert_allclose(
        np.linalg.matrix_power(_dense_operator(lifted), 4),
        np.eye(4),
        atol=1e-10,
    )


def test_qubit_raw_xz_and_i_xz_distinguish_phase_lifts():
    module = PauliModule.from_dimensions((2,), ("q",))
    raw = module.operator((LocalPauliTerm.cyclic("q", x=1, z=1),))
    lifted = raw.with_phase(1)
    assert raw.power(2).phase == 2
    assert lifted.power(2).is_identity


def test_inverse_and_negative_power_are_exact():
    module = PauliModule.from_dimensions((6,), ("q",))
    operator = module.operator((LocalPauliTerm.cyclic("q", x=2, z=3),), phase=5)
    assert (operator * operator.inverse()).is_identity
    assert (operator.inverse() * operator).is_identity
    assert operator.power(-3) == operator.inverse().power(3)
    np.testing.assert_allclose(_dense_operator(operator.inverse()), np.linalg.inv(_dense_operator(operator)))


def test_projective_order_handles_nonprimitive_composite_exponents():
    module = PauliModule.from_dimensions((12,), ("q",))
    x4 = module.operator((LocalPauliTerm.cyclic("q", x=4),))
    z8 = module.operator((LocalPauliTerm.cyclic("q", z=8),))
    both = module.operator((LocalPauliTerm.cyclic("q", x=4, z=8),))
    assert x4.projective_element_order == 3
    assert z8.projective_element_order == 3
    assert both.projective_element_order == 3


def test_operator_hash_is_invariant_under_site_and_term_input_order():
    first_module = PauliModule.from_dimensions((2, 4), ("a", "b"))
    second_module = PauliModule(
        (LocalSystem.cyclic("b", 4), LocalSystem.cyclic("a", 2))
    )
    first = first_module.operator(
        (LocalPauliTerm.cyclic("b", x=1), LocalPauliTerm.cyclic("a", z=1)),
        phase=3,
    )
    second = second_module.operator(
        (LocalPauliTerm.cyclic("a", z=1), LocalPauliTerm.cyclic("b", x=1)),
        phase=3,
    )
    assert first == second
    assert canonical_hash(PauliOperator.SCHEMA_ID, first) == canonical_hash(
        PauliOperator.SCHEMA_ID, second
    )


def test_dense_oracle_matches_random_small_products():
    module = PauliModule.from_dimensions((2, 3), ("a", "b"))
    operators = []
    for phase in range(module.phase_modulus):
        operators.append(
            module.operator(
                (
                    LocalPauliTerm.cyclic("a", x=phase, z=phase + 1),
                    LocalPauliTerm.cyclic("b", x=2 * phase, z=phase - 1),
                ),
                phase=phase,
            )
        )
    for left, right in zip(operators, reversed(operators)):
        np.testing.assert_allclose(
            _dense_operator(left * right),
            _dense_operator(left) @ _dense_operator(right),
            atol=1e-10,
        )
