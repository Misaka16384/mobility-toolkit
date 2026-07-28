"""Canonical three-dimensional stabilizer models from independent formulas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mobility_toolkit.core import (
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
)


@dataclass(frozen=True)
class LiteraturePeriodicModel:
    model_id: str
    code: PeriodicCode
    source: str
    source_equations: Tuple[str, ...]
    theorem_scope: str

    SCHEMA_ID = "mobility_toolkit.literature_periodic_model.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id:
            raise ValueError("model_id must be a nonempty string")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source must be a nonempty string")
        equations = tuple(self.source_equations)
        if not equations or any(not isinstance(item, str) or not item for item in equations):
            raise ValueError("source_equations must be nonempty strings")
        if not isinstance(self.theorem_scope, str) or not self.theorem_scope:
            raise ValueError("theorem_scope must be a nonempty string")
        object.__setattr__(self, "source_equations", equations)

    def to_canonical_dict(self) -> dict:
        return {
            "code": self.code,
            "model_id": self.model_id,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "source_equations": self.source_equations,
            "theorem_scope": self.theorem_scope,
        }


def _term(offset, species, *, x=0, z=0):
    return OperatorTerm.cyclic(offset, species, x=x, z=z)


def z2_xcube_model() -> LiteraturePeriodicModel:
    """X-cube stabilizer map in Ruba--Yang Eq. (140)."""

    group = TranslationGroup(3)
    species = tuple(
        LocalSystem.cyclic(label, 2) for label in ("edge_x", "edge_y", "edge_z")
    )
    cube_x = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_x", x=1),
            _term((-1, 0, 0), "edge_x", x=1),
            _term((0, -1, 0), "edge_x", x=1),
            _term((-1, -1, 0), "edge_x", x=1),
            _term((0, 0, 0), "edge_y", x=1),
            _term((0, -1, 0), "edge_y", x=1),
            _term((0, 0, -1), "edge_y", x=1),
            _term((0, -1, -1), "edge_y", x=1),
            _term((0, 0, 0), "edge_z", x=1),
            _term((-1, 0, 0), "edge_z", x=1),
            _term((0, 0, -1), "edge_z", x=1),
            _term((-1, 0, -1), "edge_z", x=1),
        ),
    )
    cross_zx = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_x", z=1),
            _term((0, 0, 1), "edge_x", z=1),
            _term((0, 0, 0), "edge_y", z=1),
            _term((1, 0, 0), "edge_y", z=1),
        ),
    )
    cross_zy = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_y", z=1),
            _term((1, 0, 0), "edge_y", z=1),
            _term((0, 0, 0), "edge_z", z=1),
            _term((0, 1, 0), "edge_z", z=1),
        ),
    )
    code = PeriodicCode(
        group,
        species,
        (cube_x, cross_zx, cross_zy),
        (
            "basis order is X(edge_x,edge_y,edge_z), then Z(edge_x,edge_y,edge_z)",
            "Laurent monomials translate the displayed unit-cell operator",
        ),
    )
    return LiteraturePeriodicModel(
        "z2_xcube_ruba_yang_eq140",
        code,
        "Ruba--Yang, Witt Groups and Bulk-Boundary Correspondence, arXiv:2509.10418",
        ("Eq. (140)", "Example 54", "Eq. (144)"),
        (
            "canonical X-cube bulk presentation; axial versus (1,1,1) half-space "
            "boundary-to-bulk behavior is a separate symbolic computation"
        ),
    )


def z2_haah_cubic_code_a_model() -> LiteraturePeriodicModel:
    """Haah code A from its two eight-corner cube stabilizers."""

    group = TranslationGroup(3)
    species = (
        LocalSystem.cyclic("sigma", 2),
        LocalSystem.cyclic("mu", 2),
    )
    x_stabilizer = OperatorTemplate(
        0,
        tuple(
            _term(offset, "sigma", x=1)
            for offset in ((0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0))
        )
        + tuple(
            _term(offset, "mu", x=1)
            for offset in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        ),
    )
    z_stabilizer = OperatorTemplate(
        0,
        tuple(
            _term(offset, "sigma", z=1)
            for offset in ((1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0))
        )
        + tuple(
            _term(offset, "mu", z=1)
            for offset in ((1, 1, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        ),
    )
    code = PeriodicCode(
        group,
        species,
        (x_stabilizer, z_stabilizer),
        (
            "two qubits sigma and mu per cubic-lattice vertex",
            "cube-corner convention p=000, q_i=100/010/001, "
            "r_i=011/101/110, s=111",
        ),
    )
    return LiteraturePeriodicModel(
        "z2_haah_cubic_code_a",
        code,
        "Haah, Local stabilizer codes in three dimensions without string logical operators, arXiv:1101.1962",
        ("Code 1 / cubic code A local cube stabilizers",),
        (
            "canonical local stabilizer presentation only; no finite support bound "
            "is promoted to a general boundary or no-string theorem"
        ),
    )


def zd_3d_toric_model(dimension: int) -> LiteraturePeriodicModel:
    """Oriented cellular 3D ``Z_d`` toric code with qudits on edges."""

    if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 1:
        raise ValueError("dimension must be an integer greater than one")
    group = TranslationGroup(3)
    species = tuple(
        LocalSystem.cyclic(label, dimension)
        for label in ("edge_x", "edge_y", "edge_z")
    )
    star_terms = []
    for axis, label in enumerate(("edge_x", "edge_y", "edge_z")):
        negative = tuple(-1 if index == axis else 0 for index in range(3))
        star_terms.extend(
            (_term((0, 0, 0), label, x=-1), _term(negative, label, x=1))
        )
    plaquette_xy = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_x", z=1),
            _term((0, 1, 0), "edge_x", z=-1),
            _term((0, 0, 0), "edge_y", z=-1),
            _term((1, 0, 0), "edge_y", z=1),
        ),
    )
    plaquette_xz = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_x", z=1),
            _term((0, 0, 1), "edge_x", z=-1),
            _term((0, 0, 0), "edge_z", z=-1),
            _term((1, 0, 0), "edge_z", z=1),
        ),
    )
    plaquette_yz = OperatorTemplate(
        0,
        (
            _term((0, 0, 0), "edge_y", z=1),
            _term((0, 0, 1), "edge_y", z=-1),
            _term((0, 0, 0), "edge_z", z=-1),
            _term((0, 1, 0), "edge_z", z=1),
        ),
    )
    code = PeriodicCode(
        group,
        species,
        (
            OperatorTemplate(0, tuple(star_terms)),
            plaquette_xy,
            plaquette_xz,
            plaquette_yz,
        ),
        (
            "oriented cellular Z_d toric code",
            "qudits lie on positively oriented cubic-lattice edges",
        ),
    )
    return LiteraturePeriodicModel(
        f"z{dimension}_3d_toric_cellular",
        code,
        "standard cellular 3D toric code from boundary and coboundary maps",
        ("vertex coboundary X check", "square boundary Z checks"),
        "bulk periodic code; boundary conditions are not included",
    )


__all__ = [
    "LiteraturePeriodicModel",
    "z2_haah_cubic_code_a_model",
    "z2_xcube_model",
    "zd_3d_toric_model",
]
