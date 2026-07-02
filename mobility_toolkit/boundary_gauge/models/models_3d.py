"""3D model definitions."""

from __future__ import annotations

from mobility_toolkit.boundary_gauge.core.types import GeneratorTerm3D
from mobility_toolkit.boundary_gauge.models.convention_transforms import transform_sublattice_convention_3d

POSITIONS_3D_EDGE_POSITIVE = [[0.5, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5]]
POSITIONS_3D_EDGE_NEGATIVE = [[-0.5, 0.0, 0.0], [0.0, -0.5, 0.0], [0.0, 0.0, -0.5]]
POSITIONS_HAAH_VERTEX_EXACT = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
POSITIONS_HAAH_VERTEX_SPLIT_X = [[-0.1, 0.0, 0.0], [0.1, 0.0, 0.0]]


def get_3d_toric_code_params() -> list[list[GeneratorTerm3D]]:
    star = [
        (1, 0, 0, 0, 0, 0),
        (1, -1, 0, 0, 0, 0),
        (1, 0, 0, 0, 1, 0),
        (1, 0, -1, 0, 1, 0),
        (1, 0, 0, 0, 2, 0),
        (1, 0, 0, -1, 2, 0),
    ]
    plaquette_xy = [
        (1, 0, 0, 0, 0, 1),
        (1, 1, 0, 0, 1, 1),
        (1, 0, 1, 0, 0, 1),
        (1, 0, 0, 0, 1, 1),
    ]
    plaquette_yz = [
        (1, 0, 0, 0, 1, 1),
        (1, 0, 1, 0, 2, 1),
        (1, 0, 0, 1, 1, 1),
        (1, 0, 0, 0, 2, 1),
    ]
    plaquette_zx = [
        (1, 0, 0, 0, 2, 1),
        (1, 0, 0, 1, 0, 1),
        (1, 1, 0, 0, 2, 1),
        (1, 0, 0, 0, 0, 1),
    ]
    return [star, plaquette_xy, plaquette_yz, plaquette_zx]


def get_xcube_code_params() -> list[list[GeneratorTerm3D]]:
    cross_xy = [
        (1, 0, 0, 0, 0, 1),
        (1, -1, 0, 0, 0, 1),
        (1, 0, 0, 0, 1, 1),
        (1, 0, -1, 0, 1, 1),
    ]
    cross_yz = [
        (1, 0, 0, 0, 1, 1),
        (1, 0, -1, 0, 1, 1),
        (1, 0, 0, 0, 2, 1),
        (1, 0, 0, -1, 2, 1),
    ]
    cross_zx = [
        (1, 0, 0, 0, 2, 1),
        (1, 0, 0, -1, 2, 1),
        (1, 0, 0, 0, 0, 1),
        (1, -1, 0, 0, 0, 1),
    ]
    cube = [
        (1, 0, 0, 0, 0, 0),
        (1, 0, 1, 0, 0, 0),
        (1, 0, 0, 1, 0, 0),
        (1, 0, 1, 1, 0, 0),
        (1, 0, 0, 0, 1, 0),
        (1, 1, 0, 0, 1, 0),
        (1, 0, 0, 1, 1, 0),
        (1, 1, 0, 1, 1, 0),
        (1, 0, 0, 0, 2, 0),
        (1, 1, 0, 0, 2, 0),
        (1, 0, 1, 0, 2, 0),
        (1, 1, 1, 0, 2, 0),
    ]
    return [cross_xy, cross_yz, cross_zx, cube]


def get_haah_cubic_code_params() -> list[list[GeneratorTerm3D]]:
    x_gen = [
        (1, 0, 0, 0, 0, 0),
        (1, 1, 1, 0, 0, 0),
        (1, 0, 1, 1, 0, 0),
        (1, 1, 0, 1, 0, 0),
        (1, 0, 0, 0, 1, 0),
        (1, 1, 0, 0, 1, 0),
        (1, 0, 1, 0, 1, 0),
        (1, 0, 0, 1, 1, 0),
    ]
    z_gen = [
        (1, 1, 1, 1, 0, 1),
        (1, 0, 1, 1, 0, 1),
        (1, 1, 0, 1, 0, 1),
        (1, 1, 1, 0, 0, 1),
        (1, 1, 1, 1, 1, 1),
        (1, 0, 0, 1, 1, 1),
        (1, 1, 0, 0, 1, 1),
        (1, 0, 1, 0, 1, 1),
    ]
    return [x_gen, z_gen]


def get_3d_toric_code_smooth_top_params() -> list[list[GeneratorTerm3D]]:
    return transform_sublattice_convention_3d(
        get_3d_toric_code_params(),
        POSITIONS_3D_EDGE_POSITIVE,
        POSITIONS_3D_EDGE_NEGATIVE,
    )


def get_xcube_code_smooth_top_params() -> list[list[GeneratorTerm3D]]:
    return transform_sublattice_convention_3d(
        get_xcube_code_params(),
        POSITIONS_3D_EDGE_POSITIVE,
        POSITIONS_3D_EDGE_NEGATIVE,
    )


__all__ = [
    "POSITIONS_3D_EDGE_NEGATIVE",
    "POSITIONS_3D_EDGE_POSITIVE",
    "POSITIONS_HAAH_VERTEX_EXACT",
    "POSITIONS_HAAH_VERTEX_SPLIT_X",
    "get_3d_toric_code_params",
    "get_3d_toric_code_smooth_top_params",
    "get_haah_cubic_code_params",
    "get_xcube_code_params",
    "get_xcube_code_smooth_top_params",
]
