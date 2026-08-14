"""Categorical Cheshire/descendant-defect classification contracts.

This module separates three notions that were conflated by the original
finite-static Cheshire API:

* an abstract oriented condensation/descendant defect;
* a finite microscopic Hamiltonian realization;
* a circuit certificate relating finite realizations.

The exact executor implemented here is the finite pointed/Abelian one.  It
folds a pair of finite metric groups and exhausts the Lagrangian subgroups of
the folded metric group.  For the source-locked 2D Z2 toric code this produces
the six oriented defects of Roumpedakis--Seifnashri--Shao and
Tantivasadakarn--Chen.  The six are not stored as an assumed candidate list:
the literature labels are attached only after the generic folded enumerator
has found and certified the six corresponding Lagrangian subgroups.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import itertools
import math
from typing import Any, Optional, Sequence, Tuple

from mobility_toolkit.anyons2d import (
    CondensateCandidate,
    CondensateEnumerationBudget,
    CondensateEnumerationCheckpoint,
    FiniteMetricGroup,
    enumerate_condensates,
    fold_metric_groups,
    test_condensation,
    zd_toric_metric_model,
)
from mobility_toolkit.core import Exactness, SparseIntMatrix, canonical_hash
from mobility_toolkit.finite import FiniteIntegerBackend, FiniteSubgroup


class EvidenceStatus(str, Enum):
    """Status of one physical or mathematical claim."""

    SOURCE_THEOREM = "source_theorem"
    COMPUTED_EXACT = "computed_exact"
    BOUNDED_EXACT = "bounded_exact"
    CONDITIONAL = "conditional"
    CONJECTURAL = "conjectural"
    UNSUPPORTED = "unsupported"


class CheshireEvidenceTier(str, Enum):
    """Evidence ladder used for mobility-restricted/fracton candidates."""

    SUPPORT_CANDIDATE = "support_candidate"
    STATIC_CHESHIRE_CANDIDATE = "static_cheshire_candidate"
    MOBILITY_ENRICHED_ALGEBRA = "mobility_enriched_algebra"
    CIRCUIT_CERTIFIED_CHESHIRE = "circuit_certified_cheshire"


@dataclass(frozen=True)
class AlgebraMultiplicationEntry:
    left_object: str
    right_object: str
    output_object: str
    phase_exponent: int
    phase_modulus: int

    SCHEMA_ID = "mobility_toolkit.algebra_multiplication_entry.v2"

    def __post_init__(self) -> None:
        if not self.left_object or not self.right_object or not self.output_object:
            raise ValueError("algebra multiplication labels must be nonempty")
        if self.phase_modulus < 2:
            raise ValueError("multiplication phase modulus must be at least two")
        object.__setattr__(
            self, "phase_exponent", int(self.phase_exponent) % self.phase_modulus
        )

    def to_canonical_dict(self) -> dict:
        return {
            "left_object": self.left_object,
            "output_object": self.output_object,
            "phase_exponent": self.phase_exponent,
            "phase_modulus": self.phase_modulus,
            "right_object": self.right_object,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class AlgebraVerificationCertificate:
    unit_verified: bool
    closure_verified: bool
    associativity_verified: bool
    separability_source_theorem: bool
    braided_commutative: bool
    obstruction_free: bool
    verification_scope: str

    SCHEMA_ID = "mobility_toolkit.algebra_verification_certificate.v2"

    @property
    def verified(self) -> bool:
        return (
            self.unit_verified
            and self.closure_verified
            and self.associativity_verified
            and self.separability_source_theorem
            and self.obstruction_free
        )

    def to_canonical_dict(self) -> dict:
        return {
            "associativity_verified": self.associativity_verified,
            "braided_commutative": self.braided_commutative,
            "closure_verified": self.closure_verified,
            "obstruction_free": self.obstruction_free,
            "schema": self.SCHEMA_ID,
            "separability_source_theorem": self.separability_source_theorem,
            "unit_verified": self.unit_verified,
            "verification_scope": self.verification_scope,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class AlgebraObjectRecord:
    algebra_id: str
    simple_object_multiplicities: Tuple[Tuple[str, int], ...]
    unit_object: str
    multiplication_class: str
    cochain_gauge_class: str
    multiplication: Tuple[AlgebraMultiplicationEntry, ...]
    certificate: AlgebraVerificationCertificate
    evidence_status: EvidenceStatus
    source: str

    SCHEMA_ID = "mobility_toolkit.algebra_object_record.v2"

    def __post_init__(self) -> None:
        if not self.algebra_id or not self.unit_object:
            raise ValueError("algebra and unit IDs must be nonempty")
        multiplicities = tuple(self.simple_object_multiplicities)
        if not multiplicities or any(
            not label or isinstance(value, bool) or int(value) < 1
            for label, value in multiplicities
        ):
            raise ValueError("algebra support needs positive integer multiplicities")
        if len({label for label, _ in multiplicities}) != len(multiplicities):
            raise ValueError("algebra support repeats a simple object")
        object.__setattr__(self, "simple_object_multiplicities", multiplicities)
        object.__setattr__(self, "multiplication", tuple(self.multiplication))

    @property
    def braided_commutative(self) -> bool:
        return self.certificate.braided_commutative

    def to_canonical_dict(self) -> dict:
        return {
            "algebra_id": self.algebra_id,
            "braided_commutative": self.braided_commutative,
            "certificate": self.certificate,
            "cochain_gauge_class": self.cochain_gauge_class,
            "evidence_status": self.evidence_status,
            "multiplication": self.multiplication,
            "multiplication_class": self.multiplication_class,
            "schema": self.SCHEMA_ID,
            "simple_object_multiplicities": self.simple_object_multiplicities,
            "source": self.source,
            "unit_object": self.unit_object,
        }


@dataclass(frozen=True)
class PointedFusionRule:
    left_object: str
    right_object: str
    output_object: str

    SCHEMA_ID = "mobility_toolkit.pointed_fusion_rule.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "left_object": self.left_object,
            "output_object": self.output_object,
            "right_object": self.right_object,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class PointedAssociatorEntry:
    first_object: str
    second_object: str
    third_object: str
    phase_exponent: int

    SCHEMA_ID = "mobility_toolkit.pointed_associator_entry.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "first_object": self.first_object,
            "phase_exponent": self.phase_exponent,
            "schema": self.SCHEMA_ID,
            "second_object": self.second_object,
            "third_object": self.third_object,
        }


@dataclass(frozen=True)
class PointedCategoryCochainData:
    object_ids: Tuple[str, ...]
    unit_object: str
    phase_modulus: int
    fusion_rules: Tuple[PointedFusionRule, ...]
    associator: Tuple[PointedAssociatorEntry, ...]
    source: str

    SCHEMA_ID = "mobility_toolkit.pointed_category_cochain_data.v2"

    def __post_init__(self) -> None:
        objects = tuple(self.object_ids)
        if not objects or len(set(objects)) != len(objects):
            raise ValueError("pointed category object IDs must be nonempty and unique")
        if self.unit_object not in objects:
            raise ValueError("pointed category unit is not an object")
        if self.phase_modulus < 2:
            raise ValueError("pointed category phase modulus must be at least two")
        if not self.source:
            raise ValueError("pointed category cochain source must be nonempty")
        object.__setattr__(self, "object_ids", objects)
        object.__setattr__(self, "fusion_rules", tuple(self.fusion_rules))
        object.__setattr__(self, "associator", tuple(self.associator))

    def to_canonical_dict(self) -> dict:
        return {
            "associator": self.associator,
            "fusion_rules": self.fusion_rules,
            "object_ids": self.object_ids,
            "phase_modulus": self.phase_modulus,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "unit_object": self.unit_object,
        }


@dataclass(frozen=True)
class PointedAlgebraCochainCertificate:
    fusion_table_total: bool
    group_laws_verified: bool
    associator_cocycle_verified: bool
    support_closed: bool
    normalized_unit_verified: bool
    associativity_verified: bool
    associator_obstruction_free: bool
    coboundary_gauge_class_hash: str
    evidence_status: EvidenceStatus
    verification_scope: str

    SCHEMA_ID = "mobility_toolkit.pointed_algebra_cochain_certificate.v2"

    @property
    def verified(self) -> bool:
        return (
            self.fusion_table_total
            and self.group_laws_verified
            and self.associator_cocycle_verified
            and self.support_closed
            and self.normalized_unit_verified
            and self.associativity_verified
            and self.associator_obstruction_free
        )

    def to_canonical_dict(self) -> dict:
        return {
            "associativity_verified": self.associativity_verified,
            "associator_cocycle_verified": self.associator_cocycle_verified,
            "associator_obstruction_free": self.associator_obstruction_free,
            "coboundary_gauge_class_hash": self.coboundary_gauge_class_hash,
            "evidence_status": self.evidence_status,
            "fusion_table_total": self.fusion_table_total,
            "group_laws_verified": self.group_laws_verified,
            "normalized_unit_verified": self.normalized_unit_verified,
            "schema": self.SCHEMA_ID,
            "support_closed": self.support_closed,
            "verification_scope": self.verification_scope,
            "verified": self.verified,
        }


def _pointed_tables(
    category: PointedCategoryCochainData,
) -> Tuple[dict, dict]:
    fusion = {
        (item.left_object, item.right_object): item.output_object
        for item in category.fusion_rules
    }
    associator = {
        (item.first_object, item.second_object, item.third_object):
            int(item.phase_exponent) % category.phase_modulus
        for item in category.associator
    }
    return fusion, associator


def verify_pointed_algebra_cochain(
    category: PointedCategoryCochainData,
    support: Sequence[str],
    multiplication_cochain: Sequence[AlgebraMultiplicationEntry],
) -> PointedAlgebraCochainCertificate:
    """Check a supplied pointed algebra multiplication against its associator."""

    support = tuple(support)
    if not support or len(set(support)) != len(support):
        raise ValueError("pointed algebra support must be nonempty and unique")
    if any(item not in category.object_ids for item in support):
        raise ValueError("pointed algebra support contains an unknown object")
    fusion, associator = _pointed_tables(category)
    expected_pairs = {
        (left, right) for left in category.object_ids for right in category.object_ids
    }
    total = set(fusion) == expected_pairs
    group_laws = total
    if total:
        group_laws = all(
            fusion[(category.unit_object, item)] == item
            and fusion[(item, category.unit_object)] == item
            for item in category.object_ids
        ) and all(
            fusion[(fusion[(first, second)], third)]
            == fusion[(first, fusion[(second, third)])]
            for first in category.object_ids
            for second in category.object_ids
            for third in category.object_ids
        )
    associator_cocycle = total and group_laws and all(
        associator.get(
            (category.unit_object, second, third), 0
        ) == 0
        and associator.get(
            (first, category.unit_object, third), 0
        ) == 0
        and associator.get(
            (first, second, category.unit_object), 0
        ) == 0
        for first in category.object_ids
        for second in category.object_ids
        for third in category.object_ids
    )
    if associator_cocycle:
        associator_cocycle = all(
            (
                associator.get((second, third, fourth), 0)
                + associator.get(
                    (first, fusion[(second, third)], fourth), 0
                )
                + associator.get((first, second, third), 0)
                - associator.get(
                    (fusion[(first, second)], third, fourth), 0
                )
                - associator.get(
                    (first, second, fusion[(third, fourth)]), 0
                )
            )
            % category.phase_modulus
            == 0
            for first in category.object_ids
            for second in category.object_ids
            for third in category.object_ids
            for fourth in category.object_ids
        )
    cochain = {
        (item.left_object, item.right_object):
            int(item.phase_exponent) % category.phase_modulus
        for item in multiplication_cochain
    }
    support_pairs = {(left, right) for left in support for right in support}
    cochain_shape_valid = (
        len(tuple(multiplication_cochain)) == len(cochain)
        and all(
            item.phase_modulus == category.phase_modulus
            and fusion.get((item.left_object, item.right_object))
            == item.output_object
            for item in multiplication_cochain
        )
    )
    support_closed = total and all(
        fusion[(left, right)] in support for left, right in support_pairs
    )
    normalized = (
        category.unit_object in support
        and set(cochain) == support_pairs
        and cochain_shape_valid
        and all(
            cochain[(category.unit_object, item)] == 0
            and cochain[(item, category.unit_object)] == 0
            for item in support
        )
    )
    associative = (
        total
        and support_closed
        and associator_cocycle
        and cochain_shape_valid
        and set(cochain) == support_pairs
    )
    if associative:
        for first in support:
            for second in support:
                for third in support:
                    left_product = fusion[(first, second)]
                    right_product = fusion[(second, third)]
                    omega = associator.get((first, second, third), 0)
                    lhs = (
                        cochain[(first, second)]
                        + cochain[(left_product, third)]
                    ) % category.phase_modulus
                    rhs = (
                        omega
                        + cochain[(second, third)]
                        + cochain[(first, right_product)]
                    ) % category.phase_modulus
                    if lhs != rhs:
                        associative = False
    normalized_vector = tuple(
        (left, right, cochain.get((left, right)))
        for left in sorted(support)
        for right in sorted(support)
    )
    return PointedAlgebraCochainCertificate(
        fusion_table_total=total,
        group_laws_verified=group_laws,
        associator_cocycle_verified=associator_cocycle,
        support_closed=support_closed,
        normalized_unit_verified=normalized,
        associativity_verified=associative,
        associator_obstruction_free=associative,
        coboundary_gauge_class_hash=canonical_hash(
            "pointed-algebra-cochain-representative-v2", normalized_vector
        ),
        evidence_status=(
            EvidenceStatus.COMPUTED_EXACT
            if (
                total
                and group_laws
                and associator_cocycle
                and support_closed
                and normalized
            )
            else EvidenceStatus.UNSUPPORTED
        ),
        verification_scope=(
            "Exact finite fusion-table, normalized cochain, and d(mu)=omega "
            "associativity check for the supplied pointed presentation."
        ),
    )


def pointed_algebra_coboundary_equivalent(
    category: PointedCategoryCochainData,
    support: Sequence[str],
    left_cochain: Sequence[AlgebraMultiplicationEntry],
    right_cochain: Sequence[AlgebraMultiplicationEntry],
    one_cochain: Sequence[Tuple[str, int]],
) -> bool:
    """Verify the explicitly supplied coboundary gauge transformation."""

    support = tuple(support)
    fusion, _ = _pointed_tables(category)
    left = {
        (item.left_object, item.right_object):
            int(item.phase_exponent) % category.phase_modulus
        for item in left_cochain
    }
    right = {
        (item.left_object, item.right_object):
            int(item.phase_exponent) % category.phase_modulus
        for item in right_cochain
    }
    gauge = {
        label: int(value) % category.phase_modulus
        for label, value in one_cochain
    }
    if set(gauge) != set(support) or gauge.get(category.unit_object) != 0:
        return False
    pairs = {(first, second) for first in support for second in support}
    if set(left) != pairs or set(right) != pairs:
        return False
    return all(
        right[(first, second)]
        == (
            left[(first, second)]
            + gauge[first]
            + gauge[second]
            - gauge[fusion[(first, second)]]
        )
        % category.phase_modulus
        for first, second in pairs
    )


@dataclass(frozen=True)
class BulkSectorAction:
    input_sector: str
    output_sectors: Tuple[Tuple[str, int], ...]

    SCHEMA_ID = "mobility_toolkit.bulk_sector_action.v2"

    def __post_init__(self) -> None:
        if not self.input_sector:
            raise ValueError("input sector must be nonempty")
        outputs = tuple(self.output_sectors)
        if any(not label or int(multiplicity) < 1 for label, multiplicity in outputs):
            raise ValueError("bulk-sector output multiplicities must be positive")
        object.__setattr__(self, "output_sectors", outputs)

    def to_canonical_dict(self) -> dict:
        return {
            "input_sector": self.input_sector,
            "output_sectors": self.output_sectors,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class DefectSpeciesRecord:
    species_id: str
    display_label: str
    domain_id: str
    species_kind: str
    folded_support: FiniteSubgroup
    folded_generators: Tuple[Tuple[int, ...], ...]
    algebra: Optional[AlgebraObjectRecord]
    morita_class_id: str
    orientation_reverse_id: Optional[str]
    invertible: bool
    bulk_sector_action: Tuple[BulkSectorAction, ...]
    evidence_status: EvidenceStatus
    microscopic_realization_constructed: bool
    missing_obligations: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.defect_species_record.v2"

    def __post_init__(self) -> None:
        for value, name in (
            (self.species_id, "species_id"),
            (self.display_label, "display_label"),
            (self.domain_id, "domain_id"),
            (self.species_kind, "species_kind"),
            (self.morita_class_id, "morita_class_id"),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} must be a nonempty string")
        object.__setattr__(
            self, "folded_generators", tuple(tuple(row) for row in self.folded_generators)
        )
        object.__setattr__(self, "bulk_sector_action", tuple(self.bulk_sector_action))
        object.__setattr__(
            self, "missing_obligations", tuple(sorted(set(self.missing_obligations)))
        )

    def to_canonical_dict(self) -> dict:
        return {
            "algebra": self.algebra,
            "bulk_sector_action": self.bulk_sector_action,
            "display_label": self.display_label,
            "domain_id": self.domain_id,
            "evidence_status": self.evidence_status,
            "folded_generators": self.folded_generators,
            "folded_support": self.folded_support,
            "invertible": self.invertible,
            "microscopic_realization_constructed":
                self.microscopic_realization_constructed,
            "missing_obligations": self.missing_obligations,
            "morita_class_id": self.morita_class_id,
            "orientation_reverse_id": self.orientation_reverse_id,
            "schema": self.SCHEMA_ID,
            "species_id": self.species_id,
            "species_kind": self.species_kind,
        }


@dataclass(frozen=True)
class ClassificationOrbit:
    orbit_id: str
    member_species_ids: Tuple[str, ...]
    equivalence_relation: str

    SCHEMA_ID = "mobility_toolkit.defect_classification_orbit.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "equivalence_relation": self.equivalence_relation,
            "member_species_ids": self.member_species_ids,
            "orbit_id": self.orbit_id,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FoldedLagrangianEnumerationCertificate:
    """Certificate for the isotropic-pruned diagonal-coordinate executor."""

    metric_hash: str
    coordinate_orders: Tuple[int, ...]
    group_order: int
    target_lagrangian_order: int
    isotropic_subgroups_visited: int
    isotropic_extension_tests: int
    lagrangian_subgroups: int
    output_transcript_hash: str
    output_complete: bool
    exactness: Exactness
    verification: Tuple[str, ...]
    theorem_scope: str

    SCHEMA_ID = "mobility_toolkit.folded_lagrangian_enumeration_certificate.v2"

    @property
    def certified_complete(self) -> bool:
        return self.output_complete and self.exactness is Exactness.CERTIFIED_EXACT

    def to_canonical_dict(self) -> dict:
        return {
            "certified_complete": self.certified_complete,
            "coordinate_orders": self.coordinate_orders,
            "exactness": self.exactness,
            "group_order": self.group_order,
            "isotropic_extension_tests": self.isotropic_extension_tests,
            "isotropic_subgroups_visited": self.isotropic_subgroups_visited,
            "lagrangian_subgroups": self.lagrangian_subgroups,
            "metric_hash": self.metric_hash,
            "output_complete": self.output_complete,
            "output_transcript_hash": self.output_transcript_hash,
            "schema": self.SCHEMA_ID,
            "target_lagrangian_order": self.target_lagrangian_order,
            "theorem_scope": self.theorem_scope,
            "verification": self.verification,
        }


@dataclass(frozen=True)
class InterfaceClassificationCertificate:
    folded_metric: FiniteMetricGroup
    enumeration: Any
    lagrangian_species_count: int
    classification_complete: bool
    oriented_morita_interpretation: bool
    toric_literature_crosswalk_verified: bool
    transcript_hash: str

    SCHEMA_ID = "mobility_toolkit.interface_classification_certificate.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "classification_complete": self.classification_complete,
            "enumeration": self.enumeration,
            "folded_metric": self.folded_metric,
            "lagrangian_species_count": self.lagrangian_species_count,
            "oriented_morita_interpretation": self.oriented_morita_interpretation,
            "schema": self.SCHEMA_ID,
            "toric_literature_crosswalk_verified":
                self.toric_literature_crosswalk_verified,
            "transcript_hash": self.transcript_hash,
        }


@dataclass(frozen=True)
class AbelianInterfaceClassification:
    left_metric: FiniteMetricGroup
    right_metric: FiniteMetricGroup
    folded_metric: FiniteMetricGroup
    species: Tuple[DefectSpeciesRecord, ...]
    orbits: Tuple[ClassificationOrbit, ...]
    equivalence_relation: str
    next_checkpoint: Optional[CondensateEnumerationCheckpoint]
    certificate: InterfaceClassificationCertificate
    assumptions: Tuple[str, ...]
    warnings: Tuple[str, ...]

    SCHEMA_ID = "mobility_toolkit.abelian_interface_classification.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "assumptions": self.assumptions,
            "certificate": self.certificate,
            "equivalence_relation": self.equivalence_relation,
            "folded_metric": self.folded_metric,
            "left_metric": self.left_metric,
            "next_checkpoint": self.next_checkpoint,
            "orbits": self.orbits,
            "right_metric": self.right_metric,
            "schema": self.SCHEMA_ID,
            "species": self.species,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class FusionCoefficient1D:
    coefficient_id: str
    tqft_kind: str
    gauge_group: Optional[str]
    partition_function_shadow_on_interval: int
    numeric_scalar: bool
    evidence_status: EvidenceStatus
    source: str

    SCHEMA_ID = "mobility_toolkit.fusion_coefficient_1d.v2"

    def __post_init__(self) -> None:
        if not self.coefficient_id or not self.tqft_kind:
            raise ValueError("fusion coefficient IDs must be nonempty")
        if self.partition_function_shadow_on_interval < 1:
            raise ValueError("partition-function shadow must be positive")

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_id": self.coefficient_id,
            "evidence_status": self.evidence_status,
            "gauge_group": self.gauge_group,
            "numeric_scalar": self.numeric_scalar,
            "partition_function_shadow_on_interval":
                self.partition_function_shadow_on_interval,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "tqft_kind": self.tqft_kind,
        }


@dataclass(frozen=True)
class FusionTerm:
    output_species_id: str
    coefficient: FusionCoefficient1D
    multiplicity: int = 1

    SCHEMA_ID = "mobility_toolkit.defect_fusion_term.v2"

    def __post_init__(self) -> None:
        if not self.output_species_id:
            raise ValueError("fusion output species must be nonempty")
        if self.multiplicity < 1:
            raise ValueError("fusion multiplicity must be positive")

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient": self.coefficient,
            "multiplicity": self.multiplicity,
            "output_species_id": self.output_species_id,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class FusionResult:
    left_species_id: str
    right_species_id: str
    ordered: bool
    terms: Tuple[FusionTerm, ...]
    evidence_status: EvidenceStatus
    source_basis: str
    verified: bool

    SCHEMA_ID = "mobility_toolkit.defect_fusion_result.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "evidence_status": self.evidence_status,
            "left_species_id": self.left_species_id,
            "ordered": self.ordered,
            "right_species_id": self.right_species_id,
            "schema": self.SCHEMA_ID,
            "source_basis": self.source_basis,
            "terms": self.terms,
            "verified": self.verified,
        }


TORIC_SPECIES_ORDER = ("1", "S_e", "S_m", "S_psi", "S_em", "S_me")
TORIC_ORIENTATION_REVERSE = {
    "1": "1",
    "S_e": "S_e",
    "S_m": "S_m",
    "S_psi": "S_psi",
    "S_em": "S_me",
    "S_me": "S_em",
}
TORIC_SOURCE = (
    "Roumpedakis--Seifnashri--Shao arXiv:2204.02407 Sec. 6.3 and "
    "Tantivasadakarn--Chen arXiv:2307.03180 Appendix A"
)


def _matrix_from_columns(
    columns: Sequence[Sequence[int]], nrows: int
) -> SparseIntMatrix:
    columns = tuple(tuple(int(value) for value in column) for column in columns)
    if any(len(column) != nrows for column in columns):
        raise ValueError("generator column has the wrong rank")
    return SparseIntMatrix(
        nrows,
        len(columns),
        tuple(
            (row, column_index, value)
            for column_index, column in enumerate(columns)
            for row, value in enumerate(column)
            if value
        ),
    )


def _generic_species_id(
    left: FiniteMetricGroup,
    right: FiniteMetricGroup,
    subgroup: FiniteSubgroup,
) -> str:
    def metric_signature(metric: FiniteMetricGroup) -> dict:
        # Coordinate labels are presentation metadata, not categorical data.
        # Keeping them out of the ID makes harmless generator relabeling
        # invisible while retaining the exact relation, spin, and braiding
        # presentation used by this executor.
        return {
            "braiding_matrix": metric.braiding_matrix,
            "generator_spins": metric.generator_spins,
            "group_invariant_factors": metric.group.invariant_factors,
            "phase_modulus": metric.phase_modulus,
            "relation_lattice_basis": metric.group.relation_lattice_basis,
        }

    digest = canonical_hash(
        "mobility_toolkit.oriented_folded_lagrangian.v2",
        {
            "left": metric_signature(left),
            "right": metric_signature(right),
            "subgroup_preimage_lattice_basis":
                subgroup.preimage_lattice_basis,
        },
    )
    return "interface:" + digest[:24]


def _orientation_swap_subgroup(
    subgroup: FiniteSubgroup,
    side_rank: int,
    backend: FiniteIntegerBackend,
) -> FiniteSubgroup:
    rank = subgroup.ambient.presentation_rank
    if rank != 2 * side_rank:
        raise ValueError("orientation swap requires equal presentation ranks")
    transform = SparseIntMatrix(
        rank,
        rank,
        tuple(
            [(index + side_rank, index, 1) for index in range(side_rank)]
            + [(index, index + side_rank, 1) for index in range(side_rank)]
        ),
    )
    return subgroup.ambient.subgroup(
        transform.matmul(subgroup.preimage_lattice_basis), backend
    )


def _classification_orbits(
    species: Sequence[DefectSpeciesRecord], equivalence_relation: str
) -> Tuple[ClassificationOrbit, ...]:
    if equivalence_relation not in {
        "oriented_morita",
        "unoriented_morita",
        "raw_folded_lagrangian",
    }:
        raise ValueError(
            "equivalence_relation must be oriented_morita, "
            "unoriented_morita, or raw_folded_lagrangian"
        )
    if equivalence_relation != "unoriented_morita":
        return tuple(
            ClassificationOrbit(
                "orbit:" + item.species_id,
                (item.species_id,),
                equivalence_relation,
            )
            for item in species
        )
    by_id = {item.species_id: item for item in species}
    remaining = set(by_id)
    output = []
    while remaining:
        item_id = min(remaining)
        partner = by_id[item_id].orientation_reverse_id
        members = tuple(
            sorted(
                {
                    item_id,
                    *(
                        (partner,)
                        if partner is not None and partner in by_id
                        else ()
                    ),
                }
            )
        )
        remaining.difference_update(members)
        output.append(
            ClassificationOrbit(
                "orbit:" + canonical_hash(
                    "mobility_toolkit.unoriented_morita_orbit.v2", members
                )[:24],
                members,
                equivalence_relation,
            )
        )
    return tuple(output)


def _diagonal_coordinate_orders(
    metric: FiniteMetricGroup,
) -> Optional[Tuple[int, ...]]:
    rows = metric.group.relation_lattice_basis.to_rows()
    if len(rows) != metric.group.presentation_rank:
        return None
    orders = []
    for row_index, row in enumerate(rows):
        if len(row) != len(rows):
            return None
        for column_index, value in enumerate(row):
            if column_index != row_index and value:
                return None
        diagonal = int(row[row_index])
        if diagonal <= 1:
            return None
        orders.append(diagonal)
    return tuple(orders)


def _coordinate_add(
    left: Sequence[int],
    right: Sequence[int],
    orders: Sequence[int],
) -> Tuple[int, ...]:
    return tuple(
        (int(left[index]) + int(right[index])) % int(order)
        for index, order in enumerate(orders)
    )


def _extend_coordinate_subgroup(
    members: frozenset[int],
    generator_index: int,
    elements: Sequence[Tuple[int, ...]],
    index_by_vector: dict[Tuple[int, ...], int],
    orders: Sequence[int],
) -> frozenset[int]:
    generator = elements[generator_index]
    cyclic = []
    current = tuple(0 for _ in orders)
    while True:
        cyclic.append(index_by_vector[current])
        current = _coordinate_add(current, generator, orders)
        if all(value == 0 for value in current):
            break
    return frozenset(
        index_by_vector[_coordinate_add(elements[left], elements[right], orders)]
        for left in members
        for right in cyclic
    )


def _coordinate_generators(
    members: frozenset[int],
    elements: Sequence[Tuple[int, ...]],
    index_by_vector: dict[Tuple[int, ...], int],
    orders: Sequence[int],
) -> Tuple[int, ...]:
    generated = frozenset({index_by_vector[tuple(0 for _ in orders)]})
    output = []
    for candidate in sorted(members):
        if candidate in generated:
            continue
        output.append(candidate)
        generated = _extend_coordinate_subgroup(
            generated, candidate, elements, index_by_vector, orders
        )
        if generated == members:
            break
    if generated != members:
        raise ArithmeticError("failed to reconstruct finite subgroup generators")
    return tuple(output)


def _matrix_from_generator_vectors(
    generators: Sequence[Sequence[int]], rank: int
) -> SparseIntMatrix:
    return SparseIntMatrix(
        rank,
        len(generators),
        tuple(
            (row, column, int(value))
            for column, generator in enumerate(generators)
            for row, value in enumerate(generator)
            if value
        ),
    )


def _enumerate_diagonal_lagrangians(
    metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    budget: CondensateEnumerationBudget,
) -> Optional[
    Tuple[
        Tuple[CondensateCandidate, ...],
        FoldedLagrangianEnumerationCertificate,
    ]
]:
    """Prune directly to isotropic subgroups for diagonal presentations.

    Returning ``None`` asks the caller to use the general resumable raw-subgroup
    enumerator.  The specialized search has no partial/checkpoint mode: it is
    used only after the complete finite domain fits the declared element and
    work budgets.
    """

    orders = _diagonal_coordinate_orders(metric)
    if orders is None:
        return None
    group_order = math.prod(orders)
    target_order = math.isqrt(group_order)
    if target_order * target_order != group_order:
        raise ValueError(
            "a nondegenerate folded metric group must have square order"
        )
    if group_order > budget.max_elements:
        return None
    elements = tuple(itertools.product(*(range(order) for order in orders)))
    index_by_vector = {vector: index for index, vector in enumerate(elements)}
    zero_index = index_by_vector[tuple(0 for _ in orders)]
    spins = tuple(metric.spin_exponent(vector) for vector in elements)
    braiding = tuple(
        tuple(metric.braiding_exponent(left, right) for right in elements)
        for left in elements
    )

    trivial = frozenset({zero_index})
    seen = {trivial}
    queue = [trivial]
    lagrangian_members = []
    extension_tests = 0
    while queue:
        subgroup = queue.pop()
        if len(subgroup) == target_order:
            lagrangian_members.append(subgroup)
            continue
        for candidate in range(1, len(elements)):
            extension_tests += 1
            if extension_tests > budget.max_work_units:
                return None
            if candidate in subgroup or spins[candidate]:
                continue
            if any(braiding[candidate][member] for member in subgroup):
                continue
            extension = _extend_coordinate_subgroup(
                subgroup, candidate, elements, index_by_vector, orders
            )
            if len(extension) > target_order or extension in seen:
                continue
            if any(spins[member] for member in extension):
                raise ArithmeticError(
                    "isotropic-extension pruning admitted a non-bosonic element"
                )
            if any(
                braiding[left][right]
                for left in extension
                for right in extension
            ):
                raise ArithmeticError(
                    "isotropic-extension pruning admitted nontrivial monodromy"
                )
            seen.add(extension)
            queue.append(extension)
            if len(seen) > budget.max_subgroups:
                return None

    metric_hash = canonical_hash(
        "finite-metric-condensates-v1", metric
    )
    candidates = []
    for members in sorted(
        set(lagrangian_members),
        key=lambda item: (len(item), tuple(sorted(item))),
    ):
        generator_indices = _coordinate_generators(
            members, elements, index_by_vector, orders
        )
        generator_vectors = tuple(elements[index] for index in generator_indices)
        subgroup = metric.group.subgroup(
            _matrix_from_generator_vectors(
                generator_vectors, metric.group.presentation_rank
            ),
            backend,
        )
        condensation = test_condensation(metric, subgroup, backend)
        if not condensation.lagrangian:
            raise ArithmeticError(
                "isotropic-pruned target-order subgroup failed the exact "
                "Lagrangian certificate"
            )
        candidates.append(
            CondensateCandidate(
                metric_hash=metric_hash,
                element_indices=tuple(sorted(members)),
                generator_indices=generator_indices,
                generator_vectors=generator_vectors,
                subgroup=subgroup,
                invariant_factors=subgroup.invariant_factors(backend),
                condensation=condensation,
            )
        )
    transcript_hash = canonical_hash(
        "mobility_toolkit.diagonal_lagrangian_transcript.v2",
        tuple(candidates),
    )
    certificate = FoldedLagrangianEnumerationCertificate(
        metric_hash=metric_hash,
        coordinate_orders=orders,
        group_order=group_order,
        target_lagrangian_order=target_order,
        isotropic_subgroups_visited=len(seen),
        isotropic_extension_tests=extension_tests,
        lagrangian_subgroups=len(candidates),
        output_transcript_hash=transcript_hash,
        output_complete=True,
        exactness=Exactness.CERTIFIED_EXACT,
        verification=(
            "every extension was generated by a boson orthogonal to the current subgroup",
            "the search exhausts the finite closure graph of isotropic subgroups",
            "every target-order subgroup passed the independent exact condensation and orthogonal-complement certificate",
            "nondegeneracy makes isotropic target-order subgroups precisely Lagrangian",
        ),
        theorem_scope=(
            "Exhaustive Lagrangian-subgroup enumeration for this explicit "
            "diagonal-coordinate finite nondegenerate metric group; no "
            "microscopic Hamiltonian or quotient by automorphisms."
        ),
    )
    return tuple(candidates), certificate


def classify_abelian_interfaces(
    left_metric: FiniteMetricGroup,
    right_metric: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    *,
    budget: Optional[CondensateEnumerationBudget] = None,
    checkpoint: Optional[CondensateEnumerationCheckpoint] = None,
    max_pages: int = 1000,
    equivalence_relation: str = "oriented_morita",
) -> AbelianInterfaceClassification:
    """Exhaust folded Lagrangians for an explicit pair of finite metric groups."""

    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    budget = budget or CondensateEnumerationBudget(
        max_work_units=2_000_000,
        max_results=100_000,
        max_elements=4_096,
        max_subgroups=500_000,
    )
    folded = fold_metric_groups(left_metric, right_metric, backend).metric
    optimized = (
        _enumerate_diagonal_lagrangians(folded, backend, budget)
        if checkpoint is None
        else None
    )
    if optimized is not None:
        candidates, enumeration_certificate = optimized
        current = None
        assembled_complete_output = True
    else:
        candidates = []
        page = None
        current = checkpoint
        assembled_complete_output = checkpoint is None
        for _ in range(max_pages):
            page = enumerate_condensates(folded, backend, budget, current)
            candidates.extend(item for item in page.candidates if item.lagrangian)
            current = page.checkpoint
            if current is None:
                break
        if page is None:
            raise ArithmeticError("folded Lagrangian enumeration produced no page")
        enumeration_certificate = page.certificate
        if current is None and checkpoint is not None:
            # A raw-subgroup checkpoint commits earlier output hashes but does
            # not carry the full candidate records.  Reconstruct the complete
            # diagonal Lagrangian output after exhaustion so a resumed
            # classification has the same species and transcript as a
            # one-shot classification, rather than promoting only the final
            # output page to a complete species list.
            reconstruction_budget = CondensateEnumerationBudget(
                max_work_units=max(budget.max_work_units, 2_000_000),
                max_results=max(budget.max_results, 100_000),
                max_elements=budget.max_elements,
                max_subgroups=budget.max_subgroups,
            )
            reconstructed = _enumerate_diagonal_lagrangians(
                folded, backend, reconstruction_budget
            )
            if reconstructed is not None:
                candidates, enumeration_certificate = reconstructed
                assembled_complete_output = True

    records = []
    for candidate in candidates:
        species_id = _generic_species_id(
            left_metric, right_metric, candidate.subgroup
        )
        records.append(
            DefectSpeciesRecord(
                species_id=species_id,
                display_label=species_id,
                domain_id="finite_pointed_abelian_interface",
                species_kind="oriented_condensation_interface",
                folded_support=candidate.subgroup,
                folded_generators=candidate.generator_vectors,
                algebra=None,
                morita_class_id=species_id,
                orientation_reverse_id=None,
                invertible=False,
                bulk_sector_action=(),
                evidence_status=EvidenceStatus.COMPUTED_EXACT,
                microscopic_realization_constructed=False,
                missing_obligations=(
                    "direct algebra multiplication not reconstructed from metric data",
                    "microscopic Hamiltonian not supplied",
                    "ordered fusion coefficient not computed",
                ),
            )
        )

    left_rank = left_metric.group.presentation_rank
    right_rank = right_metric.group.presentation_rank
    reverse_folded = fold_metric_groups(
        right_metric, left_metric, backend
    ).metric
    with_orientation = []
    for item in records:
        swapped_vectors = tuple(
            tuple(vector[left_rank:]) + tuple(vector[:left_rank])
            for vector in item.folded_generators
        )
        swapped_support = reverse_folded.group.subgroup(
            _matrix_from_generator_vectors(
                swapped_vectors, left_rank + right_rank
            ),
            backend,
        )
        with_orientation.append(
            replace(
                item,
                orientation_reverse_id=_generic_species_id(
                    right_metric, left_metric, swapped_support
                ),
            )
        )
    records = with_orientation

    records = sorted(records, key=lambda item: item.species_id)
    complete = (
        current is None
        and enumeration_certificate.certified_complete
        and assembled_complete_output
    )
    transcript_hash = canonical_hash(
        "mobility_toolkit.abelian_interface_classification_transcript.v2",
        {
            "enumeration": enumeration_certificate,
            "left": left_metric,
            "right": right_metric,
            "species": tuple(records),
        },
    )
    certificate = InterfaceClassificationCertificate(
        folded_metric=folded,
        enumeration=enumeration_certificate,
        lagrangian_species_count=len(records),
        classification_complete=complete,
        oriented_morita_interpretation=True,
        toric_literature_crosswalk_verified=False,
        transcript_hash=transcript_hash,
    )
    orbits = _classification_orbits(records, equivalence_relation)
    return AbelianInterfaceClassification(
        left_metric=left_metric,
        right_metric=right_metric,
        folded_metric=folded,
        species=tuple(records),
        orbits=orbits,
        equivalence_relation=equivalence_relation,
        next_checkpoint=current,
        certificate=certificate,
        assumptions=(
            "the supplied metric groups describe finite pointed/Abelian topological orders",
            "folding identifies oriented interfaces with Lagrangian algebras in the doubled theory",
        ),
        warnings=(
            "Abstract folded classification does not construct a microscopic Hamiltonian.",
            "Direct algebra multiplication and generic interface fusion require additional pointed-category cochain data.",
            *(
                (
                    "The resumed non-diagonal raw-subgroup search exhausted, "
                    "but prior candidate records were not reconstructible from "
                    "the hash-only checkpoint; classification_complete remains false.",
                )
                if current is None and not assembled_complete_output
                else ()
            ),
        ),
    )


_TORIC_BITS = {
    "1": (0, 0),
    "e": (1, 0),
    "m": (0, 1),
    "psi": (1, 1),
}
_TORIC_LABEL_BY_BITS = {value: key for key, value in _TORIC_BITS.items()}


def _toric_multiplication(
    support: Sequence[str], multiplication_class: str
) -> Tuple[AlgebraMultiplicationEntry, ...]:
    support = tuple(support)
    entries = []
    for left in support:
        for right in support:
            a, b = _TORIC_BITS[left]
            c, d = _TORIC_BITS[right]
            output = _TORIC_LABEL_BY_BITS[(a ^ c, b ^ d)]
            phase = 0
            if multiplication_class == "mu_1_nontrivial_discrete_torsion":
                phase = b * c
            entries.append(
                AlgebraMultiplicationEntry(left, right, output, phase, 2)
            )
    return tuple(entries)


def _verify_toric_algebra(
    support: Sequence[str],
    multiplication: Sequence[AlgebraMultiplicationEntry],
    braided_commutative: bool,
) -> AlgebraVerificationCertificate:
    support = tuple(support)
    table = {
        (item.left_object, item.right_object):
            (item.output_object, item.phase_exponent)
        for item in multiplication
    }
    closure = len(table) == len(support) ** 2 and all(
        output in support for output, _ in table.values()
    )
    unit = all(
        table.get(("1", item)) == (item, 0)
        and table.get((item, "1")) == (item, 0)
        for item in support
    )
    associative = True
    for first in support:
        for second in support:
            for third in support:
                left_output, left_phase = table[(first, second)]
                lhs_output, lhs_phase_2 = table[(left_output, third)]
                right_output, right_phase = table[(second, third)]
                rhs_output, rhs_phase_2 = table[(first, right_output)]
                if (
                    lhs_output != rhs_output
                    or (left_phase + lhs_phase_2 - right_phase - rhs_phase_2) % 2
                ):
                    associative = False
    return AlgebraVerificationCertificate(
        unit_verified=unit,
        closure_verified=closure,
        associativity_verified=associative,
        separability_source_theorem=True,
        braided_commutative=braided_commutative,
        obstruction_free=unit and closure and associative,
        verification_scope=(
            "Exact normalized Z2-valued multiplication/cochain replay; "
            "separability is source-locked for these finite semisimple toric algebras."
        ),
    )


def _toric_algebra(species_id: str) -> AlgebraObjectRecord:
    algebra_ids = {
        "1": "A_1",
        "S_e": "A_1_plus_e",
        "S_m": "A_1_plus_m",
        "S_psi": "A_1_plus_psi",
        "S_em": "A_full_mu0",
        "S_me": "A_full_mu1",
    }
    definitions = {
        "1": (("1",), "unique", "trivial", True),
        "S_e": (("1", "e"), "unique", "trivial", True),
        "S_m": (("1", "m"), "unique", "trivial", True),
        "S_psi": (("1", "psi"), "unique", "trivial", False),
        "S_em": (
            ("1", "e", "m", "psi"),
            "mu_0_trivial_discrete_torsion",
            "trivial_H2_class",
            False,
        ),
        "S_me": (
            ("1", "e", "m", "psi"),
            "mu_1_nontrivial_discrete_torsion",
            "nontrivial_H2_class",
            False,
        ),
    }
    support, multiplication_class, gauge_class, commutative = definitions[species_id]
    multiplication = _toric_multiplication(support, multiplication_class)
    certificate = _verify_toric_algebra(support, multiplication, commutative)
    if not certificate.verified:
        raise ArithmeticError("source-locked toric algebra certificate failed")
    return AlgebraObjectRecord(
        algebra_id=algebra_ids[species_id],
        simple_object_multiplicities=tuple((label, 1) for label in support),
        unit_object="1",
        multiplication_class=multiplication_class,
        cochain_gauge_class=gauge_class,
        multiplication=multiplication,
        certificate=certificate,
        evidence_status=EvidenceStatus.COMPUTED_EXACT,
        source=TORIC_SOURCE,
    )


def _actions(*rows: Tuple[str, Sequence[str]]) -> Tuple[BulkSectorAction, ...]:
    return tuple(
        BulkSectorAction(
            input_sector,
            tuple((output, 1) for output in outputs),
        )
        for input_sector, outputs in rows
    )


TORIC_ACTIONS = {
    "1": _actions(
        ("1", ("1",)), ("e", ("e",)), ("m", ("m",)), ("psi", ("psi",))
    ),
    "S_e": _actions(
        ("1", ("1", "e")), ("e", ("1", "e")), ("m", ()), ("psi", ())
    ),
    "S_m": _actions(
        ("1", ("1", "m")), ("e", ()), ("m", ("1", "m")), ("psi", ())
    ),
    "S_psi": _actions(
        ("1", ("1",)), ("e", ("m",)), ("m", ("e",)), ("psi", ("psi",))
    ),
    "S_em": _actions(
        ("1", ("1", "e")), ("e", ()), ("m", ("1", "e")), ("psi", ())
    ),
    "S_me": _actions(
        ("1", ("1", "m")), ("e", ("1", "m")), ("m", ()), ("psi", ())
    ),
}


def toric_2d_defect_classification(
    backend: FiniteIntegerBackend,
    *,
    equivalence_relation: str = "oriented_morita",
) -> AbelianInterfaceClassification:
    """Return the six source-locked toric species from the generic enumerator."""

    metric = zd_toric_metric_model(2, backend).metric
    generic = classify_abelian_interfaces(
        metric,
        metric,
        backend,
        budget=CondensateEnumerationBudget(
            max_work_units=1_000_000,
            max_results=100_000,
            max_elements=1_000,
            max_subgroups=100_000,
        ),
        max_pages=100,
        equivalence_relation="oriented_morita",
    )
    desired_generators = {
        "S_e": ((1, 0, 0, 0), (0, 0, 1, 0)),
        "S_em": ((1, 0, 0, 0), (0, 0, 0, 1)),
        "S_me": ((0, 1, 0, 0), (0, 0, 1, 0)),
        "S_m": ((0, 1, 0, 0), (0, 0, 0, 1)),
        "1": ((1, 0, 1, 0), (0, 1, 0, 1)),
        "S_psi": ((1, 0, 0, 1), (0, 1, 1, 0)),
    }
    by_support = {item.folded_support: item for item in generic.species}
    mapped = {}
    for species_id, generators in desired_generators.items():
        subgroup = generic.folded_metric.group.subgroup(
            _matrix_from_columns(generators, 4), backend
        )
        source = by_support.get(subgroup)
        if source is None:
            raise ArithmeticError(
                "generic folded enumerator missed toric species " + species_id
            )
        kind = {
            "1": "identity",
            "S_e": "cheshire_condensate",
            "S_m": "cheshire_condensate",
            "S_psi": "invertible_descendant_em_duality",
            "S_em": "oriented_mixed_noninvertible_condensation",
            "S_me": "oriented_mixed_noninvertible_condensation",
        }[species_id]
        mapped[species_id] = replace(
            source,
            species_id=species_id,
            display_label=species_id,
            domain_id="z2_toric_2d_oriented_descendant_defects",
            species_kind=kind,
            algebra=_toric_algebra(species_id),
            morita_class_id="morita:" + species_id,
            orientation_reverse_id=TORIC_ORIENTATION_REVERSE[species_id],
            invertible=species_id in {"1", "S_psi"},
            bulk_sector_action=TORIC_ACTIONS[species_id],
            evidence_status=EvidenceStatus.COMPUTED_EXACT,
            microscopic_realization_constructed=True,
            missing_obligations=(
                "thermodynamic spectral gap is not inferred from finite realizations",
                "minimum circuit depth is not claimed",
            ),
        )
    records = tuple(mapped[item] for item in TORIC_SPECIES_ORDER)
    if len(records) != 6 or len(by_support) != 6:
        raise ArithmeticError("toric folded classification is not exactly six species")
    certificate = replace(
        generic.certificate,
        lagrangian_species_count=6,
        classification_complete=True,
        toric_literature_crosswalk_verified=True,
        transcript_hash=canonical_hash(
            "mobility_toolkit.toric_2d_six_defect_crosswalk.v2",
            {
                "folded_enumeration": generic.certificate,
                "species": records,
            },
        ),
    )
    return replace(
        generic,
        species=records,
        orbits=_classification_orbits(records, equivalence_relation),
        equivalence_relation=equivalence_relation,
        certificate=certificate,
        assumptions=generic.assumptions
        + (
            "paper labels use the left-to-right action convention of Eq. (6.38)",
        ),
        warnings=(
            "S_e and S_m are strict Cheshire condensates; S_psi, S_em, and S_me are distinct descendant/condensation-defect kinds.",
            "The finite lattice realizations and circuits do not prove a thermodynamic spectral gap or optimal circuit depth.",
        ),
    )


_TRIVIAL_COEFFICIENT = FusionCoefficient1D(
    coefficient_id="1d_trivial",
    tqft_kind="trivial_1_plus_1d_tqft",
    gauge_group=None,
    partition_function_shadow_on_interval=1,
    numeric_scalar=False,
    evidence_status=EvidenceStatus.SOURCE_THEOREM,
    source="arXiv:2204.02407 Sec. 6.3",
)
_Z2_COEFFICIENT = FusionCoefficient1D(
    coefficient_id="1d_z2_gauge_theory",
    tqft_kind="finite_gauge_theory_1_plus_1d",
    gauge_group="Z2",
    partition_function_shadow_on_interval=2,
    numeric_scalar=False,
    evidence_status=EvidenceStatus.SOURCE_THEOREM,
    source="arXiv:2204.02407 Eq. (6.37); coefficient is a 1+1D TQFT",
)


def _toric_nonidentity_fusion_rules() -> dict:
    z2 = "z2"
    rules = {
        ("S_e", "S_e"): ("S_e", z2),
        ("S_e", "S_m"): ("S_em", "trivial"),
        ("S_em", "S_em"): ("S_em", "trivial"),
        ("S_m", "S_m"): ("S_m", z2),
        ("S_e", "S_psi"): ("S_em", "trivial"),
        ("S_em", "S_me"): ("S_e", z2),
        ("S_psi", "S_psi"): ("1", "trivial"),
        ("S_psi", "S_m"): ("S_em", "trivial"),
        ("S_me", "S_em"): ("S_m", z2),
        ("S_e", "S_em"): ("S_em", z2),
        ("S_m", "S_em"): ("S_m", "trivial"),
        ("S_psi", "S_em"): ("S_m", "trivial"),
        ("S_m", "S_me"): ("S_me", z2),
        ("S_e", "S_me"): ("S_e", "trivial"),
        ("S_psi", "S_me"): ("S_e", "trivial"),
    }
    for (left, right), (output, coefficient) in tuple(rules.items()):
        reversed_key = (
            TORIC_ORIENTATION_REVERSE[right],
            TORIC_ORIENTATION_REVERSE[left],
        )
        reversed_value = (
            TORIC_ORIENTATION_REVERSE[output],
            coefficient,
        )
        existing = rules.get(reversed_key)
        if existing is not None and existing != reversed_value:
            raise ArithmeticError("toric fusion orientation reversal is inconsistent")
        rules[reversed_key] = reversed_value
    return rules


TORIC_FUSION_RULES = _toric_nonidentity_fusion_rules()


def fuse_toric_2d_species(
    left_species_id: str, right_species_id: str
) -> FusionResult:
    """Evaluate the complete ordered toric six-species fusion table."""

    if left_species_id not in TORIC_SPECIES_ORDER:
        raise ValueError("unknown toric left species: " + left_species_id)
    if right_species_id not in TORIC_SPECIES_ORDER:
        raise ValueError("unknown toric right species: " + right_species_id)
    if left_species_id == "1":
        output, coefficient = right_species_id, "trivial"
    elif right_species_id == "1":
        output, coefficient = left_species_id, "trivial"
    else:
        output, coefficient = TORIC_FUSION_RULES[(left_species_id, right_species_id)]
    coefficient_value = (
        _Z2_COEFFICIENT if coefficient == "z2" else _TRIVIAL_COEFFICIENT
    )
    result = FusionResult(
        left_species_id=left_species_id,
        right_species_id=right_species_id,
        ordered=True,
        terms=(FusionTerm(output, coefficient_value),),
        evidence_status=EvidenceStatus.COMPUTED_EXACT,
        source_basis=(
            "arXiv:2204.02407 Eq. (6.37), completed by orientation reversal "
            "and the identity unit"
        ),
        verified=True,
    )
    reversed_result_key = (
        TORIC_ORIENTATION_REVERSE[right_species_id],
        TORIC_ORIENTATION_REVERSE[left_species_id],
    )
    if reversed_result_key != (left_species_id, right_species_id):
        if reversed_result_key[0] == "1":
            reversed_output = reversed_result_key[1]
        elif reversed_result_key[1] == "1":
            reversed_output = reversed_result_key[0]
        else:
            reversed_output = TORIC_FUSION_RULES[reversed_result_key][0]
        if reversed_output != TORIC_ORIENTATION_REVERSE[output]:
            raise ArithmeticError("toric ordered fusion fails orientation reversal")
    return result


def toric_2d_fusion_table() -> Tuple[FusionResult, ...]:
    table = tuple(
        fuse_toric_2d_species(left, right)
        for left in TORIC_SPECIES_ORDER
        for right in TORIC_SPECIES_ORDER
    )
    if len(table) != 36:
        raise ArithmeticError("toric fusion table is incomplete")
    return table


__all__ = [
    "AbelianInterfaceClassification",
    "AlgebraMultiplicationEntry",
    "AlgebraObjectRecord",
    "AlgebraVerificationCertificate",
    "BulkSectorAction",
    "CheshireEvidenceTier",
    "ClassificationOrbit",
    "DefectSpeciesRecord",
    "EvidenceStatus",
    "FoldedLagrangianEnumerationCertificate",
    "FusionCoefficient1D",
    "FusionResult",
    "FusionTerm",
    "InterfaceClassificationCertificate",
    "PointedAlgebraCochainCertificate",
    "PointedAssociatorEntry",
    "PointedCategoryCochainData",
    "PointedFusionRule",
    "TORIC_ACTIONS",
    "TORIC_ORIENTATION_REVERSE",
    "TORIC_SPECIES_ORDER",
    "classify_abelian_interfaces",
    "fuse_toric_2d_species",
    "pointed_algebra_coboundary_equivalent",
    "toric_2d_defect_classification",
    "toric_2d_fusion_table",
    "verify_pointed_algebra_cochain",
]
