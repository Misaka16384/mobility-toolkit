"""Source-locked X-cube half-space orientation benchmarks.

This module records the two orientation-specific conclusions in Ruba--Yang,
Example 54.  It deliberately does not construct the full boundary operator
module ``P_boundary``.  The presentation and lattice geometry are checked
locally, while the boundary-to-bulk conclusion remains an analytic literature
oracle rather than a machine-derived theorem.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from mobility_toolkit.boundary_halfspace.geometry import (
    HalfSpaceSemigroup,
    OneSidedSupportDescriptor,
    OrientedHalfSpace,
    PrimitiveNormal,
    UnimodularBasisChange,
)
from mobility_toolkit.core import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.models import z2_xcube_model
from mobility_toolkit.periodic import QuasiFreePauliModulePresentation


LaurentRow = Tuple[str, ...]
LaurentMatrixRows = Tuple[LaurentRow, ...]
IntegerVector = Tuple[int, ...]


# The rows are the three columns sigma_1, sigma_2, sigma_3 of Eq. (140),
# rendered in the toolkit's fixed order
# X(edge_x,edge_y,edge_z), Z(edge_x,edge_y,edge_z).
XCUBE_RUBA_YANG_EQ140_ROWS: LaurentMatrixRows = (
    (
        "t1*t2 + t1 + t2 + 1",
        "t2*t3 + t2 + t3 + 1",
        "t1*t3 + t1 + t3 + 1",
        "0",
        "0",
        "0",
    ),
    ("0", "0", "0", "1 + x3", "1 + x1", "0"),
    ("0", "0", "0", "0", "1 + x1", "1 + x2"),
)


# All exponent vectors occurring in Eq. (140).  This is used only to certify
# the orientation-adapted one-sided support envelope; it is not a substitute
# for computing L_H or P_boundary.
_EQ140_SUPPORT: Tuple[IntegerVector, ...] = tuple(
    sorted(
        {
            (0, 0, 0),
            (-1, 0, 0),
            (0, -1, 0),
            (-1, -1, 0),
            (0, 0, -1),
            (0, -1, -1),
            (-1, 0, -1),
            (0, 0, 1),
            (1, 0, 0),
            (0, 1, 0),
        }
    )
)


class BoundaryToBulkBehavior(str, Enum):
    """Only the two conclusions explicitly locked below are represented."""

    NOT_SURJECTIVE = "not_surjective"
    ISOMORPHISM = "isomorphism"


@dataclass(frozen=True)
class XCubeOrientationRequest:
    """An oriented X-cube half-space request."""

    normal: PrimitiveNormal

    SCHEMA_ID = "mobility_toolkit.xcube_orientation_request.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.normal, PrimitiveNormal):
            raise TypeError("normal must be a PrimitiveNormal")
        if self.normal.dimension != 3:
            raise ValueError("X-cube orientation benchmarks require dimension three")

    def to_canonical_dict(self) -> dict:
        return {"normal": self.normal, "schema": self.SCHEMA_ID}


@dataclass(frozen=True)
class XCubeLiteratureSource:
    """Literal provenance and equation locks for the benchmark."""

    arxiv_id: str
    url: str
    title: str
    authors: Tuple[str, ...]
    example: str
    equations: Tuple[str, ...]
    expected_presentation_rows: LaurentMatrixRows

    SCHEMA_ID = "mobility_toolkit.xcube_literature_source.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "arxiv_id": self.arxiv_id,
            "authors": self.authors,
            "equations": self.equations,
            "example": self.example,
            "expected_presentation_rows": self.expected_presentation_rows,
            "schema": self.SCHEMA_ID,
            "title": self.title,
            "url": self.url,
        }


XCUBE_RUBA_YANG_SOURCE = XCubeLiteratureSource(
    arxiv_id="2509.10418",
    url="https://arxiv.org/abs/2509.10418",
    title="Witt Groups and Bulk-Boundary Correspondence for Stabilizer States",
    authors=("Blazej Ruba", "Bowen Yang"),
    example="Example 54",
    equations=("Eq. (138)", "Eq. (140)", "Eq. (141)", "Eq. (144)"),
    expected_presentation_rows=XCUBE_RUBA_YANG_EQ140_ROWS,
)


@dataclass(frozen=True)
class XCubeChargeWitness:
    """The explicit axial obstruction family from Example 54."""

    representative_family: str
    parameters: Tuple[str, ...]
    violated_condition: str
    source_statement: str

    SCHEMA_ID = "mobility_toolkit.xcube_charge_witness.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "parameters": self.parameters,
            "representative_family": self.representative_family,
            "schema": self.SCHEMA_ID,
            "source_statement": self.source_statement,
            "violated_condition": self.violated_condition,
        }


@dataclass(frozen=True)
class XCubeOrientationCertificate:
    """Machine checks around a source-locked, not re-proved, conclusion."""

    source: XCubeLiteratureSource
    observed_presentation_rows: LaurentMatrixRows
    registered_normal: PrimitiveNormal
    basis_change: UnimodularBasisChange
    support_translation: IntegerVector
    original_depth_interval: Tuple[int, int]
    one_sided_support: OneSidedSupportDescriptor
    expected_behavior: BoundaryToBulkBehavior
    expected_source_equation: str
    full_boundary_module_constructed: bool = False

    SCHEMA_ID = "mobility_toolkit.xcube_orientation_certificate.v1"

    @property
    def equation_lock_verified(self) -> bool:
        return (
            self.source.arxiv_id == "2509.10418"
            and self.source.example == "Example 54"
            and self.source.expected_presentation_rows
            == XCUBE_RUBA_YANG_EQ140_ROWS
            # Stabilizer-column order is presentation-irrelevant and the
            # canonical PeriodicCode IR sorts template identifiers.  Compare
            # row multisets, retaining multiplicity rather than using a set.
            and tuple(sorted(self.observed_presentation_rows))
            == tuple(sorted(self.source.expected_presentation_rows))
        )

    @property
    def orientation_lock_verified(self) -> bool:
        locked = {
            (0, 0, 1): (
                BoundaryToBulkBehavior.NOT_SURJECTIVE,
                "Eq. (138) and Example 54 axial counterexample",
            ),
            (1, 1, 1): (
                BoundaryToBulkBehavior.ISOMORPHISM,
                "Eq. (144)",
            ),
        }
        expected = locked.get(self.registered_normal.components)
        return expected == (self.expected_behavior, self.expected_source_equation)

    @property
    def one_sided_support_verified(self) -> bool:
        translation_depth = self.registered_normal.dot(self.support_translation)
        translated = tuple(
            tuple(left + right for left, right in zip(point, self.support_translation))
            for point in _EQ140_SUPPORT
        )
        translated_depths = tuple(
            self.registered_normal.dot(point) for point in translated
        )
        return (
            len(self.support_translation) == 3
            and self.one_sided_support.semigroup.half_space.normal
            == self.registered_normal
            and self.one_sided_support.ambient_displacements
            == tuple(sorted(set(translated)))
            and self.original_depth_interval
            == (
                min(self.registered_normal.dot(point) for point in _EQ140_SUPPORT),
                max(self.registered_normal.dot(point) for point in _EQ140_SUPPORT),
            )
            and translation_depth == max(0, -self.original_depth_interval[0])
            and min(translated_depths) == 0
        )

    @property
    def verified(self) -> bool:
        return (
            self.equation_lock_verified
            and self.orientation_lock_verified
            and self.basis_change.normal == self.registered_normal
            and self.basis_change.certificate.verified
            and self.one_sided_support_verified
            and not self.full_boundary_module_constructed
        )

    def to_canonical_dict(self) -> dict:
        return {
            "basis_change": self.basis_change,
            "equation_lock_verified": self.equation_lock_verified,
            "expected_behavior": self.expected_behavior,
            "expected_source_equation": self.expected_source_equation,
            "full_boundary_module_constructed":
                self.full_boundary_module_constructed,
            "observed_presentation_rows": self.observed_presentation_rows,
            "one_sided_support": self.one_sided_support,
            "one_sided_support_verified": self.one_sided_support_verified,
            "orientation_lock_verified": self.orientation_lock_verified,
            "original_depth_interval": self.original_depth_interval,
            "registered_normal": self.registered_normal,
            "schema": self.SCHEMA_ID,
            "source": self.source,
            "support_translation": self.support_translation,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class XCubeOrientationBenchmark:
    """One registered orientation conclusion, with no implicit extrapolation."""

    model_id: str
    half_space: OrientedHalfSpace
    behavior: BoundaryToBulkBehavior
    conclusion: str
    obstruction_witness: Optional[XCubeChargeWitness]
    certificate: XCubeOrientationCertificate

    SCHEMA_ID = "mobility_toolkit.xcube_orientation_benchmark.v1"

    @property
    def constructs_full_boundary_module(self) -> bool:
        return self.certificate.full_boundary_module_constructed

    def to_canonical_dict(self) -> dict:
        return {
            "behavior": self.behavior,
            "certificate": self.certificate,
            "conclusion": self.conclusion,
            "constructs_full_boundary_module":
                self.constructs_full_boundary_module,
            "half_space": self.half_space,
            "model_id": self.model_id,
            "obstruction_witness": self.obstruction_witness,
            "schema": self.SCHEMA_ID,
        }


def _orientation_geometry(
    normal: PrimitiveNormal,
) -> Tuple[
    UnimodularBasisChange,
    IntegerVector,
    Tuple[int, int],
    OneSidedSupportDescriptor,
]:
    half_space = OrientedHalfSpace(normal)
    basis = half_space.basis_change
    depths = tuple(normal.dot(point) for point in _EQ140_SUPPORT)
    interval = (min(depths), max(depths))
    clearing_depth = max(0, -interval[0])
    translation = tuple(
        clearing_depth * value for value in basis.transverse_vector
    )
    translated = tuple(
        tuple(left + right for left, right in zip(point, translation))
        for point in _EQ140_SUPPORT
    )
    descriptor = HalfSpaceSemigroup.create(half_space).support_descriptor(translated)
    return basis, translation, interval, descriptor


def _unsupported_orientation(
    request: XCubeOrientationRequest,
) -> ComputationResult:
    return ComputationResult(
        operation="halfspace.xcube_orientation_benchmark",
        input_data=request,
        value=None,
        exactness=Exactness.UNSUPPORTED,
        assumptions=("oriented rational lattice half-space through the origin",),
        theorem_scope=(
            "No boundary-to-bulk conclusion is registered for this orientation."
        ),
        certificate_level=CertificateLevel.NONE,
        verification=(
            ("registered_normals", ((0, 0, 1), (1, 1, 1))),
            ("requested_normal", request.normal.components),
        ),
        backend_provenance=BackendProvenance(
            backend="internal-source-lock",
            algorithm="xcube-example54-orientation-registry",
            version="1",
        ),
        warnings=(
            "Example 54 is orientation sensitive; no conclusion is extrapolated "
            "from either registered normal.",
            "This operation does not construct P_boundary.",
        ),
    )


def xcube_orientation_benchmark(normal: PrimitiveNormal) -> ComputationResult:
    """Return the source-locked Example 54 conclusion for ``normal``.

    Supported oriented normals are exactly ``(0,0,1)`` and ``(1,1,1)``.
    Every other normal, including the opposite orientations, receives a
    structured ``unsupported`` result.
    """

    request = XCubeOrientationRequest(normal)
    registered = {
        (0, 0, 1): (
            BoundaryToBulkBehavior.NOT_SURJECTIVE,
            "Eq. (138) and Example 54 axial counterexample",
        ),
        (1, 1, 1): (
            BoundaryToBulkBehavior.ISOMORPHISM,
            "Eq. (144)",
        ),
    }
    case = registered.get(normal.components)
    if case is None:
        return _unsupported_orientation(request)

    behavior, source_equation = case
    model = z2_xcube_model()
    observed_rows = QuasiFreePauliModulePresentation.from_periodic_code(
        model.code
    ).to_legacy_generator_rows()
    basis, translation, interval, support = _orientation_geometry(normal)
    certificate = XCubeOrientationCertificate(
        source=XCUBE_RUBA_YANG_SOURCE,
        observed_presentation_rows=observed_rows,
        registered_normal=normal,
        basis_change=basis,
        support_translation=translation,
        original_depth_interval=interval,
        one_sided_support=support,
        expected_behavior=behavior,
        expected_source_equation=source_equation,
    )
    if not certificate.verified:
        raise ArithmeticError("X-cube literature/source-lock certificate failed")

    if behavior is BoundaryToBulkBehavior.NOT_SURJECTIVE:
        witness = XCubeChargeWitness(
            representative_family="[<x^m y^n z>]",
            parameters=("m in Z", "n in Z"),
            violated_condition="Proposition 52 / Eq. (138)",
            source_statement=(
                "For c >= 0, every displayed class fails the kernel condition "
                "required to lie in the image of V."
            ),
        )
        conclusion = (
            "For the oriented half-space c >= 0, V:E_L->Q_L is not "
            "surjective."
        )
    else:
        witness = None
        conclusion = (
            "For the oriented half-space a+b+c >= 0, Example 54 states that "
            "V:E_L->Q_L is an isomorphism."
        )

    value = XCubeOrientationBenchmark(
        model_id=model.model_id,
        half_space=OrientedHalfSpace(normal),
        behavior=behavior,
        conclusion=conclusion,
        obstruction_witness=witness,
        certificate=certificate,
    )
    return ComputationResult(
        operation="halfspace.xcube_orientation_benchmark",
        input_data=request,
        value=value,
        exactness=Exactness.EXPERIMENTAL,
        assumptions=(
            "R=F2[x^+-1,y^+-1,z^+-1]",
            "L is exactly the image of Ruba--Yang Eq. (140)",
            "oriented rational lattice half-space through the origin",
        ),
        theorem_scope=(
            "The boundary-to-bulk behavior is the orientation-specific analytic "
            "conclusion of Ruba--Yang Example 54. The toolkit verifies the "
            "literal presentation lock and adapted one-sided geometry, but does "
            "not independently re-prove the charge-module statement."
        ),
        certificate_level=CertificateLevel.STANDARD,
        certificate=certificate,
        verification=(
            ("analytic_conclusion_recomputed", False),
            ("equation_lock_verified", certificate.equation_lock_verified),
            ("full_boundary_module_constructed", False),
            ("one_sided_support_verified", certificate.one_sided_support_verified),
            ("orientation_lock_verified", certificate.orientation_lock_verified),
        ),
        backend_provenance=BackendProvenance(
            backend="literature-locked-analytic-oracle",
            algorithm="xcube-example54-orientation-registry",
            version="1",
            parameters=(("normal", normal.components),),
        ),
        diagnostics=(
            conclusion,
            (
                "Eq. (140) support was translated by the certified transverse "
                "basis vector only to verify a one-sided support envelope."
            ),
        ),
        warnings=(
            "experimental denotes that the literature conclusion is not backed "
            "by a complete machine-verifiable algebraic proof in this operation.",
            "No full P_boundary, secondary module, or new orientation theorem "
            "is constructed here.",
        ),
    )


__all__ = [
    "BoundaryToBulkBehavior",
    "XCUBE_RUBA_YANG_EQ140_ROWS",
    "XCUBE_RUBA_YANG_SOURCE",
    "XCubeChargeWitness",
    "XCubeLiteratureSource",
    "XCubeOrientationBenchmark",
    "XCubeOrientationCertificate",
    "XCubeOrientationRequest",
    "xcube_orientation_benchmark",
]
