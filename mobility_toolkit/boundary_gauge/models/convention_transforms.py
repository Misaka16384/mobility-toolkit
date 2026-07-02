"""Sublattice convention transforms."""

from __future__ import annotations

from typing import Sequence

from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D, GeneratorTerm3D


def transform_sublattice_convention_2d(
    generators: list[list[GeneratorTerm2D]],
    old_positions: Sequence[Sequence[float]],
    new_positions: Sequence[Sequence[float]],
) -> list[list[GeneratorTerm2D]]:
    if len(old_positions) != len(new_positions):
        raise ValueError("old_positions and new_positions must have the same length.")
    shifts: list[tuple[int, int]] = []
    for old, new in zip(old_positions, new_positions):
        shifts.append((int(round(old[0] - new[0])), int(round(old[1] - new[1]))))

    transformed: list[list[GeneratorTerm2D]] = []
    for gen in generators:
        if not gen:
            transformed.append([])
            continue
        max_dx_old = max(t[1] for t in gen)
        max_dy_old = max(t[2] for t in gen)
        new_gen: list[GeneratorTerm2D] = []
        for coeff, dx, dy, s, p_type in gen:
            sx, sy = shifts[s]
            new_gen.append((coeff, dx + sx - max_dx_old, dy + sy - max_dy_old, s, p_type))
        transformed.append(new_gen)
    return transformed


def transform_sublattice_convention_3d(
    generators: list[list[GeneratorTerm3D]],
    old_positions: Sequence[Sequence[float]],
    new_positions: Sequence[Sequence[float]],
) -> list[list[GeneratorTerm3D]]:
    if len(old_positions) != len(new_positions):
        raise ValueError("old_positions and new_positions must have the same length.")
    shifts: list[tuple[int, int, int]] = []
    for old, new in zip(old_positions, new_positions):
        shifts.append((
            int(round(old[0] - new[0])),
            int(round(old[1] - new[1])),
            int(round(old[2] - new[2])),
        ))

    transformed: list[list[GeneratorTerm3D]] = []
    for gen in generators:
        if not gen:
            transformed.append([])
            continue
        max_dx_old = max(t[1] for t in gen)
        max_dy_old = max(t[2] for t in gen)
        max_dz_old = max(t[3] for t in gen)
        new_gen: list[GeneratorTerm3D] = []
        for coeff, dx, dy, dz, s, p_type in gen:
            sx, sy, sz = shifts[s]
            new_gen.append((coeff, dx + sx - max_dx_old, dy + sy - max_dy_old, dz + sz - max_dz_old, s, p_type))
        transformed.append(new_gen)
    return transformed


__all__ = [
    "transform_sublattice_convention_2d",
    "transform_sublattice_convention_3d",
]
