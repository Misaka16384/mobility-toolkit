"""Finite-coordinate adapter for phase-aware generalized Pauli modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.pauli import LocalPauliTerm, PauliModule, PauliOperator
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteAbelianGroup


@dataclass(frozen=True)
class PauliAxis:
    site_id: str
    factor_index: int
    kind: str
    order: int

    SCHEMA_ID = "mobility_toolkit.pauli_axis.v1"

    def __post_init__(self) -> None:
        if self.kind not in {"x", "z"}:
            raise ValueError("Pauli axis kind must be 'x' or 'z'")
        if self.factor_index < 0 or self.order <= 1:
            raise ValueError("invalid Pauli axis factor")

    @property
    def label(self) -> str:
        return f"{self.site_id}:{self.kind}{self.factor_index}"

    def to_canonical_dict(self) -> dict:
        return {
            "factor_index": self.factor_index,
            "kind": self.kind,
            "order": self.order,
            "schema": self.SCHEMA_ID,
            "site_id": self.site_id,
        }


@dataclass(frozen=True)
class FinitePauliCoordinates:
    """Explicit adapter between semantic Paulis and an integer presentation.

    Axes are interleaved ``(x, z)`` per invariant-factor component.  This
    ordering is local to the finite backend and is never used as semantic
    identity.
    """

    module: PauliModule
    axes: Tuple[PauliAxis, ...]

    SCHEMA_ID = "mobility_toolkit.finite_pauli_coordinates.v1"

    def __post_init__(self) -> None:
        expected = self.from_module(self.module).axes
        if self.axes != expected:
            raise ValueError("Pauli coordinate axes are not canonical for the module")

    @classmethod
    def from_module(cls, module: PauliModule) -> "FinitePauliCoordinates":
        axes = []
        for system in module.local_systems:
            for factor_index, order in enumerate(system.invariant_factors):
                axes.append(PauliAxis(system.site_id, factor_index, "x", order))
                axes.append(PauliAxis(system.site_id, factor_index, "z", order))
        instance = object.__new__(cls)
        object.__setattr__(instance, "module", module)
        object.__setattr__(instance, "axes", tuple(axes))
        return instance

    @property
    def rank(self) -> int:
        return len(self.axes)

    @property
    def coordinate_orders(self) -> Tuple[int, ...]:
        return tuple(axis.order for axis in self.axes)

    def ambient_group(self, backend: FiniteIntegerBackend) -> FiniteAbelianGroup:
        return FiniteAbelianGroup.from_coordinate_orders(
            self.coordinate_orders,
            backend,
            tuple(axis.label for axis in self.axes),
        )

    def vector(self, operator: PauliOperator) -> Tuple[int, ...]:
        if operator.module != self.module:
            raise ValueError("Pauli operator belongs to a different module")
        terms = {term.site_id: term for term in operator.terms}
        values = []
        for axis in self.axes:
            term = terms.get(axis.site_id)
            if term is None:
                values.append(0)
            elif axis.kind == "x":
                values.append(term.x_exponents[axis.factor_index])
            else:
                values.append(term.z_exponents[axis.factor_index])
        return tuple(values)

    def operator(self, vector: Sequence[int], phase: int = 0) -> PauliOperator:
        vector = tuple(vector)
        if len(vector) != self.rank:
            raise ValueError("Pauli vector has the wrong coordinate rank")
        terms = []
        offset = 0
        for system in self.module.local_systems:
            x_values = []
            z_values = []
            for order in system.invariant_factors:
                x_values.append(vector[offset] % order)
                z_values.append(vector[offset + 1] % order)
                offset += 2
            if any(x_values) or any(z_values):
                terms.append(
                    LocalPauliTerm(
                        system.site_id,
                        tuple(x_values),
                        tuple(z_values),
                    )
                )
        return self.module.operator(terms, phase=phase)

    def generator_matrix(self, operators: Sequence[PauliOperator]) -> SparseIntMatrix:
        operators = tuple(operators)
        columns = tuple(self.vector(operator) for operator in operators)
        return SparseIntMatrix(
            self.rank,
            len(columns),
            tuple(
                (row, column, value)
                for column, values in enumerate(columns)
                for row, value in enumerate(values)
                if value
            ),
        )

    @property
    def pairing_matrix(self) -> SparseIntMatrix:
        modulus = self.module.phase_modulus
        entries = []
        for x_index in range(0, self.rank, 2):
            order = self.axes[x_index].order
            scale = modulus // order
            entries.append((x_index, x_index + 1, -scale))
            entries.append((x_index + 1, x_index, scale))
        return SparseIntMatrix(self.rank, self.rank, tuple(entries))

    def to_canonical_dict(self) -> dict:
        return {
            "axes": self.axes,
            "module": self.module,
            "pairing_matrix": self.pairing_matrix,
            "schema": self.SCHEMA_ID,
        }


__all__ = ["FinitePauliCoordinates", "PauliAxis"]
