"""Explicit, phase-aware compilation of finite primary boundary images.

Primary operators are not inferred from a support-minimization heuristic.  A
caller supplies an exact parent stabilizer presentation and identifies cut
stabilizers together with their projected operators.  If support is dropped,
the dropped sites must be declared exactly and the projected phase must agree
with literal tensor-factor restriction.

There are two separate claims:

* every supplied projection is checked exactly; and
* the supplied projected subgroup is the complete primary image, modulo
  retained bulk-trivial operators.

The second claim is certified only when the literal restrictions of every
generator in the declared parent presentation are covered.  An incomplete
list remains a useful, exactly checked subgroup, but is never passed to the
primary/secondary classifier as though it were the complete primary image.

Current ``geometry.FiniteCode`` provenance records missing addresses but does
not retain a common ambient Pauli module containing the missing sites and the
uncut source operator.  It is therefore insufficient, by itself, for this
phase-aware compiler; callers must reconstruct and supply those source
operators explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence, Tuple

from mobility_toolkit.boundary.algebra import (
    FiniteBoundaryAlgebra,
    SupportWindow,
    TangentTranslationSpec,
    analyze_finite_boundary_algebra,
)
from mobility_toolkit.core import Exactness, PauliOperator
from mobility_toolkit.finite import (
    FiniteIntegerBackend,
    FiniteStabilizerAnalysis,
    FiniteSubgroup,
    StabilizerValidation,
    analyze_finite_stabilizer,
    validate_stabilizer_generators,
)


class ProjectionPolicy(str, Enum):
    REQUIRE_FULL_SUPPORT = "require_full_support"
    EXPLICIT_SITE_RESTRICTION = "explicit_site_restriction"


@dataclass(frozen=True)
class CutStabilizerProjection:
    projection_id: str
    source_operator: PauliOperator
    projected_operator: PauliOperator
    policy: ProjectionPolicy
    declared_dropped_site_ids: Tuple[str, ...] = ()

    SCHEMA_ID = "mobility_toolkit.cut_stabilizer_projection.v1"

    def __post_init__(self) -> None:
        if not self.projection_id:
            raise ValueError("projection_id must be nonempty")
        if not isinstance(self.policy, ProjectionPolicy):
            raise TypeError("projection policy must be explicit")
        dropped = tuple(sorted(set(self.declared_dropped_site_ids)))
        if len(dropped) != len(self.declared_dropped_site_ids):
            raise ValueError("declared dropped site IDs must be unique and canonical")
        object.__setattr__(self, "declared_dropped_site_ids", dropped)

    def to_canonical_dict(self) -> dict:
        return {
            "declared_dropped_site_ids": self.declared_dropped_site_ids,
            "policy": self.policy,
            "projected_operator": self.projected_operator,
            "projection_id": self.projection_id,
            "schema": self.SCHEMA_ID,
            "source_operator": self.source_operator,
        }


@dataclass(frozen=True)
class PrimaryProjectionRecord:
    projection_id: str
    source_operator: PauliOperator
    projected_operator: PauliOperator
    dropped_site_ids: Tuple[str, ...]
    policy: ProjectionPolicy
    source_phase_membership_verified: bool
    literal_restriction_verified: bool

    SCHEMA_ID = "mobility_toolkit.primary_projection_record.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "dropped_site_ids": self.dropped_site_ids,
            "literal_restriction_verified": self.literal_restriction_verified,
            "policy": self.policy,
            "projected_operator": self.projected_operator,
            "projection_id": self.projection_id,
            "schema": self.SCHEMA_ID,
            "source_operator": self.source_operator,
            "source_phase_membership_verified": self.source_phase_membership_verified,
        }


@dataclass(frozen=True)
class PrimaryCoverageRecord:
    """Coverage of one declared parent generator after literal restriction."""

    source_generator_index: int
    source_operator: PauliOperator
    literal_restriction: PauliOperator
    restriction_is_identity: bool
    restriction_is_projective_identity: bool
    centralizer_membership_verified: bool
    covered_by_supplied_projected_subgroup: bool
    covered_by_bulk_trivial: bool
    covered_modulo_bulk_trivial: bool

    SCHEMA_ID = "mobility_toolkit.primary_coverage_record.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "centralizer_membership_verified": self.centralizer_membership_verified,
            "covered_by_bulk_trivial": self.covered_by_bulk_trivial,
            "covered_by_supplied_projected_subgroup": (
                self.covered_by_supplied_projected_subgroup
            ),
            "covered_modulo_bulk_trivial": self.covered_modulo_bulk_trivial,
            "literal_restriction": self.literal_restriction,
            "restriction_is_identity": self.restriction_is_identity,
            "restriction_is_projective_identity": (
                self.restriction_is_projective_identity
            ),
            "schema": self.SCHEMA_ID,
            "source_generator_index": self.source_generator_index,
            "source_operator": self.source_operator,
        }


@dataclass(frozen=True)
class PrimaryImageCompilationCertificate:
    source_validation: StabilizerValidation
    records: Tuple[PrimaryProjectionRecord, ...]
    coverage_records: Tuple[PrimaryCoverageRecord, ...]
    coverage_complete: bool
    source_generator_count: int
    projected_generator_count: int
    exactness: Exactness
    supplied_projected_subgroup_exactness: Exactness = Exactness.BOUNDED_EXACT
    theorem_scope: str = (
        "literal, phase-aware verification of the supplied finite projections; "
        "completeness means that every generator of the declared parent "
        "presentation is covered after restriction, modulo retained "
        "bulk-trivial operators"
    )

    SCHEMA_ID = "mobility_toolkit.primary_image_compilation_certificate.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "coverage_complete": self.coverage_complete,
            "coverage_records": self.coverage_records,
            "exactness": self.exactness,
            "projected_generator_count": self.projected_generator_count,
            "records": self.records,
            "schema": self.SCHEMA_ID,
            "source_generator_count": self.source_generator_count,
            "source_validation": self.source_validation,
            "supplied_projected_subgroup_exactness": (
                self.supplied_projected_subgroup_exactness
            ),
            "theorem_scope": self.theorem_scope,
        }


@dataclass(frozen=True)
class CompiledPrimaryImage:
    image: FiniteSubgroup
    projected_operators: Tuple[PauliOperator, ...]
    certificate: PrimaryImageCompilationCertificate
    source_description: str

    SCHEMA_ID = "mobility_toolkit.compiled_primary_image.v1"

    def __post_init__(self) -> None:
        if not self.source_description:
            raise ValueError("source_description must be nonempty")

    @property
    def supplied_projected_subgroup(self) -> FiniteSubgroup:
        """The exactly checked subgroup generated by supplied projections."""

        return self.image

    @property
    def coverage_complete(self) -> bool:
        return self.certificate.coverage_complete

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "image": self.image,
            "projected_operators": self.projected_operators,
            "schema": self.SCHEMA_ID,
            "source_description": self.source_description,
        }


@dataclass(frozen=True)
class CompiledFiniteBoundaryAlgebra:
    compilation: CompiledPrimaryImage
    algebra: FiniteBoundaryAlgebra

    SCHEMA_ID = "mobility_toolkit.compiled_finite_boundary_algebra.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "algebra": self.algebra,
            "compilation": self.compilation,
            "schema": self.SCHEMA_ID,
        }


def _literal_site_restriction(
    operator: PauliOperator, retained_site_ids: Tuple[str, ...]
) -> PauliOperator:
    retained = set(retained_site_ids)
    return operator.module.operator(
        tuple(term for term in operator.terms if term.site_id in retained),
        phase=operator.phase,
    )


def compile_projected_primary_image(
    analysis: FiniteStabilizerAnalysis,
    window: SupportWindow,
    source_bulk_generators: Sequence[PauliOperator],
    projections: Sequence[CutStabilizerProjection],
    backend: FiniteIntegerBackend,
    *,
    source_description: str,
) -> CompiledPrimaryImage:
    """Compile an exact primary image from identified cut stabilizers.

    ``source_bulk_generators`` is the uncut parent stabilizer presentation.  It
    may differ from the retained stabilizers in ``analysis``.  This distinction
    is necessary because cut stabilizers are commonly absent from the retained
    finite Hamiltonian whose boundary algebra is being computed.
    """

    if window.paulis.ambient != analysis.ambient_projective_paulis:
        raise ValueError("support window belongs to a different Pauli ambient group")
    if not window.site_ids:
        raise ValueError(
            "phase-aware site restriction requires explicit window.site_ids; "
            "an arbitrary projective subgroup is ambiguous"
        )
    source_bulk_generators = tuple(source_bulk_generators)
    projections = tuple(projections)
    if len({item.projection_id for item in projections}) != len(projections):
        raise ValueError("projection IDs must be unique")
    if any(operator.module != analysis.module for operator in source_bulk_generators):
        raise ValueError("source bulk generators belong to a different Pauli module")
    source_analysis = analyze_finite_stabilizer(
        analysis.module, source_bulk_generators, backend
    )
    window_sites = set(window.site_ids)
    records = []
    projected = []
    for item in projections:
        if item.source_operator.module != analysis.module:
            raise ValueError(f"projection {item.projection_id!r} source has wrong module")
        if item.projected_operator.module != analysis.module:
            raise ValueError(f"projection {item.projection_id!r} target has wrong module")
        source_vector = analysis.coordinates.vector(item.source_operator)
        if not source_analysis.stabilizer.contains(source_vector, backend):
            raise ValueError(
                f"projection {item.projection_id!r} source is not in the parent stabilizer"
            )
        phase_membership = validate_stabilizer_generators(
            analysis.module,
            source_bulk_generators + (item.source_operator,),
            backend,
        )
        if not phase_membership.valid:
            raise ValueError(
                f"projection {item.projection_id!r} source has the wrong stabilizer phase"
            )

        source_sites = {term.site_id for term in item.source_operator.terms}
        actual_dropped = tuple(sorted(source_sites - window_sites))
        if item.policy is ProjectionPolicy.REQUIRE_FULL_SUPPORT:
            if actual_dropped:
                raise ValueError(
                    f"projection {item.projection_id!r} drops support under full-support policy"
                )
            if item.declared_dropped_site_ids:
                raise ValueError("full-support projection cannot declare dropped sites")
        elif item.declared_dropped_site_ids != actual_dropped:
            raise ValueError(
                f"projection {item.projection_id!r} dropped-site declaration is not exact"
            )

        expected = _literal_site_restriction(item.source_operator, window.site_ids)
        if item.projected_operator != expected:
            raise ValueError(
                f"projection {item.projection_id!r} is not the literal phase-aware restriction"
            )
        if (
            item.projected_operator.is_projective_identity
            and not item.projected_operator.is_identity
        ):
            raise ValueError(
                f"projection {item.projection_id!r} produces a nontrivial scalar"
            )
        projected_vector = analysis.coordinates.vector(item.projected_operator)
        if not window.paulis.contains(projected_vector, backend):
            raise ValueError(
                f"projection {item.projection_id!r} target is not contained in W"
            )
        if not analysis.centralizer.contains(projected_vector, backend):
            raise ValueError(
                f"projection {item.projection_id!r} target does not commute with retained bulk"
            )
        records.append(
            PrimaryProjectionRecord(
                item.projection_id,
                item.source_operator,
                item.projected_operator,
                actual_dropped,
                item.policy,
                True,
                True,
            )
        )
        projected.append(item.projected_operator)

    generator_matrix = analysis.coordinates.generator_matrix(tuple(projected))
    image = analysis.ambient_projective_paulis.subgroup(generator_matrix, backend)
    bulk_trivial = analysis.stabilizer.intersection(window.paulis, backend)
    supplied_or_bulk = image.sum(bulk_trivial, backend)
    coverage_records = []
    for source_index, source_operator in enumerate(source_bulk_generators):
        restriction = _literal_site_restriction(source_operator, window.site_ids)
        restriction_vector = analysis.coordinates.vector(restriction)
        central = analysis.centralizer.contains(restriction_vector, backend)
        covered_by_supplied = image.contains(restriction_vector, backend)
        covered_by_bulk = bulk_trivial.contains(restriction_vector, backend)
        covered_modulo_bulk = supplied_or_bulk.contains(restriction_vector, backend)
        coverage_records.append(
            PrimaryCoverageRecord(
                source_index,
                source_operator,
                restriction,
                restriction.is_identity,
                restriction.is_projective_identity,
                central,
                covered_by_supplied,
                covered_by_bulk,
                covered_modulo_bulk,
            )
        )
    coverage_complete = all(
        record.restriction_is_identity
        or (
            not record.restriction_is_projective_identity
            and record.centralizer_membership_verified
            and record.covered_modulo_bulk_trivial
        )
        for record in coverage_records
    )
    certificate = PrimaryImageCompilationCertificate(
        source_analysis.validation,
        tuple(records),
        tuple(coverage_records),
        coverage_complete,
        len(source_bulk_generators),
        len(projected),
        (
            Exactness.BOUNDED_EXACT
            if coverage_complete
            else Exactness.EXPERIMENTAL
        ),
    )
    return CompiledPrimaryImage(
        image,
        tuple(projected),
        certificate,
        source_description,
    )


def compile_and_analyze_finite_boundary(
    analysis: FiniteStabilizerAnalysis,
    window: SupportWindow,
    source_bulk_generators: Sequence[PauliOperator],
    projections: Sequence[CutStabilizerProjection],
    backend: FiniteIntegerBackend,
    *,
    source_description: str,
    tangent_translations: Sequence[TangentTranslationSpec] = (),
) -> CompiledFiniteBoundaryAlgebra:
    compilation = compile_projected_primary_image(
        analysis,
        window,
        source_bulk_generators,
        projections,
        backend,
        source_description=source_description,
    )
    if not compilation.coverage_complete:
        uncovered = tuple(
            record.source_generator_index
            for record in compilation.certificate.coverage_records
            if not (
                record.restriction_is_identity
                or (
                    not record.restriction_is_projective_identity
                    and record.centralizer_membership_verified
                    and record.covered_modulo_bulk_trivial
                )
            )
        )
        raise ValueError(
            "primary/secondary classification requires a coverage-complete "
            "projected primary image; uncovered parent generator indices: "
            + ", ".join(str(index) for index in uncovered)
        )
    algebra = analyze_finite_boundary_algebra(
        analysis,
        window,
        backend,
        tangent_translations=tangent_translations,
        projected_primary_image=compilation.image,
        primary_source_description=compilation.source_description,
    )
    return CompiledFiniteBoundaryAlgebra(compilation, algebra)


__all__ = [
    "CompiledFiniteBoundaryAlgebra",
    "CompiledPrimaryImage",
    "CutStabilizerProjection",
    "PrimaryCoverageRecord",
    "PrimaryImageCompilationCertificate",
    "PrimaryProjectionRecord",
    "ProjectionPolicy",
    "compile_and_analyze_finite_boundary",
    "compile_projected_primary_image",
]
