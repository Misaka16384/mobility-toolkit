"""Shared type aliases for stabilizer and qudit data."""

from __future__ import annotations

from typing import Dict, Tuple

GeneratorTerm2D = Tuple[int, int, int, int, int]
GeneratorTerm3D = Tuple[int, int, int, int, int, int]
QuditCoord3D = Tuple[int, int, int, int]
StabilizerDict = Dict[int, Tuple[int, int]]

__all__ = [
    "GeneratorTerm2D",
    "GeneratorTerm3D",
    "QuditCoord3D",
    "StabilizerDict",
]
