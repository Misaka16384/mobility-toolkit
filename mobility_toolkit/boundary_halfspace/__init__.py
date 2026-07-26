"""Exact geometry, one-sided modules, and bounded-search contracts.

The uniform-prime module path computes ``L_H = L cap P_H`` by an exact
normal-variable saturation.  It still does not claim to construct
``P_boundary``, a relative Ext module, or a quasi-symplectic boundary module.
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
from mobility_toolkit.boundary_halfspace.presentation import (
    OneSidedClearing,
    TangentDepthPolynomial,
    TangentDepthTerm,
    adapt_laurent_polynomial,
    clear_negative_depth,
)
from mobility_toolkit.boundary_halfspace.module_contraction import (
    HalfSpaceContractionCertificate,
    LaurentHalfSpaceSubmodule,
    OneSidedSubmodule,
    clear_submodule_columns,
    contract_laurent_submodule,
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
    "OneSidedClearing",
    "TangentDepthPolynomial",
    "TangentDepthTerm",
    "adapt_laurent_polynomial",
    "clear_negative_depth",
    "HalfSpaceContractionCertificate",
    "LaurentHalfSpaceSubmodule",
    "OneSidedSubmodule",
    "clear_submodule_columns",
    "contract_laurent_submodule",
]
