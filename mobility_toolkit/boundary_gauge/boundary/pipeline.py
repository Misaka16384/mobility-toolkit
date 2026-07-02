"""Integrated Algorithm 1 pipeline wrappers."""

from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

from mobility_toolkit.boundary_gauge.boundary.bulk_build import (
    construct_M1_matrix_2d,
    construct_M1_matrix_3d,
    convert_bulk_to_S_mat_2d,
    convert_bulk_to_S_mat_3d,
    convert_bulk_to_physical_rows_2d,
    convert_bulk_to_physical_rows_3d,
)
from mobility_toolkit.boundary_gauge.boundary.filter import (
    filter_boundary_gauge_operators_2d,
    filter_boundary_gauge_operators_3d,
    prune_boundary_gauge_ops_2d,
    prune_boundary_gauge_ops_3d,
)
from mobility_toolkit.boundary_gauge.boundary.reduction import (
    simplify_boundary_gauge_ops_2d,
    simplify_boundary_gauge_ops_3d,
)
from mobility_toolkit.boundary_gauge.boundary.strings_2d import print_boundary_operators_2d
from mobility_toolkit.boundary_gauge.boundary.strings_3d import print_boundary_operators_3d
from mobility_toolkit.boundary_gauge.boundary.zero_syndrome import (
    construct_M1_w_and_extract_O_w_2d,
    construct_M1_w_and_extract_O_w_3d,
)
from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D, GeneratorTerm3D, StabilizerDict
from mobility_toolkit.boundary_gauge.visualization.viz2d import (
    visualize_all_stabilizers_2d,
    visualize_first_n_operators_2d,
    visualize_stabilizer_generators_2d,
)
from mobility_toolkit.boundary_gauge.visualization.viz3d import (
    visualize_all_stabilizers_3d,
    visualize_first_n_operators_3d,
    visualize_stabilizer_generators_3d,
)

_VISUALIZATION_WARNING_SHOWN = False


def _visualization_is_enabled(requested: bool) -> bool:
    global _VISUALIZATION_WARNING_SHOWN
    if not requested:
        return False
    try:
        import matplotlib.pyplot  # noqa: F401
    except ModuleNotFoundError:
        if not _VISUALIZATION_WARNING_SHOWN:
            print("matplotlib is not available; keeping algebra output but skipping figures.")
            _VISUALIZATION_WARNING_SHOWN = True
        return False
    return True


def run_algorithm_1_boundary_ops_2d(
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    stabilizer_generators: list[list[GeneratorTerm2D]],
    qudit_positions: Sequence[Sequence[float]],
    boundary: Literal["bottom", "top"] = "bottom",
    visualize_stabilizer_generators_flag: bool = False,
    visualize_first_n_bulk_stabilizers: int = 0,
    visualize_local_boundary_gauge_ops: bool = False,
) -> tuple[list[StabilizerDict], np.ndarray, np.ndarray]:
    """Run the 2D boundary pipeline with physical-row support reduction.

    This is intentionally close to the legacy notebook workflow. The behavioral
    change is that local support reduction uses the full physical bulk
    stabilizer list instead of the row-reduced span matrix ``S_mat``.
    """
    patch_origin = (0, 0) if boundary == "bottom" else (0, Ly - wy)
    print("\n" + "=" * 88)
    print(f"2D Algorithm 1 | boundary={boundary} | system={Lx}x{Ly}, patch={wx}x{wy}, d={d}, q={q}")
    print(f"Patch origin = {patch_origin}; x is periodic, y is open.")
    print("=" * 88)

    if visualize_stabilizer_generators_flag:
        visualize_stabilizer_generators_2d(stabilizer_generators, q, d, qudit_positions)

    _, bulk_stabilizers = construct_M1_matrix_2d(Lx, Ly, d, q, stabilizer_generators)
    print(f"Total qudits = {Lx * Ly * q}; retained fully-supported bulk stabilizers = {len(bulk_stabilizers)}")

    if visualize_first_n_bulk_stabilizers > 0:
        visualize_all_stabilizers_2d(bulk_stabilizers[:visualize_first_n_bulk_stabilizers], Lx, Ly, q, d, qudit_positions)

    S_mat = convert_bulk_to_S_mat_2d(bulk_stabilizers, Lx, Ly, q, d)
    physical_bulk_rows = convert_bulk_to_physical_rows_2d(bulk_stabilizers, Lx, Ly, q, d)
    print(f"Bulk-stabilizer row matrix S_mat shape = {S_mat.shape}")

    O_w_matrix = construct_M1_w_and_extract_O_w_2d(Lx, Ly, q, d, wx, wy, bulk_stabilizers, patch_origin=patch_origin)
    print(f"Raw zero-syndrome operators in boundary patch = {O_w_matrix.shape[0]}")
    if O_w_matrix.shape[0] == 0:
        return bulk_stabilizers, np.empty((0, 2 * Lx * Ly * q), dtype=int), S_mat

    _, raw_boundary_ops = filter_boundary_gauge_operators_2d(O_w_matrix, S_mat, Lx, Ly, q, d)
    print(f"Independent raw boundary gauge operators = {raw_boundary_ops.shape[0]}")
    if raw_boundary_ops.shape[0] == 0:
        return bulk_stabilizers, np.empty((0, 2 * Lx * Ly * q), dtype=int), S_mat

    support_minimized = simplify_boundary_gauge_ops_2d(raw_boundary_ops, physical_bulk_rows, Lx, Ly, q, d)
    boundary_ops = prune_boundary_gauge_ops_2d(support_minimized, S_mat, Lx, Ly, q, d)
    print(f"Final exact boundary gauge operator generators = {boundary_ops.shape[0]}")

    if visualize_local_boundary_gauge_ops:
        visualize_first_n_operators_2d(boundary_ops, boundary_ops.shape[0], Lx, Ly, q, d, qudit_positions)

    return bulk_stabilizers, boundary_ops, S_mat


def run_algorithm_1_boundary_ops_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    wz: int,
    stabilizer_generators: list[list[GeneratorTerm3D]],
    qudit_positions: Sequence[Sequence[float]],
    boundary: Literal["bottom", "top"] = "bottom",
    visualize_stabilizer_generators_flag: bool = False,
    visualize_first_n_bulk_stabilizers: int = 0,
    visualize_local_boundary_gauge_ops: bool = False,
) -> tuple[list[StabilizerDict], np.ndarray, np.ndarray]:
    """Run the 3D boundary pipeline with physical-row support reduction."""
    patch_origin = (0, 0, 0) if boundary == "bottom" else (0, 0, Lz - wz)
    print("\n" + "=" * 96)
    print(f"3D Algorithm 1 | boundary={boundary} | system={Lx}x{Ly}x{Lz}, patch={wx}x{wy}x{wz}, d={d}, q={q}")
    print(f"Patch origin = {patch_origin}; x,y are periodic, z is open.")
    print("=" * 96)

    if visualize_stabilizer_generators_flag:
        visualize_stabilizer_generators_3d(stabilizer_generators, q, d, qudit_positions)

    _, bulk_stabilizers = construct_M1_matrix_3d(Lx, Ly, Lz, d, q, stabilizer_generators)
    print(f"Total qudits = {Lx * Ly * Lz * q}; retained fully-supported bulk stabilizers = {len(bulk_stabilizers)}")

    if visualize_first_n_bulk_stabilizers > 0:
        visualize_all_stabilizers_3d(bulk_stabilizers[:visualize_first_n_bulk_stabilizers], Lx, Ly, Lz, q, d, qudit_positions)

    S_mat = convert_bulk_to_S_mat_3d(bulk_stabilizers, Lx, Ly, Lz, q, d)
    physical_bulk_rows = convert_bulk_to_physical_rows_3d(bulk_stabilizers, Lx, Ly, Lz, q, d)
    print(f"Bulk-stabilizer row matrix S_mat shape = {S_mat.shape}")

    O_w_matrix = construct_M1_w_and_extract_O_w_3d(
        Lx,
        Ly,
        Lz,
        q,
        d,
        wx,
        wy,
        wz,
        bulk_stabilizers,
        patch_origin=patch_origin,
    )
    print(f"Raw zero-syndrome operators in boundary patch = {O_w_matrix.shape[0]}")
    if O_w_matrix.shape[0] == 0:
        return bulk_stabilizers, np.empty((0, 2 * Lx * Ly * Lz * q), dtype=int), S_mat

    _, raw_boundary_ops = filter_boundary_gauge_operators_3d(O_w_matrix, S_mat, Lx, Ly, Lz, q, d)
    print(f"Independent raw boundary gauge operators = {raw_boundary_ops.shape[0]}")
    if raw_boundary_ops.shape[0] == 0:
        return bulk_stabilizers, np.empty((0, 2 * Lx * Ly * Lz * q), dtype=int), S_mat

    support_minimized = simplify_boundary_gauge_ops_3d(raw_boundary_ops, physical_bulk_rows, Lx, Ly, Lz, q, d)
    boundary_ops = prune_boundary_gauge_ops_3d(support_minimized, S_mat, Lx, Ly, Lz, q, d)
    print(f"Final exact boundary gauge operator generators = {boundary_ops.shape[0]}")

    if visualize_local_boundary_gauge_ops:
        visualize_first_n_operators_3d(boundary_ops, boundary_ops.shape[0], Lx, Ly, Lz, q, d, qudit_positions)

    return bulk_stabilizers, boundary_ops, S_mat


def run_and_report_example_2d(
    *,
    example_title: str,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    stabilizer_generators: list[list[GeneratorTerm2D]],
    qudit_positions: Sequence[Sequence[float]],
    boundary: Literal["bottom", "top"],
    visualize: bool = True,
    visualize_generators: bool = True,
    visualize_first_n_bulk_stabilizers: int = 0,
    visualize_boundary_ops: bool = True,
    max_visualized_boundary_ops: int | None = None,
    max_printed_ops: int | None = None,
) -> tuple[list[StabilizerDict], np.ndarray, np.ndarray]:
    print("\n" + "#" * 100)
    print(example_title)
    print(f"boundary = {boundary}; qudit_positions = {list(map(list, qudit_positions))}")
    print("#" * 100)

    can_visualize = _visualization_is_enabled(visualize)

    if can_visualize and visualize_generators:
        visualize_stabilizer_generators_2d(
            stabilizer_generators,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Bulk Stabilizer Generator",
        )

    bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_2d(
        Lx=Lx,
        Ly=Ly,
        q=q,
        d=d,
        wx=wx,
        wy=wy,
        stabilizer_generators=stabilizer_generators,
        qudit_positions=qudit_positions,
        boundary=boundary,
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    if can_visualize and visualize_first_n_bulk_stabilizers > 0:
        visualize_all_stabilizers_2d(
            bulk_stabilizers[:visualize_first_n_bulk_stabilizers],
            Lx,
            Ly,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Valid Bulk Stabilizer",
        )

    print_boundary_operators_2d(
        title=f"{example_title} | Boundary gauge operator generators",
        ops=boundary_ops,
        Lx=Lx,
        Ly=Ly,
        q=q,
        d=d,
        qudit_positions=qudit_positions,
        max_ops=max_printed_ops,
    )

    if can_visualize and visualize_boundary_ops:
        n_vis = boundary_ops.shape[0] if max_visualized_boundary_ops is None else min(max_visualized_boundary_ops, boundary_ops.shape[0])
        visualize_first_n_operators_2d(
            boundary_ops,
            n_vis,
            Lx,
            Ly,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Boundary Gauge Operator",
        )

    return bulk_stabilizers, boundary_ops, S_mat


def run_and_report_example_3d(
    *,
    example_title: str,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    wz: int,
    stabilizer_generators: list[list[GeneratorTerm3D]],
    qudit_positions: Sequence[Sequence[float]],
    boundary: Literal["bottom", "top"],
    visualize: bool = True,
    visualize_generators: bool = True,
    visualize_first_n_bulk_stabilizers: int = 0,
    visualize_boundary_ops: bool = True,
    max_visualized_boundary_ops: int | None = None,
    max_printed_ops: int | None = None,
) -> tuple[list[StabilizerDict], np.ndarray, np.ndarray]:
    print("\n" + "#" * 100)
    print(example_title)
    print(f"boundary = {boundary}; qudit_positions = {list(map(list, qudit_positions))}")
    print("#" * 100)

    can_visualize = _visualization_is_enabled(visualize)

    if can_visualize and visualize_generators:
        visualize_stabilizer_generators_3d(
            stabilizer_generators,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Bulk Stabilizer Generator",
        )

    bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_3d(
        Lx=Lx,
        Ly=Ly,
        Lz=Lz,
        q=q,
        d=d,
        wx=wx,
        wy=wy,
        wz=wz,
        stabilizer_generators=stabilizer_generators,
        qudit_positions=qudit_positions,
        boundary=boundary,
        visualize_stabilizer_generators_flag=False,
        visualize_first_n_bulk_stabilizers=0,
        visualize_local_boundary_gauge_ops=False,
    )

    if can_visualize and visualize_first_n_bulk_stabilizers > 0:
        visualize_all_stabilizers_3d(
            bulk_stabilizers[:visualize_first_n_bulk_stabilizers],
            Lx,
            Ly,
            Lz,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Valid Bulk Stabilizer",
        )

    print_boundary_operators_3d(
        title=f"{example_title} | Boundary gauge operator generators",
        ops=boundary_ops,
        Lx=Lx,
        Ly=Ly,
        Lz=Lz,
        q=q,
        d=d,
        qudit_positions=qudit_positions,
        max_ops=max_printed_ops,
    )

    if can_visualize and visualize_boundary_ops:
        n_vis = boundary_ops.shape[0] if max_visualized_boundary_ops is None else min(max_visualized_boundary_ops, boundary_ops.shape[0])
        visualize_first_n_operators_3d(
            boundary_ops,
            n_vis,
            Lx,
            Ly,
            Lz,
            q,
            d,
            qudit_positions,
            title_prefix=f"{example_title} | Boundary Gauge Operator",
        )

    return bulk_stabilizers, boundary_ops, S_mat


__all__ = [
    "print_boundary_operators_2d",
    "print_boundary_operators_3d",
    "run_algorithm_1_boundary_ops_2d",
    "run_algorithm_1_boundary_ops_3d",
    "run_and_report_example_2d",
    "run_and_report_example_3d",
]
