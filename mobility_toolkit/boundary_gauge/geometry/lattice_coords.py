"""Lattice coordinate and qudit-list helpers."""

from __future__ import annotations

from mobility_toolkit.boundary_gauge.core.types import QuditCoord3D


def lattice_index_to_coordinate_2d(idx: int, Lx: int, Ly: int, q: int) -> tuple[int, int, int]:
    s = idx % q
    temp = idx // q
    x = temp % Lx
    y = temp // Lx
    return x, y, s


def lattice_coordinate_to_index_2d(x: int, y: int, s: int, Lx: int, Ly: int, q: int) -> int:
    return (y * Lx + x) * q + s


def generate_lattice_qudits_2d(Lx: int, Ly: int, q: int) -> list[tuple[int, int, int]]:
    qudits: list[tuple[int, int, int]] = []
    for y in range(Ly):
        for x in range(Lx):
            for s in range(q):
                qudits.append((x, y, s))
    return qudits


def generate_lattice_qudits_3d(Lx: int, Ly: int, Lz: int, q: int) -> list[QuditCoord3D]:
    qudits: list[QuditCoord3D] = []
    for z in range(Lz):
        for y in range(Ly):
            for x in range(Lx):
                for s in range(q):
                    qudits.append((x, y, z, s))
    return qudits


def lattice_index_to_coordinate_3d(idx: int, Lx: int, Ly: int, Lz: int, q: int) -> QuditCoord3D:
    s = idx % q
    temp = idx // q
    x = temp % Lx
    temp //= Lx
    y = temp % Ly
    z = temp // Ly
    return x, y, z, s


def lattice_coordinate_to_index_3d(
    x: int,
    y: int,
    z: int,
    s: int,
    Lx: int,
    Ly: int,
    Lz: int,
    q: int,
) -> int:
    return (((z * Ly + y) * Lx + x) * q) + s


__all__ = [
    "generate_lattice_qudits_2d",
    "generate_lattice_qudits_3d",
    "lattice_coordinate_to_index_2d",
    "lattice_coordinate_to_index_3d",
    "lattice_index_to_coordinate_2d",
    "lattice_index_to_coordinate_3d",
]
