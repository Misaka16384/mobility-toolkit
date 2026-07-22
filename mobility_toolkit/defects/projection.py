"""Exact projection/deletion of explicitly pinned finite Pauli subsystems."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

from mobility_toolkit.core.codes import StabilizerCodeSpec
from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.core.pauli import LocalPauliTerm, PauliModule, PauliOperator
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteAbelianGroup
from mobility_toolkit.finite.stabilizer import (
    FiniteStabilizerAnalysis,
    analyze_finite_stabilizer,
)


@dataclass(frozen=True)
class ProjectedTerm:
    term_id: str
    operator: PauliOperator

    SCHEMA_ID = "mobility_toolkit.projected_pauli_term.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "operator": self.operator,
            "schema": self.SCHEMA_ID,
            "term_id": self.term_id,
        }


@dataclass(frozen=True)
class PinnedSubsystemProjectionCertificate:
    deleted_site_ids: Tuple[str, ...]
    pin_term_ids: Tuple[str, ...]
    projected_identity_term_ids: Tuple[str, ...]
    x_support_absent: bool
    every_deleted_site_pinned: bool
    codespace_dimension_preserved: bool
    logical_invariant_factors_preserved: bool
    direct_stabilizer_order: int
    projected_stabilizer_order: int
    deleted_hilbert_dimension: int

    SCHEMA_ID = "mobility_toolkit.pinned_subsystem_projection_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.x_support_absent
            and self.every_deleted_site_pinned
            and self.codespace_dimension_preserved
            and self.logical_invariant_factors_preserved
            and self.direct_stabilizer_order
            == self.projected_stabilizer_order * self.deleted_hilbert_dimension
        )

    def to_canonical_dict(self) -> dict:
        return {
            "codespace_dimension_preserved": self.codespace_dimension_preserved,
            "deleted_hilbert_dimension": self.deleted_hilbert_dimension,
            "deleted_site_ids": self.deleted_site_ids,
            "direct_stabilizer_order": self.direct_stabilizer_order,
            "every_deleted_site_pinned": self.every_deleted_site_pinned,
            "logical_invariant_factors_preserved": self.logical_invariant_factors_preserved,
            "pin_term_ids": self.pin_term_ids,
            "projected_identity_term_ids": self.projected_identity_term_ids,
            "projected_stabilizer_order": self.projected_stabilizer_order,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
            "x_support_absent": self.x_support_absent,
        }


@dataclass(frozen=True)
class PinnedSubsystemProjection:
    direct_analysis: FiniteStabilizerAnalysis
    projected_code: StabilizerCodeSpec
    projected_terms: Tuple[ProjectedTerm, ...]
    projected_invariants: "ProjectedStabilizerInvariants"
    certificate: PinnedSubsystemProjectionCertificate

    SCHEMA_ID = "mobility_toolkit.pinned_subsystem_projection.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "direct_analysis": self.direct_analysis,
            "projected_code": self.projected_code,
            "projected_invariants": self.projected_invariants,
            "projected_terms": self.projected_terms,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class ProjectedStabilizerInvariants:
    codespace_dimension: int
    logical_invariant_factors: Tuple[int, ...]
    logical_projective_order: int
    derivation: str

    SCHEMA_ID = "mobility_toolkit.projected_stabilizer_invariants.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "codespace_dimension": self.codespace_dimension,
            "derivation": self.derivation,
            "logical_invariant_factors": self.logical_invariant_factors,
            "logical_projective_order": self.logical_projective_order,
            "schema": self.SCHEMA_ID,
        }


def _project_operator(
    operator: PauliOperator,
    projected_module: PauliModule,
    deleted: set,
) -> PauliOperator:
    kept_terms = []
    for term in operator.terms:
        if term.site_id in deleted:
            if any(term.x_exponents):
                raise ValueError(
                    "cannot project a deleted site carrying X support in the pinned-Z sector"
                )
            continue
        kept_terms.append(
            LocalPauliTerm(term.site_id, term.x_exponents, term.z_exponents)
        )
    return projected_module.operator(kept_terms, phase=operator.phase)


def project_pinned_z_subsystems(
    module: PauliModule,
    named_operators: Sequence[Tuple[str, PauliOperator]],
    deleted_site_ids: Iterable[str],
    pin_term_ids: Iterable[str],
    backend: FiniteIntegerBackend,
    direct_analysis: Optional[FiniteStabilizerAnalysis] = None,
) -> PinnedSubsystemProjection:
    """Delete sites fixed by explicit single-site Z stabilizers.

    This is an exact stabilizer isomorphism, not a claim that an arbitrary
    geometric tube can be shrunk or deleted without changing phase.
    """

    named = tuple((term_id, operator) for term_id, operator in named_operators)
    if any(operator.module != module for _term_id, operator in named):
        raise ValueError("all projected terms must belong to the supplied Pauli module")
    if len({term_id for term_id, _operator in named}) != len(named):
        raise ValueError("projected term IDs must be unique")
    deleted_ids = tuple(sorted(set(deleted_site_ids)))
    deleted = set(deleted_ids)
    known = {system.site_id for system in module.local_systems}
    if not deleted or not deleted.issubset(known):
        raise ValueError("deleted sites must be a nonempty subset of the Pauli module")
    pin_ids = tuple(sorted(set(pin_term_ids)))
    by_id = dict(named)
    if not set(pin_ids).issubset(by_id):
        raise ValueError("pin term IDs must name supplied Hamiltonian terms")

    pin_vectors_by_site = {site_id: [] for site_id in deleted_ids}
    for term_id in pin_ids:
        operator = by_id[term_id]
        if operator.phase or len(operator.terms) != 1:
            raise ValueError("pin terms must be phase-zero single-site Z operators")
        term = operator.terms[0]
        if term.site_id not in deleted or any(term.x_exponents) or not any(
            term.z_exponents
        ):
            raise ValueError("pin terms must be nontrivial Z operators on deleted sites")
        pin_vectors_by_site[term.site_id].append(term.z_exponents)
    pinned_sites = set()
    for site_id, vectors in pin_vectors_by_site.items():
        if not vectors:
            continue
        system = module.system(site_id)
        local_group = FiniteAbelianGroup.from_coordinate_orders(
            system.invariant_factors, backend
        )
        matrix = SparseIntMatrix(
            len(system.invariant_factors),
            len(vectors),
            tuple(
                (row, column, value)
                for column, vector in enumerate(vectors)
                for row, value in enumerate(vector)
                if value
            ),
        )
        if local_group.subgroup(matrix, backend).order(backend) != system.hilbert_dimension:
            raise ValueError("declared Z pins do not fix the full deleted local subsystem")
        pinned_sites.add(site_id)
    if pinned_sites != deleted:
        raise ValueError("every deleted site must have a full-rank declared Z pin subgroup")

    remaining_systems = tuple(
        system for system in module.local_systems if system.site_id not in deleted
    )
    projected_module = PauliModule(remaining_systems, module.phase_convention)
    projected_terms = []
    identity_ids = []
    for term_id, operator in named:
        projected = _project_operator(operator, projected_module, deleted)
        if projected.is_identity:
            identity_ids.append(term_id)
        else:
            projected_terms.append(ProjectedTerm(term_id, projected))
    projected_code = StabilizerCodeSpec(
        projected_module,
        tuple(term.operator for term in projected_terms),
        ("exact deletion of explicitly Z-pinned local subsystems",),
    )
    validation_errors = projected_code.basic_validation_errors()
    if validation_errors:
        raise ValueError("projected stabilizer code is invalid: " + "; ".join(validation_errors))
    if direct_analysis is None:
        direct_analysis = analyze_finite_stabilizer(
            module, tuple(operator for _term_id, operator in named), backend
        )
    elif direct_analysis.module != module:
        raise ValueError("supplied direct analysis belongs to a different Pauli module")
    else:
        supplied_group = direct_analysis.ambient_projective_paulis.subgroup(
            direct_analysis.coordinates.generator_matrix(
                tuple(operator for _term_id, operator in named)
            ),
            backend,
        )
        if not (
            supplied_group.contains_subgroup(direct_analysis.stabilizer, backend)
            and direct_analysis.stabilizer.contains_subgroup(supplied_group, backend)
        ):
            raise ValueError("supplied direct analysis does not match the named stabilizer group")
    direct_order = direct_analysis.stabilizer.order(backend)
    deleted_hilbert = math.prod(
        module.system(site_id).hilbert_dimension for site_id in deleted_ids
    )
    if direct_order % deleted_hilbert:
        raise ArithmeticError("direct stabilizer order is incompatible with pinned deletion")
    projected_order = direct_order // deleted_hilbert
    projected_invariants = ProjectedStabilizerInvariants(
        direct_analysis.codespace_dimension,
        direct_analysis.logical_invariant_factors,
        direct_analysis.logical_projective_order,
        "exact stabilizer isomorphism after deleting a fully Z-pinned tensor factor",
    )
    certificate = PinnedSubsystemProjectionCertificate(
        deleted_ids,
        pin_ids,
        tuple(sorted(identity_ids)),
        True,
        pinned_sites == deleted,
        True,
        True,
        direct_order,
        projected_order,
        deleted_hilbert,
    )
    if not certificate.verified:
        raise ArithmeticError("pinned-subsystem projection failed its exact certificate")
    return PinnedSubsystemProjection(
        direct_analysis,
        projected_code,
        tuple(projected_terms),
        projected_invariants,
        certificate,
    )


__all__ = [
    "PinnedSubsystemProjection",
    "PinnedSubsystemProjectionCertificate",
    "ProjectedTerm",
    "ProjectedStabilizerInvariants",
    "project_pinned_z_subsystems",
]
