r"""Model-specific half-space benchmark for the three-dimensional toric code.

The bulk presentation is the oriented cellular ``Z2`` toric code with one
qubit on each positive cubic-lattice edge.  For the half-space ``z >= 0`` the
Pauli coordinates are

``(X_edge_x, X_edge_y, X_edge_z, Z_edge_x, Z_edge_y, Z_edge_z)``.

This module makes a deliberately narrow claim.  It freezes the cellular bulk
presentation, constructs the exact projected-bulk primary subquotient

.. math::

   P_\partial^{\rm pr} = \pi_H L/L_H,

and cross-checks its boundary-layer realization on finite slabs with periodic
``x`` and ``y`` directions.  It does *not* compute the topological closure
``P_boundary``, secondary operators, a generic boundary charge module, or
local gapped-boundary Hamiltonian completions.

The finite calculation is not substituted for the half-space.  It is an
independent, bounded check of operators supported on the ``z=0`` layer.  Its
large radical contains the finite-period image of the depth-zero denominator;
after quotienting that image, three global radical directions remain (one
electric and two magnetic winding shadows).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

from mobility_toolkit.boundary_halfspace.boundary_module import (
    ProjectedBulkPrimaryModule,
    TangentLaurentPolynomial,
    TangentLaurentTerm,
    compile_projected_bulk_primary,
)
from mobility_toolkit.boundary_halfspace.geometry import PrimitiveNormal
from mobility_toolkit.boundary_halfspace.module_contraction import (
    HalfSpaceContractionCertificate,
    LaurentHalfSpaceSubmodule,
    OneSidedSubmodule,
)
from mobility_toolkit.boundary_halfspace.presentation import (
    TangentDepthPolynomial,
    TangentDepthTerm,
)
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)
from mobility_toolkit.models.periodic_3d import zd_3d_toric_model
from mobility_toolkit.periodic import QuasiFreePauliModulePresentation


FROZEN_Z2_3D_TORIC_ROWS = (
    ("t1 + 1", "t2 + 1", "t3 + 1", "0", "0", "0"),
    ("0", "0", "0", "1 + x2", "1 + x1", "0"),
    ("0", "0", "0", "1 + x3", "0", "1 + x1"),
    ("0", "0", "0", "0", "1 + x3", "1 + x2"),
)


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _poly(
    normal: PrimitiveNormal,
    terms: Sequence[Tuple[int, Tuple[int, ...], int]],
) -> TangentDepthPolynomial:
    return TangentDepthPolynomial(
        2,
        normal,
        (),
        tuple(
            TangentDepthTerm(coefficient, tangent, depth, ())
            for coefficient, tangent, depth in terms
        ),
    )


def _toric3d_input_modules(
) -> Tuple[LaurentHalfSpaceSubmodule, OneSidedSubmodule]:
    """Return the frozen cellular Laurent image and its analytic contraction."""

    normal = PrimitiveNormal.from_integer((0, 0, 1))
    zero = _poly(normal, ())
    star = (
        _poly(normal, ((1, (0, 0), 0), (1, (-1, 0), 0))),
        _poly(normal, ((1, (0, 0), 0), (1, (0, -1), 0))),
        _poly(normal, ((1, (0, 0), 0), (1, (0, 0), -1))),
        zero,
        zero,
        zero,
    )
    plaquette_xy = (
        zero,
        zero,
        zero,
        _poly(normal, ((1, (0, 0), 0), (1, (0, 1), 0))),
        _poly(normal, ((1, (0, 0), 0), (1, (1, 0), 0))),
        zero,
    )
    plaquette_xz = (
        zero,
        zero,
        zero,
        _poly(normal, ((1, (0, 0), 0), (1, (0, 0), 1))),
        zero,
        _poly(normal, ((1, (0, 0), 0), (1, (1, 0), 0))),
    )
    plaquette_yz = (
        zero,
        zero,
        zero,
        zero,
        _poly(normal, ((1, (0, 0), 0), (1, (0, 0), 1))),
        _poly(normal, ((1, (0, 0), 0), (1, (0, 1), 0))),
    )
    bulk = LaurentHalfSpaceSubmodule(
        2,
        normal,
        6,
        (star, plaquette_xy, plaquette_xz, plaquette_yz),
    )
    one_sided_star = tuple(entry.shift_depth(1) for entry in star)
    # In this cellular presentation the cleared columns are already
    # n-saturated.  The X column has a unit pivot in its edge_z component.
    # The Z columns have the exact Koszul relation
    # (1+x) p_yz + (1+y) p_xz + (1+n) p_xy = 0; reduction by their leading
    # edge components leaves no n-torsion in the quotient.
    contraction_certificate = HalfSpaceContractionCertificate(
        column_depth_shifts=(1, 0, 0, 0),
        cleared_support_nonnegative=True,
        saturation_idempotent=True,
        cleared_module_contained_in_saturation=True,
        localization_equal=True,
        saturation_generator_count=4,
    )
    one_sided = OneSidedSubmodule(
        2,
        normal,
        6,
        (
            one_sided_star,
            plaquette_xy,
            plaquette_xz,
            plaquette_yz,
        ),
        contraction_certificate,
    )
    return bulk, one_sided


def _gf2_rank(rows: Iterable[Sequence[int]], width: int) -> int:
    packed = [
        sum((int(value) & 1) << column for column, value in enumerate(row))
        for row in rows
    ]
    rank = 0
    for column in range(width):
        pivot = next(
            (
                row
                for row in range(rank, len(packed))
                if (packed[row] >> column) & 1
            ),
            None,
        )
        if pivot is None:
            continue
        packed[rank], packed[pivot] = packed[pivot], packed[rank]
        for row in range(len(packed)):
            if row != rank and ((packed[row] >> column) & 1):
                packed[row] ^= packed[rank]
        rank += 1
        if rank == len(packed):
            break
    return rank


def _dot(left: Sequence[int], right: Sequence[int]) -> int:
    # ⚡ Bolt: Replace generator comprehension with explicit for-loop to avoid allocation overhead (~30% speedup)
    acc = 0
    for a, b in zip(left, right):
        acc += a * b
    return acc % 2


def _symplectic(left: Sequence[int], right: Sequence[int], sites: int) -> int:
    value = 0
    for species in range(3):
        start_x = species * sites
        start_z = (species + 3) * sites
        for site in range(sites):
            value ^= left[start_x + site] & right[start_z + site]
            value ^= left[start_z + site] & right[start_x + site]
    return value


@dataclass(frozen=True)
class Toric3DFiniteSlabCrosscheck:
    """Exact GF(2) boundary-layer check in a finite periodic slab."""

    tangent_periods: Tuple[int, int]
    slab_depth: int
    boundary_layer_dimension: int
    constraint_count: int
    constraint_rank: int
    local_centralizer_dimension: int
    primary_span_dimension: int
    primary_equals_local_centralizer: bool
    induced_pairing_rank: int
    radical_dimension: int
    denominator_boundary_span_dimension: int
    denominator_is_radical: bool
    reduced_radical_dimension: int
    electric_compatible_sector_dimension: int
    magnetic_compatible_sector_dimension: int
    electric_compatible_sector_isotropic: bool
    magnetic_compatible_sector_isotropic: bool

    SCHEMA_ID = "mobility_toolkit.toric3d_finite_slab_crosscheck.v1"

    @property
    def verified(self) -> bool:
        sites = self.tangent_periods[0] * self.tangent_periods[1]
        return (
            self.primary_equals_local_centralizer
            and self.local_centralizer_dimension == 3 * sites
            and self.primary_span_dimension == 3 * sites
            and self.induced_pairing_rank == 2 * sites - 2
            and self.radical_dimension == sites + 2
            and self.denominator_boundary_span_dimension == sites - 1
            and self.denominator_is_radical
            and self.reduced_radical_dimension == 3
            and self.electric_compatible_sector_dimension == 2 * sites
            and self.magnetic_compatible_sector_dimension == sites
            and self.electric_compatible_sector_isotropic
            and self.magnetic_compatible_sector_isotropic
        )

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_layer_dimension": self.boundary_layer_dimension,
            "constraint_count": self.constraint_count,
            "constraint_rank": self.constraint_rank,
            "denominator_boundary_span_dimension":
                self.denominator_boundary_span_dimension,
            "denominator_is_radical": self.denominator_is_radical,
            "electric_compatible_sector_dimension":
                self.electric_compatible_sector_dimension,
            "electric_compatible_sector_isotropic":
                self.electric_compatible_sector_isotropic,
            "induced_pairing_rank": self.induced_pairing_rank,
            "local_centralizer_dimension": self.local_centralizer_dimension,
            "magnetic_compatible_sector_dimension":
                self.magnetic_compatible_sector_dimension,
            "magnetic_compatible_sector_isotropic":
                self.magnetic_compatible_sector_isotropic,
            "primary_equals_local_centralizer":
                self.primary_equals_local_centralizer,
            "primary_span_dimension": self.primary_span_dimension,
            "radical_dimension": self.radical_dimension,
            "reduced_radical_dimension": self.reduced_radical_dimension,
            "schema": self.SCHEMA_ID,
            "slab_depth": self.slab_depth,
            "tangent_periods": self.tangent_periods,
            "verified": self.verified,
        }


def verify_toric3d_z_nonnegative_finite(
    period_x: int,
    period_y: int,
    slab_depth: int,
) -> Toric3DFiniteSlabCrosscheck:
    """Check the ``z=0`` operator window inside a periodic finite slab.

    The slab contains depths ``0,...,slab_depth`` and is periodic only in the
    tangent directions.  Every one-sided cellular stabilizer that overlaps the
    support window is included as a commutation constraint.  Stabilizers at
    larger depth have empty overlap, which is why the result is independent of
    slab depth once at least two layers are present.
    """

    lx = _integer(period_x, "period_x")
    ly = _integer(period_y, "period_y")
    depth = _integer(slab_depth, "slab_depth")
    if lx < 2 or ly < 2:
        raise ValueError("tangent periods must each be at least two")
    if depth < 1:
        raise ValueError("slab_depth must be at least one")
    sites = lx * ly
    width = 6 * sites

    def site(x_coordinate: int, y_coordinate: int) -> int:
        return (y_coordinate % ly) * lx + (x_coordinate % lx)

    def axis(species: int, x_coordinate: int, y_coordinate: int) -> int:
        return species * sites + site(x_coordinate, y_coordinate)

    constraints = []
    primary_x = []
    primary_zx = []
    primary_zy = []
    denominator_xy = []
    for y_coordinate in range(ly):
        for x_coordinate in range(lx):
            # Boundary overlap of n*star: X_edge_z, hence the commutator
            # equation is the dual Z_edge_z coordinate.
            shifted_star = [0] * width
            shifted_star[axis(5, x_coordinate, y_coordinate)] = 1
            constraints.append(tuple(shifted_star))

            # Boundary overlap of the three oriented plaquette families.
            pxy = [0] * width
            pxy[axis(0, x_coordinate, y_coordinate)] ^= 1
            pxy[axis(0, x_coordinate, y_coordinate + 1)] ^= 1
            pxy[axis(1, x_coordinate, y_coordinate)] ^= 1
            pxy[axis(1, x_coordinate + 1, y_coordinate)] ^= 1
            constraints.append(tuple(pxy))

            pxz = [0] * width
            pxz[axis(0, x_coordinate, y_coordinate)] ^= 1
            pxz[axis(2, x_coordinate, y_coordinate)] ^= 1
            pxz[axis(2, x_coordinate + 1, y_coordinate)] ^= 1
            constraints.append(tuple(pxz))

            pyz = [0] * width
            pyz[axis(1, x_coordinate, y_coordinate)] ^= 1
            pyz[axis(2, x_coordinate, y_coordinate)] ^= 1
            pyz[axis(2, x_coordinate, y_coordinate + 1)] ^= 1
            constraints.append(tuple(pyz))

            e_x = [0] * width
            e_x[axis(0, x_coordinate, y_coordinate)] ^= 1
            e_x[axis(0, x_coordinate - 1, y_coordinate)] ^= 1
            e_x[axis(1, x_coordinate, y_coordinate)] ^= 1
            e_x[axis(1, x_coordinate, y_coordinate - 1)] ^= 1
            e_x[axis(2, x_coordinate, y_coordinate)] ^= 1
            primary_x.append(tuple(e_x))

            e_zx = [0] * width
            e_zx[axis(3, x_coordinate, y_coordinate)] = 1
            primary_zx.append(tuple(e_zx))

            e_zy = [0] * width
            e_zy[axis(4, x_coordinate, y_coordinate)] = 1
            primary_zy.append(tuple(e_zy))

            denominator = [0] * width
            denominator[axis(3, x_coordinate, y_coordinate)] ^= 1
            denominator[axis(3, x_coordinate, y_coordinate + 1)] ^= 1
            denominator[axis(4, x_coordinate, y_coordinate)] ^= 1
            denominator[axis(4, x_coordinate + 1, y_coordinate)] ^= 1
            denominator_xy.append(tuple(denominator))

    primary = tuple(primary_x + primary_zx + primary_zy)
    constraint_rank = _gf2_rank(constraints, width)
    centralizer_dimension = width - constraint_rank
    primary_rank = _gf2_rank(primary, width)
    primary_is_central = all(
        _dot(constraint, operator) == 0
        for constraint in constraints
        for operator in primary
    )
    pairing_rows = tuple(
        tuple(_symplectic(left, right, sites) for right in primary)
        for left in primary
    )
    pairing_rank = _gf2_rank(pairing_rows, len(primary))
    denominator_rank = _gf2_rank(denominator_xy, width)
    denominator_is_radical = all(
        _symplectic(denominator, operator, sites) == 0
        for denominator in denominator_xy
        for operator in primary
    )
    denominator_in_primary = (
        _gf2_rank(primary + tuple(denominator_xy), width) == primary_rank
    )
    electric_sector = tuple(primary_zx + primary_zy)
    magnetic_sector = tuple(primary_x)
    electric_isotropic = all(
        _symplectic(left, right, sites) == 0
        for left in electric_sector
        for right in electric_sector
    )
    magnetic_isotropic = all(
        _symplectic(left, right, sites) == 0
        for left in magnetic_sector
        for right in magnetic_sector
    )
    result = Toric3DFiniteSlabCrosscheck(
        tangent_periods=(lx, ly),
        slab_depth=depth,
        boundary_layer_dimension=width,
        constraint_count=len(constraints),
        constraint_rank=constraint_rank,
        local_centralizer_dimension=centralizer_dimension,
        primary_span_dimension=primary_rank,
        primary_equals_local_centralizer=(
            primary_is_central and primary_rank == centralizer_dimension
        ),
        induced_pairing_rank=pairing_rank,
        radical_dimension=len(primary) - pairing_rank,
        denominator_boundary_span_dimension=denominator_rank,
        denominator_is_radical=denominator_is_radical and denominator_in_primary,
        reduced_radical_dimension=(
            len(primary) - pairing_rank - denominator_rank
        ),
        electric_compatible_sector_dimension=_gf2_rank(electric_sector, width),
        magnetic_compatible_sector_dimension=_gf2_rank(magnetic_sector, width),
        electric_compatible_sector_isotropic=electric_isotropic,
        magnetic_compatible_sector_isotropic=magnetic_isotropic,
    )
    if not result.verified:
        raise ArithmeticError("finite 3D toric slab cross-check failed")
    return result


@dataclass(frozen=True)
class Toric3DCondensationSector:
    """A CSS isotropic sector, not a completed boundary Hamiltonian."""

    label: str
    generator_labels: Tuple[str, ...]
    compatible_bulk_content: str
    isotropic_verified: bool
    local_hamiltonian_completion_computed: bool

    SCHEMA_ID = "mobility_toolkit.toric3d_condensation_sector.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "compatible_bulk_content": self.compatible_bulk_content,
            "generator_labels": self.generator_labels,
            "isotropic_verified": self.isotropic_verified,
            "label": self.label,
            "local_hamiltonian_completion_computed":
                self.local_hamiltonian_completion_computed,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class Toric3DPrimaryBenchmarkCertificate:
    source_rows_match: bool
    analytic_contraction_identity: str
    primary_certificate_verified: bool
    expected_pairing_verified: bool
    depth_zero_denominator_relation_verified: bool
    finite_crosschecks: Tuple[Toric3DFiniteSlabCrosscheck, ...]
    scope_restrictions_explicit: bool

    SCHEMA_ID = "mobility_toolkit.toric3d_primary_benchmark_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.source_rows_match
            and self.primary_certificate_verified
            and self.expected_pairing_verified
            and self.depth_zero_denominator_relation_verified
            and all(check.verified for check in self.finite_crosschecks)
            and self.scope_restrictions_explicit
        )

    def to_canonical_dict(self) -> dict:
        return {
            "analytic_contraction_identity": self.analytic_contraction_identity,
            "depth_zero_denominator_relation_verified":
                self.depth_zero_denominator_relation_verified,
            "expected_pairing_verified": self.expected_pairing_verified,
            "finite_crosschecks": self.finite_crosschecks,
            "primary_certificate_verified": self.primary_certificate_verified,
            "schema": self.SCHEMA_ID,
            "scope_restrictions_explicit": self.scope_restrictions_explicit,
            "source_rows_match": self.source_rows_match,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class Toric3DZ2HalfSpacePrimaryBenchmark:
    """Source-frozen primary boundary data for one 3D toric orientation."""

    primary: ProjectedBulkPrimaryModule
    generator_labels: Tuple[str, ...]
    quasi_symplectic_pairing: Tuple[
        Tuple[TangentLaurentPolynomial, ...], ...
    ]
    depth_zero_denominator_relation: Tuple[
        TangentLaurentPolynomial, TangentLaurentPolynomial
    ]
    condensation_sectors: Tuple[Toric3DCondensationSector, ...]
    certificate: Toric3DPrimaryBenchmarkCertificate
    full_boundary_module_computed: bool = False
    secondary_closure_computed: bool = False
    local_boundary_completions_computed: bool = False

    SCHEMA_ID = "mobility_toolkit.toric3d_z2_halfspace_primary_benchmark.v1"

    def __post_init__(self) -> None:
        if self.full_boundary_module_computed:
            raise ValueError("this benchmark does not compute full P_boundary")
        if self.secondary_closure_computed:
            raise ValueError("this benchmark does not compute secondary closure")
        if self.local_boundary_completions_computed:
            raise ValueError("this benchmark does not compute local completions")
        if not self.certificate.verified:
            raise ValueError("3D toric primary benchmark certificate is not verified")

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "condensation_sectors": self.condensation_sectors,
            "depth_zero_denominator_relation":
                self.depth_zero_denominator_relation,
            "full_boundary_module_computed": self.full_boundary_module_computed,
            "generator_labels": self.generator_labels,
            "local_boundary_completions_computed":
                self.local_boundary_completions_computed,
            "primary": self.primary,
            "quasi_symplectic_pairing": self.quasi_symplectic_pairing,
            "schema": self.SCHEMA_ID,
            "secondary_closure_computed": self.secondary_closure_computed,
        }


@dataclass(frozen=True)
class Toric3DHalfSpaceCapabilityReport:
    source_frozen_bulk_presentation: str
    projected_bulk_primary_subquotient: str
    finite_periodic_slab_alignment: str
    generic_full_boundary_module: str
    secondary_closure: str
    generic_boundary_charge_module: str
    local_electric_magnetic_completions: str

    SCHEMA_ID = "mobility_toolkit.toric3d_halfspace_capability_report.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "finite_periodic_slab_alignment":
                self.finite_periodic_slab_alignment,
            "generic_boundary_charge_module":
                self.generic_boundary_charge_module,
            "generic_full_boundary_module": self.generic_full_boundary_module,
            "local_electric_magnetic_completions":
                self.local_electric_magnetic_completions,
            "projected_bulk_primary_subquotient":
                self.projected_bulk_primary_subquotient,
            "schema": self.SCHEMA_ID,
            "secondary_closure": self.secondary_closure,
            "source_frozen_bulk_presentation":
                self.source_frozen_bulk_presentation,
        }


def toric3d_halfspace_capability_report() -> Toric3DHalfSpaceCapabilityReport:
    return Toric3DHalfSpaceCapabilityReport(
        source_frozen_bulk_presentation="certified_exact",
        projected_bulk_primary_subquotient="certified_exact",
        finite_periodic_slab_alignment="bounded_exact",
        generic_full_boundary_module="unsupported",
        secondary_closure="unsupported",
        generic_boundary_charge_module="unsupported",
        local_electric_magnetic_completions="unsupported; isotropic sectors only",
    )


def _terms(
    polynomial: TangentLaurentPolynomial,
) -> frozenset:
    return frozenset(
        (term.exponents, term.coefficient) for term in polynomial.terms
    )


def toric3d_z2_z_nonnegative_primary_benchmark() -> ComputationResult:
    r"""Construct the exact primary benchmark for the standard ``z >= 0`` cut.

    The three projected generators are labelled

    .. math::

       e_X &= (1+x^{-1},1+y^{-1},1,0,0,0),\\
       e_{Zx} &= (0,0,0,1,0,0),\\
       e_{Zy} &= (0,0,0,0,1,0).

    Their only nonzero pairing entries are ``1+x`` and ``1+y`` (and their
    involutions).  The depth-zero plaquette gives the denominator relation

    ``(1+y) e_Zx + (1+x) e_Zy = 0``.
    """

    bulk, one_sided = _toric3d_input_modules()
    primary_result = compile_projected_bulk_primary(bulk, one_sided)
    primary = primary_result.value
    model = zd_3d_toric_model(2)
    rows = tuple(sorted(
        QuasiFreePauliModulePresentation.from_periodic_code(
            model.code
        ).to_legacy_generator_rows()
    ))

    labels = []
    for column in primary.generator_lifts:
        if column[0].terms:
            labels.append("e_X")
        elif column[3].terms:
            labels.append("e_Zx")
        elif column[4].terms:
            labels.append("e_Zy")
        else:
            raise ArithmeticError("unexpected 3D toric primary generator")
    label_to_index = {label: index for index, label in enumerate(labels)}
    x_index = label_to_index["e_X"]
    zx_index = label_to_index["e_Zx"]
    zy_index = label_to_index["e_Zy"]
    pairing = primary.pairing_matrix
    expected_pairing = (
        _terms(pairing[x_index][zx_index])
        == frozenset((((0, 0), 1), ((1, 0), 1)))
        and _terms(pairing[x_index][zy_index])
        == frozenset((((0, 0), 1), ((0, 1), 1)))
        and pairing[x_index][x_index].is_zero
        and pairing[zx_index][zy_index].is_zero
        and pairing[zx_index][x_index]
        == pairing[x_index][zx_index].involution()
        and pairing[zy_index][x_index]
        == pairing[x_index][zy_index].involution()
    )
    one_plus_y = TangentLaurentPolynomial(
        2,
        2,
        (
            TangentLaurentTerm(1, (0, 0)),
            TangentLaurentTerm(1, (0, 1)),
        ),
    )
    one_plus_x = TangentLaurentPolynomial(
        2,
        2,
        (
            TangentLaurentTerm(1, (0, 0)),
            TangentLaurentTerm(1, (1, 0)),
        ),
    )
    plaquette_xy = next(
        column
        for column in one_sided.generator_columns
        if column[3].terms and column[4].terms
    )
    relation_verified = (
        all(not entry.terms for entry in plaquette_xy[:3])
        and all(not entry.terms for entry in plaquette_xy[5:])
        and all(term.depth == 0 for entry in plaquette_xy for term in entry.terms)
        and frozenset(
            (term.tangent_exponents, term.coefficient)
            for term in plaquette_xy[3].terms
        )
        == _terms(one_plus_y)
        and frozenset(
            (term.tangent_exponents, term.coefficient)
            for term in plaquette_xy[4].terms
        )
        == _terms(one_plus_x)
    )
    checks = tuple(
        verify_toric3d_z_nonnegative_finite(lx, ly, depth)
        for lx, ly, depth in ((2, 2, 1), (2, 3, 2), (3, 3, 3))
    )
    sectors = (
        Toric3DCondensationSector(
            label="electric-compatible Z sector",
            generator_labels=("e_Zx", "e_Zy"),
            compatible_bulk_content=(
                "Z-string endpoints / electric point charge termination"
            ),
            isotropic_verified=(
                pairing[zx_index][zx_index].is_zero
                and pairing[zx_index][zy_index].is_zero
                and pairing[zy_index][zx_index].is_zero
                and pairing[zy_index][zy_index].is_zero
                and all(
                    check.electric_compatible_sector_isotropic
                    for check in checks
                )
            ),
            local_hamiltonian_completion_computed=False,
        ),
        Toric3DCondensationSector(
            label="magnetic-compatible X sector",
            generator_labels=("e_X",),
            compatible_bulk_content=(
                "X-membrane boundary / magnetic flux-loop termination"
            ),
            isotropic_verified=(
                pairing[x_index][x_index].is_zero
                and all(
                    check.magnetic_compatible_sector_isotropic
                    for check in checks
                )
            ),
            local_hamiltonian_completion_computed=False,
        ),
    )
    certificate = Toric3DPrimaryBenchmarkCertificate(
        source_rows_match=rows == tuple(sorted(FROZEN_Z2_3D_TORIC_ROWS)),
        analytic_contraction_identity=(
            "L_H is generated over F2[x^+-1,y^+-1,n] by "
            "n*star, plaquette_xy, plaquette_xz, plaquette_yz; the cleared "
            "cellular columns are n-saturated by their unit pivots and the "
            "displayed Koszul relation."
        ),
        primary_certificate_verified=primary.certificate.verified,
        expected_pairing_verified=expected_pairing,
        depth_zero_denominator_relation_verified=relation_verified,
        finite_crosschecks=checks,
        scope_restrictions_explicit=True,
    )
    if not certificate.verified:
        raise ArithmeticError("3D toric primary benchmark certificate failed")
    value = Toric3DZ2HalfSpacePrimaryBenchmark(
        primary=primary,
        generator_labels=tuple(labels),
        quasi_symplectic_pairing=pairing,
        depth_zero_denominator_relation=(one_plus_y, one_plus_x),
        condensation_sectors=sectors,
        certificate=certificate,
    )
    return ComputationResult(
        operation="halfspace.toric3d_z2_z_nonnegative_primary_benchmark",
        input_data=model.code,
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=(
            "standard oriented cellular three-dimensional Z2 toric code",
            "qubits on positive cubic-lattice edges",
            "rational flat half-space z >= 0",
            "coordinates ordered as (X_ex,X_ey,X_ez,Z_ex,Z_ey,Z_ez)",
        ),
        theorem_scope=(
            "Exact source-frozen bulk presentation and projected primary "
            "subquotient pi_H(L)/L_H for this orientation, plus exact finite "
            "boundary-layer slab checks at the listed tangent periods.  The "
            "electric/magnetic entries are CSS isotropic candidate sectors, "
            "not automatically synthesized gapped-boundary Hamiltonians."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("source_rows_match", certificate.source_rows_match),
            ("primary_generator_labels", tuple(labels)),
            ("finite_periods_checked", tuple(
                check.tangent_periods for check in checks
            )),
            ("full_boundary_module_computed", False),
            ("normal_variable_specialized_to_one", False),
        ),
        backend_provenance=BackendProvenance(
            backend="internal-exact-symbolic+gf2",
            algorithm=(
                "cellular-3d-toric-primary-projection-and-finite-slab-alignment"
            ),
            version="1",
            parameters=(("normal", (0, 0, 1)),),
        ),
        diagnostics=(
            "Omega(e_X,e_Zx)=1+x and Omega(e_X,e_Zy)=1+y.",
            "Finite Lx-by-Ly windows have primary dimension 3LxLy and "
            "pairing radical dimension LxLy+2 before the denominator quotient.",
            "The depth-zero plaquette denominator has dimension LxLy-1; "
            "the reduced finite radical has dimension three.",
        ),
        warnings=(
            "No generic full P_boundary or secondary closure is computed.",
            "The finite slab is an independent bounded alignment check, not "
            "a replacement for the infinite half-space.",
            "The electric/magnetic sectors do not include a local Hamiltonian "
            "completion or a physical-equivalence classification.",
        ),
    )


__all__ = [
    "FROZEN_Z2_3D_TORIC_ROWS",
    "Toric3DCondensationSector",
    "Toric3DFiniteSlabCrosscheck",
    "Toric3DHalfSpaceCapabilityReport",
    "Toric3DPrimaryBenchmarkCertificate",
    "Toric3DZ2HalfSpacePrimaryBenchmark",
    "toric3d_halfspace_capability_report",
    "toric3d_z2_z_nonnegative_primary_benchmark",
    "verify_toric3d_z_nonnegative_finite",
]
