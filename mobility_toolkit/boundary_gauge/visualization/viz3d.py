"""3D static visualization helpers."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from mobility_toolkit.boundary_gauge.algebra.pauli_vectors import _format_pauli
from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm3D, StabilizerDict
from mobility_toolkit.boundary_gauge.geometry.lattice_coords import (
    lattice_coordinate_to_index_3d,
    lattice_index_to_coordinate_3d,
)

try:
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as path_effects
except ModuleNotFoundError:
    plt = None
    path_effects = None


def _require_matplotlib() -> None:
    if plt is None:
        raise ModuleNotFoundError("matplotlib is required for visualization.")


def _axis_bounds_3d(
    Lx: int,
    Ly: int,
    Lz: int,
    qudit_positions: Sequence[Sequence[float]],
) -> tuple[float, float, float, float, float, float]:
    x_offsets = [float(pos[0]) for pos in qudit_positions]
    y_offsets = [float(pos[1]) for pos in qudit_positions]
    z_offsets = [float(pos[2]) for pos in qudit_positions]
    x_min = min(-0.75, min(x_offsets) - 0.35)
    x_max = max(float(Lx), (Lx - 1) + max(x_offsets) + 0.35)
    y_min = min(-0.75, min(y_offsets) - 0.35)
    y_max = max(float(Ly), (Ly - 1) + max(y_offsets) + 0.35)
    z_min = min(-0.75, min(z_offsets) - 0.35)
    z_max = max(float(Lz), (Lz - 1) + max(z_offsets) + 0.35)
    return x_min, x_max, y_min, y_max, z_min, z_max


def _draw_3d_grid(ax, Lx: int, Ly: int, Lz: int) -> None:
    for z in range(Lz + 1):
        for y in range(Ly + 1):
            ax.plot([0, Lx], [y, y], [z, z], color="lightgray", linewidth=0.4, alpha=0.6, zorder=0)
        for x in range(Lx + 1):
            ax.plot([x, x], [0, Ly], [z, z], color="lightgray", linewidth=0.4, alpha=0.6, zorder=0)
    for x in range(Lx + 1):
        for y in range(Ly + 1):
            ax.plot([x, x], [y, y], [0, Lz], color="lightgray", linewidth=0.35, alpha=0.45, zorder=0)


def _draw_xy_slice_background(ax, Lx: int, Ly: int) -> None:
    for y in range(Ly + 1):
        ax.axhline(y, color="lightgray", linestyle="--", linewidth=0.5, zorder=0)
    for x in range(Lx + 1):
        ax.axvline(x, color="lightgray", linestyle="--", linewidth=0.5, zorder=0)


def _add_3d_axis(fig, gridspec_cell):
    try:
        return fig.add_subplot(gridspec_cell, projection="3d", computed_zorder=False)
    except TypeError:
        ax = fig.add_subplot(gridspec_cell, projection="3d")
        if hasattr(ax, "computed_zorder"):
            ax.computed_zorder = False
        return ax


def visualize_operator_3d(
    operator_vector: np.ndarray,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title: str = "Operator Visualization",
) -> None:
    _require_matplotlib()
    num_qudits = Lx * Ly * Lz * q
    if len(operator_vector) != 2 * num_qudits:
        raise ValueError(f"Vector length {len(operator_vector)} does not match lattice parameters.")

    supported = []
    for idx in range(num_qudits):
        exp_x = int(operator_vector[2 * idx]) % d
        exp_z = int(operator_vector[2 * idx + 1]) % d
        if exp_x == 0 and exp_z == 0:
            continue
        x, y, z, sublattice = lattice_index_to_coordinate_3d(idx, Lx, Ly, Lz, q)
        supported.append((idx, x, y, z, sublattice, exp_x, exp_z))

    slice_cols = min(3, max(1, Lz))
    slice_rows = math.ceil(max(1, Lz) / slice_cols)
    fig = plt.figure(figsize=(8 + 4 * slice_cols, max(5, 3.5 * slice_rows)))
    outer = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.55], wspace=0.25)
    ax3d = _add_3d_axis(fig, outer[0, 0])
    slice_grid = outer[0, 1].subgridspec(slice_rows, slice_cols, wspace=0.25, hspace=0.35)
    _draw_3d_grid(ax3d, Lx, Ly, Lz)

    colors = ["#ff9999", "#99cc99", "#99b3ff", "#ffd699", "#d5b3ff", "#c2f0f0"]
    has_support = False

    for _, x, y, z, sublattice, exp_x, exp_z in supported:
        has_support = True
        pos_x = x + float(qudit_positions[sublattice][0])
        pos_y = y + float(qudit_positions[sublattice][1])
        pos_z = z + float(qudit_positions[sublattice][2])
        label = _format_pauli(exp_x, exp_z)
        color = colors[sublattice % len(colors)]
        ax3d.scatter(
            [pos_x],
            [pos_y],
            [pos_z],
            s=180,
            c=color,
            edgecolors="black",
            linewidths=0.6,
            depthshade=False,
            zorder=2,
        )
        # Text and markers share a 3D coordinate; default depth sorting can hide the text behind the marker.
        text = ax3d.text(
            pos_x,
            pos_y,
            pos_z,
            label,
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="center",
            color="black",
            zorder=5,
            clip_on=False,
        )
        if path_effects is not None:
            text.set_path_effects([path_effects.withStroke(linewidth=2.2, foreground="white")])

    x_min, x_max, y_min, y_max, z_min, z_max = _axis_bounds_3d(Lx, Ly, Lz, qudit_positions)
    if not has_support:
        ax3d.text(
            0.5 * (x_min + x_max),
            0.5 * (y_min + y_max),
            0.5 * (z_min + z_max),
            "Identity Operator",
            fontsize=12,
            color="gray",
        )
    ax3d.set_xlim(x_min, x_max)
    ax3d.set_ylim(y_min, y_max)
    ax3d.set_zlim(z_min, z_max)
    ax3d.set_box_aspect((max(x_max - x_min, 1.0), max(y_max - y_min, 1.0), max(z_max - z_min, 1.0)))
    ax3d.set_xticks(range(Lx + 1))
    ax3d.set_yticks(range(Ly + 1))
    ax3d.set_zticks(range(Lz + 1))
    ax3d.set_xlabel("x")
    ax3d.set_ylabel("y")
    ax3d.set_zlabel("z")
    ax3d.view_init(elev=24, azim=-55)
    ax3d.set_title("3D Overview")

    for slice_index in range(slice_rows * slice_cols):
        row = slice_index // slice_cols
        col = slice_index % slice_cols
        ax = fig.add_subplot(slice_grid[row, col])
        if slice_index >= Lz:
            ax.axis("off")
            continue

        z_layer = slice_index
        _draw_xy_slice_background(ax, Lx, Ly)
        for _, x, y, z, sublattice, exp_x, exp_z in supported:
            if z != z_layer:
                continue
            pos_x = x + float(qudit_positions[sublattice][0])
            pos_y = y + float(qudit_positions[sublattice][1])
            label = _format_pauli(exp_x, exp_z)
            color = colors[sublattice % len(colors)]
            circle = plt.Circle((pos_x, pos_y), 0.16, color=color, ec="black", lw=0.5, zorder=1)
            ax.add_patch(circle)
            ax.text(pos_x, pos_y, label, ha="center", va="center", fontsize=10, fontweight="bold", zorder=2)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        ax.set_aspect("equal")
        ax.set_xticks(range(Lx + 1))
        ax.set_yticks(range(Ly + 1))
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"xy slice at z = {z_layer}")
        ax.grid(False)
        if not has_support:
            ax.text(
                0.5 * (x_min + x_max),
                0.5 * (y_min + y_max),
                "Identity",
                ha="center",
                va="center",
                fontsize=11,
                color="gray",
            )

    fig.suptitle(title)
    fig.subplots_adjust(top=0.90)
    plt.show()
    plt.close(fig)


def visualize_first_n_operators_3d(
    O_matrix: np.ndarray,
    n: int,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title_prefix: str = "Boundary Gauge Operator",
) -> None:
    count = 0
    for i in range(O_matrix.shape[0]):
        if count >= n:
            break
        op = O_matrix[i]
        if not np.any(op):
            continue
        visualize_operator_3d(op, Lx, Ly, Lz, q, d, qudit_positions, title=f"{title_prefix} #{i}")
        count += 1


def visualize_stabilizer_generators_3d(
    generators: list[list[GeneratorTerm3D]],
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title_prefix: str = "Bulk Stabilizer Generator",
) -> None:
    print(f"\n=== Visualizing {len(generators)} Stabilizer Generators ===")
    for i, gen_poly in enumerate(generators):
        if not gen_poly:
            continue
        min_dx = min(term[1] for term in gen_poly)
        max_dx = max(term[1] for term in gen_poly)
        min_dy = min(term[2] for term in gen_poly)
        max_dy = max(term[2] for term in gen_poly)
        min_dz = min(term[3] for term in gen_poly)
        max_dz = max(term[3] for term in gen_poly)
        Lx_local = (max_dx - min_dx) + 3
        Ly_local = (max_dy - min_dy) + 3
        Lz_local = (max_dz - min_dz) + 3
        tx = -min_dx + 1
        ty = -min_dy + 1
        tz = -min_dz + 1
        num_qudits_local = Lx_local * Ly_local * Lz_local * q
        op_vector = np.zeros(2 * num_qudits_local, dtype=int)

        for coeff, dx, dy, dz, sublattice, p_type in gen_poly:
            x = tx + dx
            y = ty + dy
            z = tz + dz
            if 0 <= x < Lx_local and 0 <= y < Ly_local and 0 <= z < Lz_local:
                idx = lattice_coordinate_to_index_3d(x, y, z, sublattice, Lx_local, Ly_local, Lz_local, q)
                op_vector[2 * idx + p_type] = (op_vector[2 * idx + p_type] + coeff) % d

        visualize_operator_3d(
            op_vector,
            Lx_local,
            Ly_local,
            Lz_local,
            q,
            d,
            qudit_positions,
            title=f"{title_prefix} #{i + 1}",
        )


def visualize_all_stabilizers_3d(
    stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title_prefix: str = "Valid Bulk Stabilizer",
) -> None:
    num_qudits = Lx * Ly * Lz * q
    print(f"\n=== Visualizing All {len(stabilizers)} Valid Bulk Stabilizers ===")
    for i, stab in enumerate(stabilizers):
        op_vec = np.zeros(2 * num_qudits, dtype=int)
        for q_idx, (sx, sz) in stab.items():
            op_vec[2 * q_idx] = sx % d
            op_vec[2 * q_idx + 1] = sz % d
        visualize_operator_3d(op_vec, Lx, Ly, Lz, q, d, qudit_positions, title=f"{title_prefix} #{i}")


__all__ = [
    "visualize_all_stabilizers_3d",
    "visualize_first_n_operators_3d",
    "visualize_operator_3d",
    "visualize_stabilizer_generators_3d",
]
