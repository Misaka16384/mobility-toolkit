"""2D static visualization helpers."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from mobility_toolkit.boundary_gauge.algebra.pauli_vectors import _format_pauli_math
from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D, StabilizerDict
from mobility_toolkit.boundary_gauge.geometry.lattice_coords import lattice_coordinate_to_index_2d

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


def _require_matplotlib() -> None:
    if plt is None:
        raise ModuleNotFoundError("matplotlib is required for visualization.")


def _axis_bounds_2d(
    Lx: int,
    Ly: int,
    qudit_positions: Sequence[Sequence[float]],
) -> tuple[float, float, float, float]:
    x_offsets = [float(pos[0]) for pos in qudit_positions]
    y_offsets = [float(pos[1]) for pos in qudit_positions]
    x_min = min(-0.75, min(x_offsets) - 0.35)
    x_max = max(float(Lx), (Lx - 1) + max(x_offsets) + 0.35)
    y_min = min(-0.75, min(y_offsets) - 0.35)
    y_max = max(float(Ly), (Ly - 1) + max(y_offsets) + 0.35)
    return x_min, x_max, y_min, y_max


def visualize_operator_2d(
    operator_vector: np.ndarray,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title: str = "Operator Visualization",
) -> None:
    _require_matplotlib()
    num_qudits = Lx * Ly * q
    if len(operator_vector) != 2 * num_qudits:
        raise ValueError(f"Vector length {len(operator_vector)} does not match lattice parameters.")

    fig, ax = plt.subplots(figsize=(max(4.8, Lx * 1.5), max(4.2, Ly * 1.5)))
    for y in range(Ly + 1):
        ax.axhline(y, color="lightgray", linestyle="--", linewidth=0.5, zorder=0)
    for x in range(Lx + 1):
        ax.axvline(x, color="lightgray", linestyle="--", linewidth=0.5, zorder=0)

    has_support = False
    colors = ["#ffcccc", "#ccffcc", "#ccccff", "#ffffcc", "#ffd9b3", "#e6ccff"]

    for idx in range(num_qudits):
        sublattice = idx % q
        temp = idx // q
        x = temp % Lx
        y = temp // Lx
        exp_x = int(operator_vector[2 * idx]) % d
        exp_z = int(operator_vector[2 * idx + 1]) % d
        if exp_x == 0 and exp_z == 0:
            continue

        has_support = True
        pos_x = x + float(qudit_positions[sublattice][0])
        pos_y = y + float(qudit_positions[sublattice][1])
        circle = plt.Circle(
            (pos_x, pos_y),
            0.15,
            color=colors[sublattice % len(colors)],
            ec="black",
            lw=0.5,
            zorder=1,
        )
        ax.add_patch(circle)
        ax.text(
            pos_x,
            pos_y,
            _format_pauli_math(exp_x, exp_z),
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            zorder=2,
        )

    x_min, x_max, y_min, y_max = _axis_bounds_2d(Lx, Ly, qudit_positions)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    ax.set_xticks(range(Lx + 1))
    ax.set_yticks(range(Ly + 1))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title)
    ax.grid(False)
    if not has_support:
        ax.text(
            0.5 * (x_min + x_max),
            0.5 * (y_min + y_max),
            "Identity Operator",
            ha="center",
            va="center",
            fontsize=14,
            color="gray",
        )
    plt.show()
    plt.close(fig)


def visualize_first_n_operators_2d(
    O_matrix: np.ndarray,
    n: int,
    Lx: int,
    Ly: int,
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
        visualize_operator_2d(op, Lx, Ly, q, d, qudit_positions, title=f"{title_prefix} #{i}")
        count += 1


def visualize_stabilizer_generators_2d(
    generators: list[list[GeneratorTerm2D]],
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
        Lx_local = (max_dx - min_dx) + 3
        Ly_local = (max_dy - min_dy) + 3
        tx = -min_dx + 1
        ty = -min_dy + 1
        num_qudits_local = Lx_local * Ly_local * q
        op_vector = np.zeros(2 * num_qudits_local, dtype=int)

        for coeff, dx, dy, sublattice, p_type in gen_poly:
            x = tx + dx
            y = ty + dy
            if 0 <= x < Lx_local and 0 <= y < Ly_local:
                idx = lattice_coordinate_to_index_2d(x, y, sublattice, Lx_local, Ly_local, q)
                op_vector[2 * idx + p_type] = (op_vector[2 * idx + p_type] + coeff) % d

        visualize_operator_2d(
            op_vector,
            Lx_local,
            Ly_local,
            q,
            d,
            qudit_positions,
            title=f"{title_prefix} #{i + 1}",
        )


def visualize_all_stabilizers_2d(
    stabilizers: list[StabilizerDict],
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    qudit_positions: Sequence[Sequence[float]],
    title_prefix: str = "Valid Bulk Stabilizer",
) -> None:
    num_qudits = Lx * Ly * q
    print(f"\n=== Visualizing All {len(stabilizers)} Valid Bulk Stabilizers ===")
    for i, stab in enumerate(stabilizers):
        op_vec = np.zeros(2 * num_qudits, dtype=int)
        for q_idx, (sx, sz) in stab.items():
            op_vec[2 * q_idx] = sx % d
            op_vec[2 * q_idx + 1] = sz % d
        visualize_operator_2d(op_vec, Lx, Ly, q, d, qudit_positions, title=f"{title_prefix} #{i}")


__all__ = [
    "visualize_all_stabilizers_2d",
    "visualize_first_n_operators_2d",
    "visualize_operator_2d",
    "visualize_stabilizer_generators_2d",
]
