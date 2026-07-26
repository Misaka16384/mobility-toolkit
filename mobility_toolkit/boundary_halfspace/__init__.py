"""Exact geometry, one-sided modules, and boundary-module contracts.

The uniform-prime module path computes ``L_H = L cap P_H`` by an exact
normal-variable saturation.  It also compiles the exact primary subquotient
``pi_H(L)/L_H``.  A full quasi-symplectic ``P_boundary`` is currently
certified only for operation-specific analytic models, beginning with the
standard two-dimensional Z2 toric code.
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
from mobility_toolkit.boundary_halfspace.boundary_module import (
    BoundaryModuleCapabilityReport,
    BoundaryToBulkMapSummary,
    PrimaryProjectionCertificate,
    ProjectedBulkPrimaryModule,
    TangentLaurentPolynomial,
    TangentLaurentTerm,
    ToricBoundaryModuleCertificate,
    ToricFiniteBoundaryCrosscheck,
    ToricZ2HalfSpaceBoundaryModule,
    boundary_module_capability_report,
    boundary_pairing,
    compile_projected_bulk_primary,
    toric_z2_y_nonnegative_boundary_module,
    verify_toric_z2_y_nonnegative_finite,
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
    "BoundaryModuleCapabilityReport",
    "BoundaryToBulkMapSummary",
    "PrimaryProjectionCertificate",
    "ProjectedBulkPrimaryModule",
    "TangentLaurentPolynomial",
    "TangentLaurentTerm",
    "ToricBoundaryModuleCertificate",
    "ToricFiniteBoundaryCrosscheck",
    "ToricZ2HalfSpaceBoundaryModule",
    "boundary_module_capability_report",
    "boundary_pairing",
    "compile_projected_bulk_primary",
    "toric_z2_y_nonnegative_boundary_module",
    "verify_toric_z2_y_nonnegative_finite",
]
