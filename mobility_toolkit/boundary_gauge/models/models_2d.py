"""2D model definitions."""

from __future__ import annotations

from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm2D
from mobility_toolkit.boundary_gauge.models.convention_transforms import transform_sublattice_convention_2d

POSITIONS_2D_EDGE_POSITIVE = [[0.5, 0.0], [0.0, 0.5]]
POSITIONS_2D_EDGE_NEGATIVE = [[-0.5, 0.0], [0.0, -0.5]]


def get_toric_code_params() -> list[list[GeneratorTerm2D]]:
    star = [
        (1, 0, 0, 0, 0),
        (1, 0, 0, 1, 0),
        (1, -1, 0, 0, 0),
        (1, 0, -1, 1, 0),
    ]
    plaquette = [
        (1, 0, 0, 0, 1),
        (1, 1, 0, 1, 1),
        (1, 0, 1, 0, 1),
        (1, 0, 0, 1, 1),
    ]
    return [star, plaquette]


def get_color_code_params() -> list[list[GeneratorTerm2D]]:
    return []


def get_fish_toric_code_params() -> list[list[GeneratorTerm2D]]:
    fish_Av = [
        (1, 0, 0, 0, 0),
        (1, -1, 0, 0, 0),
        (1, 0, 0, 1, 0),
        (1, 0, -1, 1, 0),
        (1, 1, -2, 1, 0),
        (1, -1, -2, 1, 0),
    ]
    fish_Bp = [
        (1, 0, 0, 0, 1),
        (1, 0, 1, 0, 1),
        (1, 0, 0, 1, 1),
        (1, 1, 0, 1, 1),
        (1, 1, 2, 0, 1),
        (1, -1, 2, 0, 1),
    ]
    return [fish_Av, fish_Bp]


def get_Z4_toric_code_params() -> list[list[GeneratorTerm2D]]:
    star = [
        (1, 0, 0, 0, 0),
        (3, 0, 0, 1, 0),
        (3, -1, 0, 0, 0),
        (1, 0, -1, 1, 0),
    ]
    plaquette = [
        (1, 0, 0, 0, 1),
        (3, 1, 0, 1, 1),
        (3, 0, 1, 0, 1),
        (1, 0, 0, 1, 1),
    ]
    return [star, plaquette]


def get_Z4_double_semion_params() -> list[list[GeneratorTerm2D]]:
    gen_1 = [
        (2, 0, 0, 0, 1),
        (2, 0, 0, 1, 1),
        (2, 1, 0, 1, 1),
        (2, 0, 1, 0, 1),
    ]
    gen_2 = [
        (2, 0, 0, 0, 0),
        (2, 0, 0, 1, 1),
    ]
    gen_3 = [
        (2, 0, 0, 1, 0),
        (2, -1, 1, 0, 1),
    ]
    gen_4 = [
        (1, 0, 0, 0, 1),
        (1, 0, 0, 1, 1),
        (3, 1, 0, 1, 1),
        (3, 0, 1, 0, 1),
        (3, 0, 0, 1, 0),
        (3, 0, 1, 0, 0),
        (1, 0, 1, 1, 0),
        (1, -1, 1, 0, 0),
    ]
    return [gen_1, gen_2, gen_3, gen_4]


def get_toric_code_smooth_top_params() -> list[list[GeneratorTerm2D]]:
    star = [
        (1, 0, 0, 0, 0),
        (1, 0, 0, 1, 0),
        (1, 1, 0, 0, 0),
        (1, 0, 1, 1, 0),
    ]
    plaquette = [
        (1, 0, 0, 0, 1),
        (1, 0, 0, 1, 1),
        (1, 0, -1, 0, 1),
        (1, -1, 0, 1, 1),
    ]
    return [star, plaquette]


def get_fish_toric_code_smooth_top_params() -> list[list[GeneratorTerm2D]]:
    return transform_sublattice_convention_2d(
        get_fish_toric_code_params(),
        POSITIONS_2D_EDGE_POSITIVE,
        POSITIONS_2D_EDGE_NEGATIVE,
    )


def get_Z4_toric_code_smooth_top_params() -> list[list[GeneratorTerm2D]]:
    return transform_sublattice_convention_2d(
        get_Z4_toric_code_params(),
        POSITIONS_2D_EDGE_POSITIVE,
        POSITIONS_2D_EDGE_NEGATIVE,
    )


def get_Z4_double_semion_smooth_top_params() -> list[list[GeneratorTerm2D]]:
    return transform_sublattice_convention_2d(
        get_Z4_double_semion_params(),
        POSITIONS_2D_EDGE_POSITIVE,
        POSITIONS_2D_EDGE_NEGATIVE,
    )


__all__ = [
    "POSITIONS_2D_EDGE_NEGATIVE",
    "POSITIONS_2D_EDGE_POSITIVE",
    "get_Z4_double_semion_params",
    "get_Z4_double_semion_smooth_top_params",
    "get_Z4_toric_code_params",
    "get_Z4_toric_code_smooth_top_params",
    "get_color_code_params",
    "get_fish_toric_code_params",
    "get_fish_toric_code_smooth_top_params",
    "get_toric_code_params",
    "get_toric_code_smooth_top_params",
]
