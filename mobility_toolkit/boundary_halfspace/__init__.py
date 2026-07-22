"""Exact lattice geometry and bounded-search contracts for half-spaces.

This package deliberately contains no symbolic boundary-module computation.
In particular, constructing a :class:`HalfSpaceSemigroup` does not claim that
``L_H``, ``P_boundary``, a relative Ext module, or a quasi-symplectic boundary
module has been computed.
"""

from mobility_toolkit.boundary_halfspace.geometry import (
    HalfSpaceSemigroup,
    OneSidedSupportDescriptor,
    OrientationRelation,
    OrientedHalfSpace,
    PrimitiveNormal,
    SemigroupCoordinate,
    UnimodularBasisCertificate,
    UnimodularBasisChange,
    compare_orientations,
)
from mobility_toolkit.boundary_halfspace.search import (
    AncillaBound,
    BoundedPeriodicSearchDomain,
    GeneratorSupportBound,
    HalfSpaceCapabilityReport,
    ResourceBound,
    SearchSpaceCertificate,
    SearchTermination,
    halfspace_capability_report,
)

__all__ = [
    "AncillaBound",
    "BoundedPeriodicSearchDomain",
    "GeneratorSupportBound",
    "HalfSpaceCapabilityReport",
    "HalfSpaceSemigroup",
    "OneSidedSupportDescriptor",
    "OrientationRelation",
    "OrientedHalfSpace",
    "PrimitiveNormal",
    "ResourceBound",
    "SearchSpaceCertificate",
    "SearchTermination",
    "SemigroupCoordinate",
    "UnimodularBasisCertificate",
    "UnimodularBasisChange",
    "compare_orientations",
    "halfspace_capability_report",
]
