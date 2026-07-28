import itertools

import numpy as np
import pytest

pytest.importorskip("flint")

from mobility_toolkit.core import LocalPauliTerm, PauliModule
from mobility_toolkit.finite import (
    FinitePauliCoordinates,
    FlintIntegerBackend,
    InvalidStabilizerGroup,
    analyze_finite_stabilizer,
    validate_stabilizer_generators,
)


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _cyclic(module, site, x=0, z=0, phase=0):
    return module.operator((LocalPauliTerm.cyclic(site, x=x, z=z),), phase=phase)


def _dense_local_pauli(dimension, x, z):
    shift = np.zeros((dimension, dimension), dtype=complex)
    for basis in range(dimension):
        shift[(basis + x) % dimension, basis] = 1
    omega = np.exp(2j * np.pi / dimension)
    clock = np.diag([omega ** (z * basis) for basis in range(dimension)])
    return np.linalg.matrix_power(shift, 1) @ clock


def _dense_operator(operator):
    terms = {term.site_id: term for term in operator.terms}
    matrices = []
    for system in operator.module.local_systems:
        local = np.array([[1.0 + 0j]])
        term = terms.get(system.site_id)
        for index, dimension in enumerate(system.invariant_factors):
            x = 0 if term is None else term.x_exponents[index]
            z = 0 if term is None else term.z_exponents[index]
            local = np.kron(local, _dense_local_pauli(dimension, x, z))
        matrices.append(local)
    result = np.array([[1.0 + 0j]])
    for matrix in matrices:
        result = np.kron(result, matrix)
    phase = np.exp(2j * np.pi * operator.phase / operator.module.phase_modulus)
    return phase * result


def _dense_codespace_dimension(module, generators):
    dimension = module.hilbert_dimension
    projector = np.eye(dimension, dtype=complex)
    for generator in generators:
        matrix = _dense_operator(generator)
        order = generator.projective_element_order
        average = sum(
            np.linalg.matrix_power(matrix, exponent) for exponent in range(order)
        ) / order
        projector = projector @ average
    eigenvalues = np.linalg.eigvalsh((projector + projector.conj().T) / 2)
    return int(np.count_nonzero(eigenvalues > 0.5))


@pytest.mark.parametrize(
    "dimension,x,expected_k,expected_logical",
    (
        (4, 2, 2, (2, 2)),
        (6, 2, 2, (2, 2)),
        (6, 3, 3, (3, 3)),
        (12, 4, 4, (4, 4)),
    ),
)
def test_single_qudit_composite_benchmarks(
    backend, dimension, x, expected_k, expected_logical
):
    module = PauliModule.from_dimensions((dimension,), ("q",))
    generators = (_cyclic(module, "q", x=x),)
    result = analyze_finite_stabilizer(module, generators, backend)
    assert result.codespace_dimension == expected_k
    assert result.logical_invariant_factors == expected_logical
    assert result.logical_projective_order == expected_k**2
    assert _dense_codespace_dimension(module, generators) == expected_k


def test_ququart_phase_obstruction_and_valid_lift(backend):
    module = PauliModule.from_dimensions((4,), ("q",))
    raw_xz = _cyclic(module, "q", x=1, z=1)
    validation = validate_stabilizer_generators(module, (raw_xz,), backend)
    assert not validation.valid
    assert validation.relation_scalar_phases == (4,)
    with pytest.raises(InvalidStabilizerGroup, match="nontrivial scalar"):
        analyze_finite_stabilizer(module, (raw_xz,), backend)

    lifted = raw_xz.with_phase(1)
    result = analyze_finite_stabilizer(module, (lifted,), backend)
    assert lifted.power(4).is_identity
    assert result.codespace_dimension == 1
    assert _dense_codespace_dimension(module, (lifted,)) == 1


def test_ququart_two_generator_unique_state(backend):
    module = PauliModule.from_dimensions((4,), ("q",))
    generators = (
        _cyclic(module, "q", x=2),
        _cyclic(module, "q", z=2),
    )
    result = analyze_finite_stabilizer(module, generators, backend)
    assert result.codespace_dimension == 1
    assert result.logical_invariant_factors == ()
    assert _dense_codespace_dimension(module, generators) == 1


@pytest.mark.parametrize(
    "dimensions,acted_sites,expected_k",
    (
        ((2, 3), ("a", "b"), 1),
        ((2, 4), ("a", "b"), 2),
        ((2, 4), ("a",), 4),
        ((3, 6), ("a",), 6),
    ),
)
def test_mixed_local_dimensions(backend, dimensions, acted_sites, expected_k):
    module = PauliModule.from_dimensions(dimensions, ("a", "b"))
    terms = tuple(LocalPauliTerm.cyclic(site, x=1) for site in acted_sites)
    generator = module.operator(terms)
    result = analyze_finite_stabilizer(module, (generator,), backend)
    assert result.codespace_dimension == expected_k
    assert _dense_codespace_dimension(module, (generator,)) == expected_k


def test_bell_stabilizer_and_pairing_are_exact(backend):
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    generators = (
        module.operator(
            (LocalPauliTerm.cyclic("a", x=1), LocalPauliTerm.cyclic("b", x=1))
        ),
        module.operator(
            (LocalPauliTerm.cyclic("a", z=1), LocalPauliTerm.cyclic("b", z=1))
        ),
    )
    result = analyze_finite_stabilizer(module, generators, backend)
    assert result.codespace_dimension == 1
    assert result.stabilizer.order(backend) == 4
    assert result.centralizer.order(backend) == 4
    assert _dense_codespace_dimension(module, generators) == 1


def test_duplicate_projective_generator_with_conflicting_phase_is_rejected(backend):
    module = PauliModule.from_dimensions((2,), ("q",))
    x = _cyclic(module, "q", x=1)
    minus_x = x.with_phase(module.phase_modulus // 2)
    validation = validate_stabilizer_generators(module, (x, minus_x), backend)
    assert not validation.valid
    assert any(validation.relation_scalar_phases)


def test_noncommuting_generators_are_rejected(backend):
    module = PauliModule.from_dimensions((3,), ("q",))
    x = _cyclic(module, "q", x=1)
    z = _cyclic(module, "q", z=1)
    validation = validate_stabilizer_generators(module, (x, z), backend)
    assert not validation.valid
    assert validation.commutator_matrix.entries
    with pytest.raises(InvalidStabilizerGroup, match="do not commute"):
        analyze_finite_stabilizer(module, (x, z), backend)


def test_empty_stabilizer_has_full_logical_pauli_group(backend):
    module = PauliModule.from_dimensions((2, 3), ("a", "b"))
    result = analyze_finite_stabilizer(module, (), backend)
    assert result.codespace_dimension == 6
    assert result.logical_projective_order == 36
    assert result.logical_invariant_factors == (6, 6)


def test_coordinate_pairing_matches_operator_pairing_exhaustively(backend):
    module = PauliModule.from_dimensions((2, 3), ("a", "b"))
    coordinates = FinitePauliCoordinates.from_module(module)
    pairing = coordinates.pairing_matrix.to_rows()
    modulus = module.phase_modulus
    ranges = [range(order) for order in coordinates.coordinate_orders]
    vectors = tuple(itertools.product(*ranges))
    for left_values in vectors:
        left = coordinates.operator(left_values)
        for right_values in vectors:
            right = coordinates.operator(right_values)
            matrix_value = sum(
                left_values[row] * pairing[row][column] * right_values[column]
                for row in range(coordinates.rank)
                for column in range(coordinates.rank)
            ) % modulus
            assert matrix_value == left.projective_pairing(right)


def test_centralizer_matches_brute_force_for_mixed_group(backend):
    module = PauliModule.from_dimensions((2, 3), ("a", "b"))
    coordinates = FinitePauliCoordinates.from_module(module)
    generator = module.operator(
        (LocalPauliTerm.cyclic("a", x=1), LocalPauliTerm.cyclic("b", x=1))
    )
    result = analyze_finite_stabilizer(module, (generator,), backend)
    ranges = [range(order) for order in coordinates.coordinate_orders]
    explicit = {
        vector
        for vector in itertools.product(*ranges)
        if coordinates.operator(vector).commutes_with(generator)
    }
    observed = {
        vector
        for vector in itertools.product(*ranges)
        if result.centralizer.contains(vector, backend)
    }
    assert observed == explicit
    assert result.centralizer.order(backend) == len(explicit)


def test_generator_reordering_and_redundancy_preserve_invariants(backend):
    module = PauliModule.from_dimensions((4,), ("q",))
    x2 = _cyclic(module, "q", x=2)
    z2 = _cyclic(module, "q", z=2)
    first = analyze_finite_stabilizer(module, (x2, z2), backend)
    second = analyze_finite_stabilizer(module, (z2, x2, x2), backend)
    assert first.stabilizer == second.stabilizer
    assert first.centralizer == second.centralizer
    assert first.logical_invariant_factors == second.logical_invariant_factors
    assert first.codespace_dimension == second.codespace_dimension


def test_dense_oracle_detects_invalid_lift_has_no_fixed_state(backend):
    module = PauliModule.from_dimensions((4,), ("q",))
    raw_xz = _cyclic(module, "q", x=1, z=1)
    assert _dense_codespace_dimension(module, (raw_xz,)) == 0
    assert raw_xz.scalar_obstruction != 0
