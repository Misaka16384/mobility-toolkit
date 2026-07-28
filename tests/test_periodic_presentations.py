import pytest

from mobility_toolkit.core import (
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
    canonical_hash,
)
from mobility_toolkit.periodic import (
    PauliAxis,
    QuasiFreePauliModulePresentation,
)


def _mixed_code(dimensions=(2, 4)):
    group = TranslationGroup(2, free_generator_names=("x", "y"))
    species = tuple(
        LocalSystem.cyclic(name, dimension)
        for name, dimension in zip(("a", "b"), dimensions)
    )
    template = OperatorTemplate(
        0,
        (
            OperatorTerm.cyclic((0, 0), "a", x=1),
            OperatorTerm.cyclic((1, -1), "b", z=1),
        ),
    )
    return PeriodicCode(group, species, (template,))


def test_mixed_2_4_presentation_has_explicit_order_relations():
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(_mixed_code())
    assert presentation.coefficient_modulus == 4
    assert [element.basis_id for element in presentation.basis] == [
        "X:a:0",
        "X:b:0",
        "Z:a:0",
        "Z:b:0",
    ]
    assert [element.local_order for element in presentation.basis] == [2, 4, 2, 4]
    assert {(relation.basis_id, relation.order) for relation in presentation.local_order_relations} == {
        ("X:a:0", 2),
        ("X:b:0", 4),
        ("Z:a:0", 2),
        ("Z:b:0", 4),
    }
    column = presentation.stabilizer_image.columns[0]
    assert column.image.coefficient("X:a:0") is not None
    shifted = column.image.coefficient("Z:b:0")
    assert shifted.terms[0].free_exponents == (1, -1)


def test_mixed_2_3_uses_z6_group_ring_with_2_and_3_relations():
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(
        _mixed_code((2, 3))
    )
    assert presentation.coefficient_modulus == 6
    assert presentation.distinct_local_orders == (2, 3)
    assert not presentation.is_uniform


def test_noncyclic_local_system_has_one_basis_pair_per_invariant_factor():
    group = TranslationGroup(1)
    code = PeriodicCode(
        group,
        (LocalSystem("q", (2, 4)),),
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm((0,), "q", (1, 0), (0, 1)),
                ),
            ),
        ),
    )
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(code)
    assert [(element.axis, element.component, element.local_order) for element in presentation.basis] == [
        (PauliAxis.X, 0, 2),
        (PauliAxis.X, 1, 4),
        (PauliAxis.Z, 0, 2),
        (PauliAxis.Z, 1, 4),
    ]


def test_presentation_hash_ignores_species_and_template_input_order():
    group = TranslationGroup(1)
    a = LocalSystem.cyclic("a", 2)
    b = LocalSystem.cyclic("b", 2)
    x_a = OperatorTemplate(0, (OperatorTerm.cyclic((0,), "a", x=1),))
    z_b = OperatorTemplate(0, (OperatorTerm.cyclic((1,), "b", z=1),))
    first = QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(group, (b, a), (z_b, x_a))
    )
    second = QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(group, (a, b), (x_a, z_b))
    )
    assert canonical_hash(first.SCHEMA_ID, first) == canonical_hash(second.SCHEMA_ID, second)


def test_uniform_prime_presentation_renders_existing_matrix_row_convention():
    group = TranslationGroup(2)
    code = PeriodicCode(
        group,
        (LocalSystem.cyclic("q", 2),),
        (
            OperatorTemplate(
                0,
                (
                    OperatorTerm.cyclic((0, 0), "q", x=1),
                    OperatorTerm.cyclic((1, -1), "q", z=1),
                ),
            ),
        ),
    )
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(code)
    assert presentation.to_legacy_generator_rows() == (("1", "x1*t2"),)


def test_nonuniform_presentation_refuses_legacy_free_module_rendering():
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(_mixed_code())
    with pytest.raises(ValueError, match="uniform local order"):
        presentation.to_legacy_generator_rows()


def test_ruba_yang_z4_example_is_reproduced_as_canonical_presentation_only():
    """Reproduce arXiv:2204.06023v3 Sec. 7.8, Eqs. (99)--(103).

    This fixture certifies the paper's input matrix, not the currently
    experimental composite Ext execution path.
    """

    group = TranslationGroup(2, free_generator_names=("x", "y"))
    species = (LocalSystem.cyclic("a", 4), LocalSystem.cyclic("b", 4))
    columns = (
        OperatorTemplate(
            0,
            (
                OperatorTerm.cyclic((0, 0), "a", x=2),
                OperatorTerm.cyclic((-1, 0), "a", x=2),
                OperatorTerm.cyclic((0, 0), "b", x=2),
                OperatorTerm.cyclic((0, -1), "b", x=2),
            ),
        ),
        OperatorTemplate(
            0,
            (
                OperatorTerm.cyclic((0, 0), "a", z=1),
                OperatorTerm.cyclic((0, 1), "a", z=-1),
                OperatorTerm.cyclic((0, 0), "b", z=1),
                OperatorTerm.cyclic((1, 0), "b", z=-1),
            ),
        ),
        OperatorTemplate(0, (OperatorTerm.cyclic((0, 0), "a", z=2),)),
        OperatorTemplate(0, (OperatorTerm.cyclic((0, 0), "b", z=2),)),
    )
    presentation = QuasiFreePauliModulePresentation.from_periodic_code(
        PeriodicCode(group, species, columns)
    )
    assert set(presentation.to_legacy_generator_rows()) == {
        ("2*t1 + 2", "2*t2 + 2", "0", "0"),
        ("0", "0", "1 + 3*x2", "1 + 3*x1"),
        ("0", "0", "2", "0"),
        ("0", "0", "0", "2"),
    }
