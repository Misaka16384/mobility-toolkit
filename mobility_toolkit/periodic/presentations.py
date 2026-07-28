"""Quasi-free periodic Pauli-module presentations.

For mixed local dimensions the ambient module is not silently represented as
a free module over one coefficient ring.  Every projective Pauli coordinate
has an explicit local-order relation, and stabilizers enter as a structured
image map whose entries are canonical Laurent AST values.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

from mobility_toolkit.core.canonical import canonical_json
from mobility_toolkit.core.codes import PeriodicCode
from mobility_toolkit.core.laurent import LaurentPolynomial, TranslationGroup
from mobility_toolkit.periodic.laurent import GroupRingMonomial, render_m2_laurent


class PauliAxis(str, Enum):
    X = "X"
    Z = "Z"


@dataclass(frozen=True, order=True)
class PauliBasisElement:
    """One cyclic X or Z coordinate in a periodic unit cell."""

    axis: PauliAxis
    species_id: str
    component: int
    local_order: int

    SCHEMA_ID = "mobility_toolkit.periodic_pauli_basis_element.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.axis, PauliAxis):
            raise TypeError("axis must be a PauliAxis")
        if not isinstance(self.species_id, str) or not self.species_id:
            raise ValueError("species_id must be a nonempty string")
        if isinstance(self.component, bool) or not isinstance(self.component, int):
            raise TypeError("component must be an integer")
        if self.component < 0:
            raise ValueError("component must be nonnegative")
        if isinstance(self.local_order, bool) or not isinstance(self.local_order, int):
            raise TypeError("local_order must be an integer")
        if self.local_order <= 1:
            raise ValueError("local_order must be greater than one")

    @property
    def basis_id(self) -> str:
        return f"{self.axis.value}:{self.species_id}:{self.component}"

    def to_canonical_dict(self) -> dict:
        return {
            "axis": self.axis,
            "basis_id": self.basis_id,
            "component": self.component,
            "local_order": self.local_order,
            "schema": self.SCHEMA_ID,
            "species_id": self.species_id,
        }


@dataclass(frozen=True, order=True)
class LocalOrderRelation:
    """The relation ``order * basis_id = 0`` over the group ring."""

    basis_id: str
    order: int

    SCHEMA_ID = "mobility_toolkit.periodic_local_order_relation.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.basis_id, str) or not self.basis_id:
            raise ValueError("basis_id must be a nonempty string")
        if isinstance(self.order, bool) or not isinstance(self.order, int):
            raise TypeError("order must be an integer")
        if self.order <= 1:
            raise ValueError("order must be greater than one")

    def to_canonical_dict(self) -> dict:
        return {"basis_id": self.basis_id, "order": self.order, "schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class LaurentModuleElement:
    """A sparse column in a declared periodic Pauli presentation."""

    entries: Tuple[Tuple[str, LaurentPolynomial], ...] = ()

    SCHEMA_ID = "mobility_toolkit.laurent_module_element.v1"

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        if any(
            len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], LaurentPolynomial)
            for item in entries
        ):
            raise TypeError("entries must be (basis_id, LaurentPolynomial) pairs")
        if len({item[0] for item in entries}) != len(entries):
            raise ValueError("Laurent module basis IDs must be unique")
        rings = {
            (polynomial.coefficient_modulus, polynomial.translation_group)
            for _, polynomial in entries
        }
        if len(rings) > 1:
            raise ValueError("all entries must belong to the same group ring")
        object.__setattr__(
            self,
            "entries",
            tuple(sorted((basis_id, polynomial) for basis_id, polynomial in entries if not polynomial.is_zero)),
        )

    def coefficient(self, basis_id: str) -> Optional[LaurentPolynomial]:
        for candidate, polynomial in self.entries:
            if candidate == basis_id:
                return polynomial
        return None

    def to_canonical_dict(self) -> dict:
        return {"entries": self.entries, "schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class StabilizerImageColumn:
    generator_id: str
    phase: int
    image: LaurentModuleElement

    SCHEMA_ID = "mobility_toolkit.periodic_stabilizer_image_column.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.generator_id, str) or not self.generator_id:
            raise ValueError("generator_id must be a nonempty string")
        if isinstance(self.phase, bool) or not isinstance(self.phase, int):
            raise TypeError("phase must be an integer")
        if not isinstance(self.image, LaurentModuleElement):
            raise TypeError("image must be a LaurentModuleElement")

    def to_canonical_dict(self) -> dict:
        return {
            "generator_id": self.generator_id,
            "image": self.image,
            "phase": self.phase,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class StabilizerImage:
    columns: Tuple[StabilizerImageColumn, ...]

    SCHEMA_ID = "mobility_toolkit.periodic_stabilizer_image.v1"

    def __post_init__(self) -> None:
        columns = tuple(self.columns)
        if any(not isinstance(column, StabilizerImageColumn) for column in columns):
            raise TypeError("columns must be StabilizerImageColumn objects")
        if len({column.generator_id for column in columns}) != len(columns):
            raise ValueError("stabilizer generator IDs must be unique")
        object.__setattr__(self, "columns", tuple(sorted(columns, key=lambda item: item.generator_id)))

    def to_canonical_dict(self) -> dict:
        return {"columns": self.columns, "schema": self.SCHEMA_ID}


def _basis_sort_key(element: PauliBasisElement) -> tuple:
    return (0 if element.axis is PauliAxis.X else 1, element.species_id, element.component)


@dataclass(frozen=True)
class QuasiFreePauliModulePresentation:
    """A finite presentation of ``P_0[Lambda]`` and a stabilizer image."""

    translation_group: TranslationGroup
    coefficient_modulus: int
    basis: Tuple[PauliBasisElement, ...]
    local_order_relations: Tuple[LocalOrderRelation, ...]
    stabilizer_image: StabilizerImage
    phase_modulus: int

    SCHEMA_ID = "mobility_toolkit.quasi_free_pauli_module_presentation.v1"

    def __post_init__(self) -> None:
        if isinstance(self.coefficient_modulus, bool) or not isinstance(
            self.coefficient_modulus, int
        ):
            raise TypeError("coefficient_modulus must be an integer")
        if self.coefficient_modulus <= 1:
            raise ValueError("coefficient_modulus must be greater than one")
        if isinstance(self.phase_modulus, bool) or not isinstance(self.phase_modulus, int):
            raise TypeError("phase_modulus must be an integer")
        basis = tuple(sorted(tuple(self.basis), key=_basis_sort_key))
        if any(not isinstance(element, PauliBasisElement) for element in basis):
            raise TypeError("basis must contain PauliBasisElement objects")
        if len({element.basis_id for element in basis}) != len(basis):
            raise ValueError("Pauli basis IDs must be unique")
        relations = tuple(sorted(tuple(self.local_order_relations)))
        expected = tuple(
            sorted(LocalOrderRelation(element.basis_id, element.local_order) for element in basis)
        )
        if relations != expected:
            raise ValueError("local_order_relations must explicitly cover every Pauli basis element")
        basis_ids = {element.basis_id for element in basis}
        for column in self.stabilizer_image.columns:
            for basis_id, polynomial in column.image.entries:
                if basis_id not in basis_ids:
                    raise ValueError(f"stabilizer image uses unknown basis ID: {basis_id}")
                if polynomial.translation_group != self.translation_group:
                    raise ValueError("stabilizer coefficient uses a different translation group")
                if polynomial.coefficient_modulus != self.coefficient_modulus:
                    raise ValueError("stabilizer coefficient uses a different coefficient modulus")
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "local_order_relations", relations)

    @classmethod
    def from_periodic_code(cls, code: PeriodicCode) -> "QuasiFreePauliModulePresentation":
        if not isinstance(code, PeriodicCode):
            raise TypeError("code must be a PeriodicCode")
        orders = tuple(
            factor for species in code.species for factor in species.invariant_factors
        )
        coefficient_modulus = math.lcm(*orders)
        basis = []
        for axis in (PauliAxis.X, PauliAxis.Z):
            for species in code.species:
                for component, order in enumerate(species.invariant_factors):
                    basis.append(
                        PauliBasisElement(axis, species.site_id, component, order)
                    )
        basis_lookup = {
            (element.axis, element.species_id, element.component): element.basis_id
            for element in basis
        }
        columns = []
        for template in code.stabilizer_templates:
            accumulated: Dict[str, LaurentPolynomial] = {}
            for term in template.terms:
                monomial = GroupRingMonomial(
                    code.translation_group,
                    term.free_offset,
                    term.torsion_offset,
                )
                for axis, exponents in (
                    (PauliAxis.X, term.x_exponents),
                    (PauliAxis.Z, term.z_exponents),
                ):
                    for component, exponent in enumerate(exponents):
                        if not exponent:
                            continue
                        basis_id = basis_lookup[(axis, term.species_id, component)]
                        polynomial = monomial.as_polynomial(coefficient_modulus, exponent)
                        previous = accumulated.get(basis_id)
                        accumulated[basis_id] = polynomial if previous is None else previous + polynomial
            image = LaurentModuleElement(tuple(accumulated.items()))
            digest = hashlib.sha256(canonical_json(template).encode("utf-8")).hexdigest()[:20]
            columns.append(
                StabilizerImageColumn(
                    generator_id=f"stabilizer:{digest}",
                    phase=template.phase % code.unit_cell_pauli_module.phase_modulus,
                    image=image,
                )
            )
        return cls(
            translation_group=code.translation_group,
            coefficient_modulus=coefficient_modulus,
            basis=tuple(basis),
            local_order_relations=tuple(
                LocalOrderRelation(element.basis_id, element.local_order) for element in basis
            ),
            stabilizer_image=StabilizerImage(tuple(columns)),
            phase_modulus=code.unit_cell_pauli_module.phase_modulus,
        )

    @property
    def local_orders(self) -> Tuple[int, ...]:
        return tuple(element.local_order for element in self.basis)

    @property
    def distinct_local_orders(self) -> Tuple[int, ...]:
        return tuple(sorted(set(self.local_orders)))

    @property
    def is_uniform(self) -> bool:
        return len(self.distinct_local_orders) == 1

    def to_legacy_generator_rows(self) -> Tuple[Tuple[str, ...], ...]:
        """Render structured columns for the existing uniform-prime path."""

        if not self.is_uniform:
            raise ValueError("legacy homology adapter requires a uniform local order")
        rows = []
        for column in self.stabilizer_image.columns:
            entries = []
            for element in self.basis:
                polynomial = column.image.coefficient(element.basis_id)
                if polynomial is None:
                    polynomial = LaurentPolynomial.zero(
                        self.coefficient_modulus, self.translation_group
                    )
                entries.append(render_m2_laurent(polynomial))
            rows.append(tuple(entries))
        return tuple(rows)

    def to_canonical_dict(self) -> dict:
        return {
            "basis": self.basis,
            "coefficient_modulus": self.coefficient_modulus,
            "local_order_relations": self.local_order_relations,
            "phase_modulus": self.phase_modulus,
            "schema": self.SCHEMA_ID,
            "stabilizer_image": self.stabilizer_image,
            "translation_group": self.translation_group,
        }


__all__ = [
    "LaurentModuleElement",
    "LocalOrderRelation",
    "PauliAxis",
    "PauliBasisElement",
    "QuasiFreePauliModulePresentation",
    "StabilizerImage",
    "StabilizerImageColumn",
]
