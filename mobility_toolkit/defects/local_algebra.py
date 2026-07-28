"""Certified Pauli algebras supported in a finite defect window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteQuotient, FiniteSubgroup
from mobility_toolkit.finite.pairing import PairedFiniteAbelianGroup, PairedFiniteQuotient
from mobility_toolkit.finite.stabilizer import FiniteStabilizerAnalysis


@dataclass(frozen=True)
class DefectLocalAlgebra:
    """The paired quotient ``(C(S) intersect W) / (S intersect W)``.

    ``W`` is the projective Pauli subgroup supported on the selected sites.
    The construction is exact for the supplied finite system and window; it
    does not by itself assert thermodynamic stabilization.
    """

    window_site_ids: Tuple[str, ...]
    window_paulis: FiniteSubgroup
    local_centralizer: FiniteSubgroup
    local_stabilizer: FiniteSubgroup
    logical_algebra: PairedFiniteQuotient
    logical_radical: FiniteQuotient

    SCHEMA_ID = "mobility_toolkit.defect_local_algebra.v1"

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.logical_algebra.invariant_factors

    @property
    def order(self) -> int:
        return self.logical_algebra.order

    @property
    def radical_invariant_factors(self) -> Tuple[int, ...]:
        return self.logical_radical.invariant_factors

    def to_canonical_dict(self) -> dict:
        return {
            "invariant_factors": self.invariant_factors,
            "local_centralizer": self.local_centralizer,
            "local_stabilizer": self.local_stabilizer,
            "logical_algebra": self.logical_algebra,
            "order": self.order,
            "logical_radical": self.logical_radical,
            "radical_invariant_factors": self.radical_invariant_factors,
            "schema": self.SCHEMA_ID,
            "window_paulis": self.window_paulis,
            "window_site_ids": self.window_site_ids,
        }


def analyze_defect_local_algebra(
    analysis: FiniteStabilizerAnalysis,
    window: FiniteSubgroup,
    backend: FiniteIntegerBackend,
) -> DefectLocalAlgebra:
    """Analyze an arbitrary projective-Pauli window subgroup exactly."""

    if window.ambient != analysis.ambient_projective_paulis:
        raise ValueError("defect window belongs to a different Pauli ambient group")
    local_centralizer = analysis.centralizer.intersection(window, backend)
    local_stabilizer = analysis.stabilizer.intersection(window, backend)
    if not local_centralizer.contains_subgroup(local_stabilizer, backend):
        raise ArithmeticError("local stabilizers are not contained in the local centralizer")

    paired = PairedFiniteAbelianGroup.create(
        analysis.ambient_projective_paulis,
        analysis.module.phase_modulus,
        analysis.coordinates.pairing_matrix,
    )
    quotient = paired.quotient_pairing(
        local_centralizer,
        local_stabilizer,
        backend,
    )
    radical = paired.radical(local_centralizer, backend)
    logical_radical = radical.quotient_by(local_stabilizer, backend)
    return DefectLocalAlgebra(
        (),
        window,
        local_centralizer,
        local_stabilizer,
        quotient,
        logical_radical,
    )


def defect_local_algebra(
    analysis: FiniteStabilizerAnalysis,
    site_ids: Iterable[str],
    backend: FiniteIntegerBackend,
) -> DefectLocalAlgebra:
    """Compute the exact finite Pauli algebra localized to whole sites."""

    requested = tuple(sorted(set(site_ids)))
    known = {system.site_id for system in analysis.module.local_systems}
    unknown = tuple(site_id for site_id in requested if site_id not in known)
    if unknown:
        raise ValueError("unknown defect-window sites: " + ", ".join(unknown))

    selected_axes = tuple(
        index
        for index, axis in enumerate(analysis.coordinates.axes)
        if axis.site_id in requested
    )
    rank = analysis.ambient_projective_paulis.presentation_rank
    support_generators = SparseIntMatrix(
        rank,
        len(selected_axes),
        tuple((axis, column, 1) for column, axis in enumerate(selected_axes)),
    )
    window = analysis.ambient_projective_paulis.subgroup(support_generators, backend)
    result = analyze_defect_local_algebra(analysis, window, backend)
    return DefectLocalAlgebra(
        requested,
        result.window_paulis,
        result.local_centralizer,
        result.local_stabilizer,
        result.logical_algebra,
        result.logical_radical,
    )


__all__ = [
    "DefectLocalAlgebra",
    "analyze_defect_local_algebra",
    "defect_local_algebra",
]
