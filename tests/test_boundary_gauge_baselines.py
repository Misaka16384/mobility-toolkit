"""Focused regression checks for the current modular baseline.

These tests intentionally verify selected current program outputs, not final
paper-level correctness. If tao later confirms an output is mathematically
wrong, update the expected values with an explanation.
"""

from __future__ import annotations

import contextlib
import io
import os

os.environ.setdefault("SYMPY_GROUND_TYPES", "python")

from mobility_toolkit.boundary_gauge.algebra.support import get_support_weight
from mobility_toolkit.boundary_gauge.boundary.pipeline import (
    _run_algorithm_1_boundary_ops_2d,
    _run_algorithm_1_boundary_ops_3d,
)
from mobility_toolkit.boundary_gauge.models.models_2d import (
    POSITIONS_2D_EDGE_POSITIVE,
    get_toric_code_params,
    get_Z4_double_semion_params,
    get_Z4_toric_code_params,
)
from mobility_toolkit.boundary_gauge.models.models_3d import (
    POSITIONS_3D_EDGE_POSITIVE,
    get_3d_toric_code_params,
)


def _weights(ops):
    return [get_support_weight(op) for op in ops]


def _quiet_call(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def test_2d_toric_smooth_bottom_support_reduction_uses_physical_rows():
    bulk, ops, s_mat = _quiet_call(
        _run_algorithm_1_boundary_ops_2d,
        Lx=5,
        Ly=5,
        q=2,
        d=2,
        wx=3,
        wy=3,
        stabilizer_generators=get_toric_code_params(),
        qudit_positions=POSITIONS_2D_EDGE_POSITIVE,
        boundary="bottom",
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    assert len(bulk) == 40
    assert s_mat.shape == (40, 100)
    assert ops.shape == (2, 100)
    assert _weights(ops) == [1, 3]


def test_z4_toric_rough_top_legacy_baseline():
    bulk, ops, s_mat = _quiet_call(
        _run_algorithm_1_boundary_ops_2d,
        Lx=5,
        Ly=5,
        q=2,
        d=4,
        wx=3,
        wy=3,
        stabilizer_generators=get_Z4_toric_code_params(),
        qudit_positions=POSITIONS_2D_EDGE_POSITIVE,
        boundary="top",
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    assert len(bulk) == 40
    assert s_mat.shape == (40, 100)
    assert ops.shape == (2, 100)
    assert _weights(ops) == [1, 3]


def test_z4_double_semion_smooth_bottom_legacy_baseline():
    bulk, ops, s_mat = _quiet_call(
        _run_algorithm_1_boundary_ops_2d,
        Lx=5,
        Ly=5,
        q=2,
        d=4,
        wx=3,
        wy=3,
        stabilizer_generators=get_Z4_double_semion_params(),
        qudit_positions=POSITIONS_2D_EDGE_POSITIVE,
        boundary="bottom",
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    assert len(bulk) == 85
    assert s_mat.shape == (85, 100)
    assert ops.shape == (2, 100)
    assert _weights(ops) == [1, 3]


def test_3d_toric_smooth_bottom_legacy_baseline():
    bulk, ops, s_mat = _quiet_call(
        _run_algorithm_1_boundary_ops_3d,
        Lx=3,
        Ly=3,
        Lz=4,
        q=3,
        d=2,
        wx=2,
        wy=2,
        wz=2,
        stabilizer_generators=get_3d_toric_code_params(),
        qudit_positions=POSITIONS_3D_EDGE_POSITIVE,
        boundary="bottom",
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    assert len(bulk) == 117
    assert s_mat.shape == (89, 216)
    assert ops.shape == (3, 216)
    assert _weights(ops) == [1, 1, 5]
