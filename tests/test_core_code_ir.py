import pytest

from mobility_toolkit.core import (
    LaurentPolynomial,
    LaurentTerm,
    LocalPauliTerm,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PauliModule,
    PeriodicCode,
    StabilizerCodeSpec,
    SubsystemCodeSpec,
    TranslationGroup,
    canonical_hash,
)


def test_laurent_polynomial_normalizes_coefficients_and_exponents():
    group = TranslationGroup(2, (4,), ("x", "y"))
    polynomial = LaurentPolynomial(
        6,
        group,
        (
            LaurentTerm(7, (1, -2), (5,)),
            LaurentTerm(5, (1, -2), (1,)),
            LaurentTerm(6, (0, 0), (0,)),
        ),
    )
    assert polynomial.terms == ()


def test_laurent_multiplication_and_involution_respect_group_inverse():
    group = TranslationGroup(2, free_generator_names=("x", "y"))
    x = LaurentPolynomial.monomial(5, group, 1, (1, 0))
    x_inv = LaurentPolynomial.monomial(5, group, 1, (-1, 0))
    y = LaurentPolynomial.monomial(5, group, 1, (0, 1))
    assert x * x_inv == LaurentPolynomial.one(5, group)
    assert (x + y).involution() == x_inv + LaurentPolynomial.monomial(5, group, 1, (0, -1))


def test_laurent_ring_mismatch_is_rejected():
    group = TranslationGroup(1)
    first = LaurentPolynomial.one(2, group)
    second = LaurentPolynomial.one(3, group)
    with pytest.raises(ValueError, match="different group rings"):
        _ = first + second


def test_stabilizer_spec_reports_basic_commutation_and_phase_errors():
    module = PauliModule.from_dimensions((2,), ("q",))
    x = module.operator((LocalPauliTerm.cyclic("q", x=1),))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    noncommuting = StabilizerCodeSpec(module, (x, z))
    assert noncommuting.basic_validation_errors() == (
        "generators are not pairwise projectively commuting",
    )

    raw_xz = module.operator((LocalPauliTerm.cyclic("q", x=1, z=1),))
    invalid_lift = StabilizerCodeSpec(module, (raw_xz,))
    assert invalid_lift.basic_validation_errors() == (
        "one or more generators has a scalar order obstruction",
    )


def test_stabilizer_spec_detects_obvious_conflicting_phase_relation():
    module = PauliModule.from_dimensions((4,), ("q",))
    x2 = module.operator((LocalPauliTerm.cyclic("q", x=2),))
    minus_x2 = x2.with_phase(module.phase_modulus // 2)
    code = StabilizerCodeSpec(module, (x2, minus_x2))
    assert code.has_obvious_scalar_conflict
    assert "obvious nontrivial scalar relation" in code.basic_validation_errors()[-1]


def test_stabilizer_generator_order_does_not_change_hash():
    module = PauliModule.from_dimensions((2, 2), ("a", "b"))
    xx = module.operator(
        (LocalPauliTerm.cyclic("a", x=1), LocalPauliTerm.cyclic("b", x=1))
    )
    zz = module.operator(
        (LocalPauliTerm.cyclic("a", z=1), LocalPauliTerm.cyclic("b", z=1))
    )
    first = StabilizerCodeSpec(module, (xx, zz, xx))
    second = StabilizerCodeSpec(module, (zz, xx))
    assert first == second
    assert first.basic_validation_errors() == ()
    assert canonical_hash(StabilizerCodeSpec.SCHEMA_ID, first) == canonical_hash(
        StabilizerCodeSpec.SCHEMA_ID, second
    )


def test_subsystem_spec_accepts_noncommuting_gauge_generators():
    module = PauliModule.from_dimensions((2,), ("q",))
    x = module.operator((LocalPauliTerm.cyclic("q", x=1),))
    z = module.operator((LocalPauliTerm.cyclic("q", z=1),))
    subsystem = SubsystemCodeSpec(module, (x, z))
    assert len(subsystem.gauge_generators) == 2


def test_periodic_code_is_dimension_independent_and_canonical():
    group = TranslationGroup(4, free_generator_names=("x", "y", "z", "w"))
    species_a = LocalSystem.cyclic("a", 2)
    species_b = LocalSystem.cyclic("b", 4)
    first_template = OperatorTemplate(
        9,
        (
            OperatorTerm.cyclic((1, 0, -2, 3), "b", x=5),
            OperatorTerm.cyclic((0, 0, 0, 0), "a", z=1),
            OperatorTerm.cyclic((1, 0, -2, 3), "b", x=-1),
        ),
    )
    first = PeriodicCode(group, (species_b, species_a), (first_template,))
    second = PeriodicCode(
        group,
        (species_a, species_b),
        (
            OperatorTemplate(
                1,
                (OperatorTerm.cyclic((0, 0, 0, 0), "a", z=1),),
            ),
        ),
    )
    assert first == second
    assert first.unit_cell_pauli_module.phase_modulus == 8


def test_periodic_code_rejects_wrong_offset_or_species_shape():
    group = TranslationGroup(2)
    species = (LocalSystem.cyclic("q", 4),)
    with pytest.raises(ValueError, match="offset rank"):
        PeriodicCode(
            group,
            species,
            (OperatorTemplate(0, (OperatorTerm.cyclic((0,), "q", x=1),)),),
        )
    with pytest.raises(ValueError, match="unknown operator species"):
        PeriodicCode(
            group,
            species,
            (OperatorTemplate(0, (OperatorTerm.cyclic((0, 0), "missing", x=1),)),),
        )
