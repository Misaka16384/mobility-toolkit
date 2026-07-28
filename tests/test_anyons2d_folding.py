import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    FiniteMetricGroup,
    direct_sum_metric_groups,
    fold_metric_groups,
)
from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _z4_toric(backend):
    # D(Z_4): q(a,b)=ab/4, B((a,b),(c,d))=(ad+bc)/4.
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend)
    return FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        (0, 0),
        backend,
    )


def test_direct_sum_preserves_second_form_but_folding_reverses_it(backend):
    metric = _z4_toric(backend)
    ordinary = direct_sum_metric_groups(metric, metric, backend)
    folded = fold_metric_groups(metric, metric, backend)
    right_dyon = folded.right_embedding((1, 1))
    assert ordinary.metric.spin_exponent(ordinary.right_embedding((1, 1))) == 1
    assert folded.metric.spin_exponent(right_dyon) == 3
    assert folded.metric.braiding_exponent(
        folded.right_embedding((1, 0)), folded.right_embedding((0, 1))
    ) == 3
    assert folded.metric.braiding_exponent(
        folded.left_embedding((1, 0)), folded.left_embedding((0, 1))
    ) == 1
    assert folded.second_form_reversed
    assert folded.metric.group.order(backend) == 16 * 16


def test_folding_uses_exact_common_phase_modulus(backend):
    z4 = _z4_toric(backend)
    z2_group = FiniteAbelianGroup.from_coordinate_orders((2, 2), backend)
    z2 = FiniteMetricGroup.create(
        z2_group,
        2,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        (0, 0),
        backend,
    )
    folded = fold_metric_groups(z2, z4, backend)
    assert folded.metric.phase_modulus == 4
    assert folded.metric.braiding_exponent(
        folded.left_embedding((1, 0)), folded.left_embedding((0, 1))
    ) == 2
    assert folded.metric.braiding_exponent(
        folded.right_embedding((1, 0)), folded.right_embedding((0, 1))
    ) == 3

