"""Canonical two-dimensional literature models and exact Clifford relations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from mobility_toolkit.core import (
    Exactness,
    LocalSystem,
    OperatorTemplate,
    OperatorTerm,
    PeriodicCode,
    TranslationGroup,
)
from mobility_toolkit.models.periodic_3d import LiteraturePeriodicModel


FISH_TORIC_SOURCE = (
    "Liang--Yang--Iosue--Chen, Operator algebra and algorithmic construction "
    "of boundaries and defects in (2+1)D topological Pauli stabilizer codes, "
    "arXiv:2410.11942v5"
)


def _term(offset, species, *, x=0, z=0):
    return OperatorTerm.cyclic(offset, species, x=x, z=z)


def z2_standard_toric_model() -> LiteraturePeriodicModel:
    """Return the oriented square-lattice ``Z_2`` toric differential."""

    species = (
        LocalSystem.cyclic("h", 2),
        LocalSystem.cyclic("v", 2),
    )
    star = OperatorTemplate(
        0,
        (
            _term((-1, 0), "h", x=1),
            _term((0, 0), "h", x=1),
            _term((0, -1), "v", x=1),
            _term((0, 0), "v", x=1),
        ),
    )
    plaquette = OperatorTemplate(
        0,
        (
            _term((0, 0), "h", z=1),
            _term((0, 1), "h", z=1),
            _term((0, 0), "v", z=1),
            _term((1, 0), "v", z=1),
        ),
    )
    return LiteraturePeriodicModel(
        "z2_standard_toric_cellular_2d",
        PeriodicCode(
            TranslationGroup(2),
            species,
            (star, plaquette),
            (
                "qubits lie on horizontal and vertical square-lattice edges",
                "star is the cellular coboundary and plaquette is the cellular boundary",
            ),
        ),
        "Bravyi--Kitaev, Quantum codes on a lattice with boundary, quant-ph/9811052",
        ("square-lattice vertex and plaquette checks",),
        "canonical bulk differential; no microscopic fish-boundary conclusion",
    )


def z2_fish_toric_model() -> LiteraturePeriodicModel:
    """Return the source-locked fish-toric bulk presentation.

    The six-term supports are transcribed into canonical ``OperatorTemplate``
    objects from Eqs. (12)--(13) and Fig. 4(a) of the source.  They are not
    imported from the legacy ``GeneratorTerm`` boundary-gauge fixtures.
    """

    species = (
        LocalSystem.cyclic("h", 2),
        LocalSystem.cyclic("v", 2),
    )
    fish_star = OperatorTemplate(
        0,
        (
            _term((-1, 0), "h", x=1),
            _term((0, 0), "h", x=1),
            _term((0, -1), "v", x=1),
            _term((0, 0), "v", x=1),
            _term((-1, -2), "v", x=1),
            _term((1, -2), "v", x=1),
        ),
    )
    fish_plaquette = OperatorTemplate(
        0,
        (
            _term((0, 0), "h", z=1),
            _term((0, 1), "h", z=1),
            _term((-1, 2), "h", z=1),
            _term((1, 2), "h", z=1),
            _term((0, 0), "v", z=1),
            _term((1, 0), "v", z=1),
        ),
    )
    return LiteraturePeriodicModel(
        "z2_fish_toric_liang_eq13",
        PeriodicCode(
            TranslationGroup(2),
            species,
            (fish_star, fish_plaquette),
            (
                "h/v label the two square-lattice edge qubits per cell",
                "the displayed six-term checks use the Fig. 4 lattice convention",
            ),
        ),
        FISH_TORIC_SOURCE,
        ("Eqs. (12)--(13)", "Fig. 4(a)", "Sec. 5.2"),
        (
            "bulk fish presentation and the paper's stated finite-depth-Clifford "
            "equivalence; Fig. 4 further states that its displayed smooth cut has "
            "nontrivial secondary boundary gauge operators"
        ),
    )


def apply_fish_cnot_shear(code: PeriodicCode) -> PeriodicCode:
    """Apply the exact two-monomial CNOT shear used by the fish presentation.

    For the two qubit species ``h`` and ``v``, the shear has X-block

    ``U = [[1, 0], [y^-2 (1+x), 1]]``.

    Equivalently, every ``X_h(a)`` gains ``X_v(a+s)`` and every ``Z_v(a)``
    gains ``Z_h(a-s)`` for ``s=(0,-2),(1,-2)``.  These are two
    translation-invariant CNOT gate families with ``h`` controls and ``v``
    targets.  The inverse-antipode action on Z is included explicitly.
    """

    if code.translation_group != TranslationGroup(2):
        raise ValueError("fish CNOT shear requires a rank-two translation group")
    species = {item.site_id: item for item in code.species}
    if set(species) != {"h", "v"} or any(
        item.invariant_factors != (2,) for item in species.values()
    ):
        raise ValueError("fish CNOT shear requires qubit species h and v")
    gate_offsets = ((0, -2), (1, -2))
    transformed = []
    for template in code.stabilizer_templates:
        terms = list(template.terms)
        for term in template.terms:
            x = term.x_exponents[0] % 2
            z = term.z_exponents[0] % 2
            if x and z:
                raise ValueError("targeted fish shear accepts CSS templates only")
            if term.species_id == "h" and x:
                for shift in gate_offsets:
                    terms.append(
                        _term(
                            tuple(a + b for a, b in zip(term.free_offset, shift)),
                            "v",
                            x=1,
                        )
                    )
            if term.species_id == "v" and z:
                for shift in gate_offsets:
                    terms.append(
                        _term(
                            tuple(a - b for a, b in zip(term.free_offset, shift)),
                            "h",
                            z=1,
                        )
                    )
        transformed.append(OperatorTemplate(template.phase, tuple(terms)))
    return PeriodicCode(
        code.translation_group,
        code.species,
        tuple(transformed),
        code.assumptions
        + (
            "conjugated by the two-monomial translation-invariant h-to-v CNOT shear",
        ),
    )


@dataclass(frozen=True)
class FishToricCliffordEquivalence:
    """Replayable source-to-canonical differential comparison."""

    standard: LiteraturePeriodicModel
    transformed_standard: PeriodicCode
    source_fish: LiteraturePeriodicModel
    cnot_gate_offsets: Tuple[Tuple[int, int], ...] = ((0, -2), (1, -2))
    exactness: Exactness = Exactness.CERTIFIED_EXACT
    theorem_scope: str = (
        "exact equality of the two infinite periodic stabilizer templates under "
        "the recorded CNOT shear; this does not identify arbitrary finite cuts "
        "without also transforming their boundary Hamiltonian"
    )

    SCHEMA_ID = "mobility_toolkit.fish_toric_clifford_equivalence.v1"

    @property
    def verified(self) -> bool:
        return (
            self.transformed_standard.stabilizer_templates
            == self.source_fish.code.stabilizer_templates
        )

    def to_canonical_dict(self) -> dict:
        return {
            "cnot_gate_offsets": self.cnot_gate_offsets,
            "exactness": self.exactness,
            "schema": self.SCHEMA_ID,
            "source_fish": self.source_fish,
            "standard": self.standard,
            "theorem_scope": self.theorem_scope,
            "transformed_standard": self.transformed_standard,
            "verified": self.verified,
        }


def z2_fish_toric_clifford_equivalence() -> FishToricCliffordEquivalence:
    standard = z2_standard_toric_model()
    fish = z2_fish_toric_model()
    return FishToricCliffordEquivalence(
        standard,
        apply_fish_cnot_shear(standard.code),
        fish,
    )


__all__ = [
    "FISH_TORIC_SOURCE",
    "FishToricCliffordEquivalence",
    "apply_fish_cnot_shear",
    "z2_fish_toric_clifford_equivalence",
    "z2_fish_toric_model",
    "z2_standard_toric_model",
]
