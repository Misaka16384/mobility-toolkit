import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import FiniteMetricGroup
from mobility_toolkit.core import SparseIntMatrix
from mobility_toolkit.finite import FiniteAbelianGroup, FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def toric_z2(backend):
    # D(Z_2): q(a,b)=ab/2 and B((a,b),(c,d))=(ad+bc)/2.
    group = FiniteAbelianGroup.from_coordinate_orders((2, 2), backend, ("e", "m"))
    return FiniteMetricGroup.create(
        group,
        2,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        (0, 0),
        backend,
    )


def toric_z4(backend):
    # D(Z_4): q(a,b)=ab/4 and B((a,b),(c,d))=(ad+bc)/4.
    group = FiniteAbelianGroup.from_coordinate_orders((4, 4), backend, ("e", "m"))
    return FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((0, 1), (1, 0))),
        (0, 0),
        backend,
    )


def double_semion(backend):
    # Double semion: q(s)=1/4, q(sbar)=-1/4, B(s,s)=B(sbar,sbar)=1/2.
    group = FiniteAbelianGroup.from_coordinate_orders(
        (2, 2), backend, ("semion", "anti-semion")
    )
    return FiniteMetricGroup.create(
        group,
        4,
        SparseIntMatrix.from_rows(((2, 0), (0, 2))),
        (1, 3),
        backend,
    )


def test_z2_toric_metric_data_and_alternating_bridge(backend):
    metric = toric_z2(backend)
    assert metric.group.invariant_factors == (2, 2)
    assert metric.spin_exponent((1, 0)) == 0
    assert metric.spin_exponent((0, 1)) == 0
    assert metric.spin_exponent((1, 1)) == 1
    assert metric.braiding_exponent((1, 0), (0, 1)) == 1
    assert metric.certificate.nondegenerate
    metric.verify_certificate(backend)
    # Only this mod-2 symmetric form also satisfies the alternating API.
    metric.as_alternating_pairing().verify_certificate()


def test_z4_toric_quadratic_refinement_and_metric_validation(backend):
    metric = toric_z4(backend)
    assert metric.spin_exponent((1, 1)) == 1
    assert metric.spin_exponent((2, 1)) == 2
    assert metric.braiding_exponent((3, 2), (1, 3)) == (3 * 3 + 2) % 4
    assert metric.certificate.ambient_radical.order(backend) == 1
    # Symmetric Z4 monodromy is not an alternating Pauli commutator.
    with pytest.raises(ValueError, match="not alternating"):
        metric.as_alternating_pairing()


def test_double_semion_spins_and_boson(backend):
    metric = double_semion(backend)
    assert metric.spin_exponent((1, 0)) == 1
    assert metric.spin_exponent((0, 1)) == 3
    assert metric.spin_exponent((1, 1)) == 0
    assert metric.braiding_exponent((1, 0), (1, 0)) == 2
    assert metric.braiding_exponent((1, 0), (0, 1)) == 0


def test_invalid_metric_data_is_rejected_exactly(backend):
    group = FiniteAbelianGroup.from_coordinate_orders((2,), backend)
    with pytest.raises(ValueError, match="quadratic refinement"):
        FiniteMetricGroup.create(
            group,
            4,
            SparseIntMatrix.from_rows(((0,),)),
            (1,),
            backend,
        )
    with pytest.raises(ValueError, match="degenerate"):
        FiniteMetricGroup.create(
            group,
            2,
            SparseIntMatrix.from_rows(((0,),)),
            (0,),
            backend,
        )

