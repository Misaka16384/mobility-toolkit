import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    FiniteMetricGroup,
    anyon_termination_certificate,
    can_terminate,
    test_condensation as check_condensation,
)
from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _generators(*columns):
    return SparseIntMatrix(
        len(columns[0]),
        len(columns),
        tuple(
            (row, column, value)
            for column, values in enumerate(columns)
            for row, value in enumerate(values)
            if value
        ),
    )


def _toric_z4(backend):
    # D(Z_4): electric and magnetic cyclic subgroups are Lagrangian.
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    return FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        (0, 0),
        backend,
    )


def _double_semion(backend):
    # q(s)=1/4, q(sbar)=-1/4; b=s+sbar is the condensable boson.
    group = FiniteAbelianGroup.from_coordinate_orders((2, 2), backend)
    return FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((2, 0), (0, 2))),
        (1, 3),
        backend,
    )


def test_z4_electric_condensate_is_exactly_lagrangian(backend):
    metric = _toric_z4(backend)
    electric = metric.group.subgroup(_generators((1, 0)), backend)
    result = check_condensation(metric, electric, backend)
    assert result.braiding_isotropic
    assert result.bosonic
    assert result.lagrangian
    assert result.orthogonal_complement == electric
    assert not result.local_completion_constructed


def test_double_semion_boson_condenses_but_semion_does_not(backend):
    metric = _double_semion(backend)
    boson = metric.group.subgroup(_generators((1, 1)), backend)
    semion = metric.group.subgroup(_generators((1, 0)), backend)
    assert check_condensation(metric, boson, backend).lagrangian
    semion_result = check_condensation(metric, semion, backend)
    assert not semion_result.braiding_isotropic
    assert not semion_result.bosonic
    assert not semion_result.lagrangian


def test_termination_is_condensate_membership_not_local_completion(backend):
    metric = _double_semion(backend)
    condensate = metric.group.subgroup(_generators((1, 1)), backend)
    certificate = anyon_termination_certificate(
        metric, condensate, (1, 1), backend
    )
    assert certificate.terminates_algebraically
    assert not certificate.local_completion_constructed
    assert can_terminate(metric, condensate, (1, 1), backend)
    assert not can_terminate(metric, condensate, (1, 0), backend)
    with pytest.raises(ValueError, match="not a member"):
        anyon_termination_certificate(metric, condensate, (1, 0), backend)

