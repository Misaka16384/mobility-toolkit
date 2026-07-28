"""Run the first legacy baseline examples from the modular package.

This script intentionally uses the notebook-compatible wrappers. It is for
manual inspection, not for deciding mathematical correctness.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SYMPY_GROUND_TYPES", "python")
os.environ.setdefault("MPMATH_NOGMPY", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mobility_toolkit.boundary_gauge.algebra.support import get_support_weight
from mobility_toolkit.boundary_gauge.boundary.pipeline import (
    _run_algorithm_1_boundary_ops_2d,
    _run_algorithm_1_boundary_ops_3d,
)
from mobility_toolkit.boundary_gauge.models.models_2d import (
    POSITIONS_2D_EDGE_POSITIVE,
    get_Z4_double_semion_params,
    get_Z4_toric_code_params,
)
from mobility_toolkit.boundary_gauge.models.models_3d import (
    POSITIONS_3D_EDGE_POSITIVE,
    get_3d_toric_code_params,
)


def _weights(ops):
    return [get_support_weight(op) for op in ops]


def main() -> None:
    cases = []

    bulk, ops, _ = _run_algorithm_1_boundary_ops_2d(
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
    cases.append(("Z4 Toric Code rough top", len(bulk), ops.shape[0], _weights(ops)))

    bulk, ops, _ = _run_algorithm_1_boundary_ops_2d(
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
    cases.append(("Z4 Double Semion smooth bottom", len(bulk), ops.shape[0], _weights(ops)))

    bulk, ops, _ = _run_algorithm_1_boundary_ops_3d(
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
    cases.append(("3D Toric Code smooth bottom", len(bulk), ops.shape[0], _weights(ops)))

    print("\nLegacy baseline summary")
    print("=======================")
    for name, bulk_count, final_count, weights in cases:
        print(f"{name}: bulk={bulk_count}, final={final_count}, weights={weights}")


if __name__ == "__main__":
    main()
