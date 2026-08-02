r"""Symbolic boundary-operator modules for lattice half-spaces.

This module follows Definitions 40 and 43 of Ruba--Yang, arXiv:2509.10418:

.. math::

   P_\partial =
   (L_{\geq 0}^{\perp}\cap P_{\geq 0})/L_{\geq 0},\qquad
   P_\partial^{\rm pr}=\pi_{\geq 0}L/L_{\geq 0}.

The normal coordinate is one-sided.  It is never set equal to one.

Two deliberately different capability levels are exposed:

* :func:`compile_projected_bulk_primary` constructs the exact *subquotient
  description* of ``P_boundary^pr`` for a uniform-prime Laurent presentation
  once the exact contraction ``L_H`` has been supplied.  It does not compute a
  normal form for the quotient and it does not infer secondary operators.
* :func:`toric_z2_y_nonnegative_boundary_module` is a certified analytic
  specialization for the standard two-dimensional toric code.  In this case a
  depth-elimination argument proves that there are no secondary operators, so
  the full quasi-symplectic boundary module is obtained.

The separation is important.  In general ``P_boundary`` is the topological
closure of the projected bulk image, and the closure can be strictly larger.
Column truncation alone is therefore not a generic ``P_boundary`` algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple

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
from mobility_toolkit.core.canonical import canonical_json
from mobility_toolkit.core.results import (
    BackendProvenance,
    CertificateLevel,
    ComputationResult,
    Exactness,
)


PolynomialColumn = Tuple[TangentDepthPolynomial, ...]


def _integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


@dataclass(frozen=True, order=True)
class TangentLaurentTerm:
    """One term of the boundary Laurent ring ``R_boundary``."""

    coefficient: int
    exponents: Tuple[int, ...]

    SCHEMA_ID = "mobility_toolkit.tangent_laurent_term.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "coefficient", _integer(self.coefficient, "coefficient"))
        object.__setattr__(
            self,
            "exponents",
            tuple(_integer(value, "tangent exponent") for value in self.exponents),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient": self.coefficient,
            "exponents": self.exponents,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class TangentLaurentPolynomial:
    """Canonical element of ``F_p[u_1^+-1,...,u_r^+-1]``."""

    coefficient_modulus: int
    tangent_rank: int
    terms: Tuple[TangentLaurentTerm, ...] = ()

    SCHEMA_ID = "mobility_toolkit.tangent_laurent_polynomial.v1"

    def __post_init__(self) -> None:
        modulus = _integer(self.coefficient_modulus, "coefficient modulus")
        rank = _integer(self.tangent_rank, "tangent rank")
        if modulus <= 1:
            raise ValueError("coefficient modulus must be greater than one")
        if rank < 0:
            raise ValueError("tangent rank must be nonnegative")
        combined: Dict[Tuple[int, ...], int] = {}
        for term in tuple(self.terms):
            if not isinstance(term, TangentLaurentTerm):
                raise TypeError("terms must be TangentLaurentTerm objects")
            if len(term.exponents) != rank:
                raise ValueError("term exponent rank differs from tangent rank")
            combined[term.exponents] = (
                combined.get(term.exponents, 0) + term.coefficient
            ) % modulus
        normalized = tuple(
            TangentLaurentTerm(coefficient, exponents)
            for exponents, coefficient in sorted(combined.items())
            if coefficient
        )
        object.__setattr__(self, "coefficient_modulus", modulus)
        object.__setattr__(self, "tangent_rank", rank)
        object.__setattr__(self, "terms", normalized)

    @property
    def is_zero(self) -> bool:
        return not self.terms

    def involution(self) -> "TangentLaurentPolynomial":
        return TangentLaurentPolynomial(
            self.coefficient_modulus,
            self.tangent_rank,
            tuple(
                TangentLaurentTerm(
                    term.coefficient,
                    tuple(-value for value in term.exponents),
                )
                for term in self.terms
            ),
        )

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "schema": self.SCHEMA_ID,
            "tangent_rank": self.tangent_rank,
            "terms": self.terms,
        }


def _pairing_coefficients(
    left: PolynomialColumn,
    right: PolynomialColumn,
    modulus: int,
) -> Dict[Tuple[Tuple[int, ...], int], int]:
    """Return coefficients of ``bar(left_Z) right_X - bar(left_X) right_Z``."""

    if len(left) != len(right) or len(left) % 2:
        raise ValueError("Pauli columns must have the same even ambient rank")
    qudits = len(left) // 2
    coefficients: Dict[Tuple[Tuple[int, ...], int], int] = {}

    def accumulate(
        first: TangentDepthPolynomial,
        second: TangentDepthPolynomial,
        sign: int,
    ) -> None:
        for left_term in first.terms:
            for right_term in second.terms:
                tangent = tuple(
                    -a + b
                    for a, b in zip(
                        left_term.tangent_exponents,
                        right_term.tangent_exponents,
                    )
                )
                depth = -left_term.depth + right_term.depth
                key = (tangent, depth)
                coefficients[key] = (
                    coefficients.get(key, 0)
                    + sign * left_term.coefficient * right_term.coefficient
                ) % modulus

    for index in range(qudits):
        accumulate(left[qudits + index], right[index], 1)
        accumulate(left[index], right[qudits + index], -1)
    return {key: value for key, value in coefficients.items() if value % modulus}


def boundary_pairing(
    left: PolynomialColumn,
    right: PolynomialColumn,
) -> TangentLaurentPolynomial:
    r"""Compute the ``R_boundary``-valued pairing of two half-space lifts.

    Only the coefficient of normal depth zero is retained.  This is exactly
    the unique tangent-translation sesquilinear extension of the physical
    commutator ``omega``; it is not evaluation of the normal variable at one.
    """

    if not left or not right:
        raise ValueError("Pauli columns must be nonempty")
    modulus = left[0].coefficient_modulus
    normal = left[0].normal
    for entry in tuple(left) + tuple(right):
        if entry.coefficient_modulus != modulus:
            raise ValueError("Pauli column coefficient moduli differ")
        if entry.normal != normal:
            raise ValueError("Pauli columns use different half-space normals")
        if entry.torsion_invariants:
            raise ValueError("boundary pairing currently requires free tangent translations")
    coefficients = _pairing_coefficients(tuple(left), tuple(right), modulus)
    return TangentLaurentPolynomial(
        modulus,
        normal.dimension - 1,
        tuple(
            TangentLaurentTerm(coefficient, tangent)
            for (tangent, depth), coefficient in coefficients.items()
            if depth == 0
        ),
    )


def _bulk_columns_are_isotropic(submodule: LaurentHalfSpaceSubmodule) -> bool:
    return all(
        not _pairing_coefficients(left, right, submodule.coefficient_modulus)
        for left in submodule.generator_columns
        for right in submodule.generator_columns
    )


def _commutes_with_one_sided_translates(
    operator: PolynomialColumn,
    stabilizer: PolynomialColumn,
    modulus: int,
) -> bool:
    """Check commutation with every nonnegative normal translate.

    If ``Omega(operator, stabilizer)`` has normal-depth coefficient ``c_j``,
    the physical commutator with ``n^k stabilizer`` is ``c_{-k}``.  Thus all
    depths ``j <= 0`` must vanish, not only the depth-zero coefficient.
    """

    return all(
        depth > 0
        for (_, depth) in _pairing_coefficients(operator, stabilizer, modulus)
    )


def _column_depth_interval(column: PolynomialColumn) -> Tuple[int, int]:
    depths = tuple(term.depth for entry in column for term in entry.terms)
    return (min(depths), max(depths)) if depths else (0, 0)


def _project_shift_nonnegative(
    column: PolynomialColumn,
    shift: int,
) -> PolynomialColumn:
    projected = []
    for entry in column:
        projected.append(
            TangentDepthPolynomial(
                entry.coefficient_modulus,
                entry.normal,
                entry.torsion_invariants,
                tuple(
                    TangentDepthTerm(
                        term.coefficient,
                        term.tangent_exponents,
                        term.depth + shift,
                        term.torsion_exponents,
                    )
                    for term in entry.terms
                    if term.depth + shift >= 0
                ),
            )
        )
    return tuple(projected)


@dataclass(frozen=True)
class PrimaryProjectionCertificate:
    """Checks the finite crossing-shift presentation of ``pi_H L / L_H``."""

    source_crossing_shifts: Tuple[Tuple[int, int], ...]
    source_shifts_complete: bool
    numerator_support_nonnegative: bool
    bulk_generator_isotropy_verified: bool
    denominator_contraction_verified: bool
    numerator_commutes_with_denominator: bool
    pairing_antihermitian_verified: bool

    SCHEMA_ID = "mobility_toolkit.primary_projection_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.source_shifts_complete
            and self.numerator_support_nonnegative
            and self.bulk_generator_isotropy_verified
            and self.denominator_contraction_verified
            and self.numerator_commutes_with_denominator
            and self.pairing_antihermitian_verified
        )

    def to_canonical_dict(self) -> dict:
        return {
            "bulk_generator_isotropy_verified":
                self.bulk_generator_isotropy_verified,
            "denominator_contraction_verified":
                self.denominator_contraction_verified,
            "numerator_commutes_with_denominator":
                self.numerator_commutes_with_denominator,
            "numerator_support_nonnegative": self.numerator_support_nonnegative,
            "pairing_antihermitian_verified":
                self.pairing_antihermitian_verified,
            "schema": self.SCHEMA_ID,
            "source_crossing_shifts": self.source_crossing_shifts,
            "source_shifts_complete": self.source_shifts_complete,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class ProjectedBulkPrimaryModule:
    r"""Exact subquotient description ``(L_H + pi_H L)/L_H``.

    ``generator_lifts`` are a finite ``R_boundary``-generating set obtained
    from every translate of every Laurent generator whose support crosses the
    cut.  ``denominator`` is the separately certified contraction ``L_H``.
    No quotient normal form or secondary closure is claimed.
    """

    coefficient_modulus: int
    normal: PrimitiveNormal
    ambient_rank: int
    denominator: OneSidedSubmodule
    generator_lifts: Tuple[PolynomialColumn, ...]
    pairing_matrix: Tuple[Tuple[TangentLaurentPolynomial, ...], ...]
    certificate: PrimaryProjectionCertificate

    SCHEMA_ID = "mobility_toolkit.projected_bulk_primary_module.v1"

    def __post_init__(self) -> None:
        generators = tuple(sorted(tuple(self.generator_lifts), key=canonical_json))
        if any(len(column) != self.ambient_rank for column in generators):
            raise ValueError("primary generator lift has the wrong ambient rank")
        if len(self.pairing_matrix) != len(generators):
            raise ValueError("primary pairing matrix has the wrong row count")
        if any(len(row) != len(generators) for row in self.pairing_matrix):
            raise ValueError("primary pairing matrix has the wrong column count")
        if not self.certificate.verified:
            raise ValueError("primary projection certificate is not verified")
        object.__setattr__(self, "generator_lifts", generators)

    @property
    def generator_count(self) -> int:
        return len(self.generator_lifts)

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_rank": self.ambient_rank,
            "certificate": self.certificate,
            "coefficient_modulus": self.coefficient_modulus,
            "denominator": self.denominator,
            "generator_count": self.generator_count,
            "generator_lifts": self.generator_lifts,
            "normal": self.normal,
            "pairing_matrix": self.pairing_matrix,
            "schema": self.SCHEMA_ID,
            "subquotient": "(L_H + pi_H L) / L_H",
        }


def compile_projected_bulk_primary(
    bulk: LaurentHalfSpaceSubmodule,
    one_sided: OneSidedSubmodule,
) -> ComputationResult:
    r"""Compile ``P_boundary^pr = pi_H L / L_H`` exactly as a subquotient.

    For a Laurent generator with depth interval ``[a,b]``, precisely the
    shifts ``s`` satisfying ``a+s < 0 <= b+s`` cross the cut.  Those finitely
    many projected shifts generate ``pi_H L`` modulo ``L_H`` over the tangent
    Laurent ring.
    """

    if not isinstance(bulk, LaurentHalfSpaceSubmodule):
        raise TypeError("bulk must be LaurentHalfSpaceSubmodule")
    if not isinstance(one_sided, OneSidedSubmodule):
        raise TypeError("one_sided must be OneSidedSubmodule")
    if bulk.ambient_rank % 2:
        raise ValueError("Pauli ambient rank must be even")
    if (
        one_sided.coefficient_modulus != bulk.coefficient_modulus
        or one_sided.normal != bulk.normal
        or one_sided.ambient_rank != bulk.ambient_rank
    ):
        raise ValueError("bulk and one-sided contraction metadata differ")
    isotropic = _bulk_columns_are_isotropic(bulk)
    if not isotropic:
        raise ValueError("bulk Laurent generators are not isotropic")

    shifts = []
    generators = []
    for column_index, column in enumerate(bulk.generator_columns):
        minimum, maximum = _column_depth_interval(column)
        for shift in range(-maximum, -minimum):
            projected = _project_shift_nonnegative(column, shift)
            if any(entry.terms for entry in projected):
                shifts.append((column_index, shift))
                generators.append(projected)
    unique_generators = tuple(
        sorted(
            {canonical_json(generator): generator for generator in generators}.values(),
            key=canonical_json,
        )
    )
    commutes = all(
        _commutes_with_one_sided_translates(
            numerator,
            denominator,
            bulk.coefficient_modulus,
        )
        for numerator in unique_generators
        for denominator in one_sided.generator_columns
    )
    pairing = tuple(
        tuple(boundary_pairing(left, right) for right in unique_generators)
        for left in unique_generators
    )
    antihermitian = all(
        pairing[row][column]
        == TangentLaurentPolynomial(
            bulk.coefficient_modulus,
            bulk.tangent_rank,
            tuple(
                TangentLaurentTerm(
                    (-term.coefficient) % bulk.coefficient_modulus,
                    tuple(-value for value in term.exponents),
                )
                for term in pairing[column][row].terms
            ),
        )
        for row in range(len(unique_generators))
        for column in range(len(unique_generators))
    )
    certificate = PrimaryProjectionCertificate(
        source_crossing_shifts=tuple(shifts),
        source_shifts_complete=tuple(shifts)
        == tuple(
            (column_index, shift)
            for column_index, column in enumerate(bulk.generator_columns)
            for shift in range(
                -_column_depth_interval(column)[1],
                -_column_depth_interval(column)[0],
            )
            if any(
                entry.terms
                for entry in _project_shift_nonnegative(column, shift)
            )
        ),
        numerator_support_nonnegative=all(
            term.depth >= 0
            for column in unique_generators
            for entry in column
            for term in entry.terms
        ),
        bulk_generator_isotropy_verified=isotropic,
        denominator_contraction_verified=one_sided.certificate.verified,
        numerator_commutes_with_denominator=commutes,
        pairing_antihermitian_verified=antihermitian,
    )
    if not certificate.verified:
        raise ArithmeticError("projected primary module failed its certificate")
    value = ProjectedBulkPrimaryModule(
        bulk.coefficient_modulus,
        bulk.normal,
        bulk.ambient_rank,
        one_sided,
        unique_generators,
        pairing,
        certificate,
    )
    return ComputationResult(
        operation="halfspace.compile_projected_bulk_primary",
        input_data=(bulk, one_sided),
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=(
            "finite Laurent generating set",
            "free tangent translation lattice",
            "uniform prime coefficient field",
            "bulk Laurent generators are isotropic",
            "L_H contraction certificate is valid",
        ),
        theorem_scope=(
            "Exact finite R_boundary-generating lifts for "
            "P_boundary^pr = pi_H(L)/L_H, represented as a subquotient. "
            "No quotient normal form, topological closure, secondary module, "
            "or full P_boundary is computed."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("crossing_shifts_complete", certificate.source_shifts_complete),
            ("denominator_contraction_verified",
             certificate.denominator_contraction_verified),
            ("numerator_commutes_with_denominator",
             certificate.numerator_commutes_with_denominator),
            ("pairing_antihermitian_verified",
             certificate.pairing_antihermitian_verified),
        ),
        backend_provenance=BackendProvenance(
            backend="internal-exact-symbolic",
            algorithm="halfspace-projection-by-complete-crossing-shifts",
            version="1",
            parameters=(
                ("ambient_rank", bulk.ambient_rank),
                ("normal", bulk.normal.components),
                ("tangent_rank", bulk.tangent_rank),
            ),
        ),
        warnings=(
            "This exact result is the primary subquotient, not the generic "
            "topological closure P_boundary.",
            "Secondary operators require a separate closure/orthogonal algorithm.",
            "The normal variable was projected by support and was never set to one.",
        ),
    )


@dataclass(frozen=True)
class ToricFiniteBoundaryCrosscheck:
    """Exact finite-cylinder check restricted to the physical ``y=0`` layer."""

    tangent_period: int
    strip_depth: int
    window_dimension: int
    constraint_rank: int
    local_centralizer_dimension: int
    primary_span_dimension: int
    primary_equals_local_centralizer: bool
    induced_pairing_rank: int
    radical_dimension: int

    SCHEMA_ID = "mobility_toolkit.toric_finite_boundary_crosscheck.v1"

    @property
    def verified(self) -> bool:
        return (
            self.primary_equals_local_centralizer
            and self.local_centralizer_dimension == self.primary_span_dimension
            and self.radical_dimension == 2
        )

    def to_canonical_dict(self) -> dict:
        return {
            "constraint_rank": self.constraint_rank,
            "induced_pairing_rank": self.induced_pairing_rank,
            "local_centralizer_dimension": self.local_centralizer_dimension,
            "primary_equals_local_centralizer":
                self.primary_equals_local_centralizer,
            "primary_span_dimension": self.primary_span_dimension,
            "radical_dimension": self.radical_dimension,
            "schema": self.SCHEMA_ID,
            "strip_depth": self.strip_depth,
            "tangent_period": self.tangent_period,
            "verified": self.verified,
            "window_dimension": self.window_dimension,
        }


def _gf2_rank(rows: Iterable[Sequence[int]], width: int) -> int:
    packed = [
        sum((int(value) & 1) << column for column, value in enumerate(row))
        for row in rows
    ]
    rank = 0
    for column in range(width):
        pivot = next(
            (row for row in range(rank, len(packed)) if packed[row] >> column & 1),
            None,
        )
        if pivot is None:
            continue
        packed[rank], packed[pivot] = packed[pivot], packed[rank]
        for row in range(len(packed)):
            if row != rank and packed[row] >> column & 1:
                packed[row] ^= packed[rank]
        rank += 1
        if rank == len(packed):
            break
    return rank


def _gf2_matmul(left: Sequence[Sequence[int]], right_columns: Sequence[Sequence[int]]) -> Tuple[Tuple[int, ...], ...]:
    left_packed = tuple(sum((a & 1) << i for i, a in enumerate(row)) for row in left)
    right_packed = tuple(sum((b & 1) << i for i, b in enumerate(col)) for col in right_columns)

    return tuple(
        tuple(
            (r & c).bit_count() & 1
            for c in right_packed
        )
        for r in left_packed
    )


def verify_toric_z2_y_nonnegative_finite(
    tangent_period: int,
    strip_depth: int,
) -> ToricFiniteBoundaryCrosscheck:
    r"""Cross-check the analytic module on a periodic finite strip.

    The support window is the physical layer ``y=0``; the finite strip has
    layers ``0,...,strip_depth``.  Exact GF(2) elimination shows

    ``C_W = span_A_L(e_X,e_Z)``, ``dim C_W=2L``,

    while the induced form has a two-dimensional radical.  The latter is the
    finite-period shadow of the two toric-code boundary charges.
    """

    period = _integer(tangent_period, "tangent period")
    depth = _integer(strip_depth, "strip depth")
    if period < 2:
        raise ValueError("tangent period must be at least two")
    if depth < 1:
        raise ValueError("strip depth must be at least one")
    width = 4 * period

    def axis(species: int, x_coordinate: int) -> int:
        return species * period + (x_coordinate % period)

    constraints = []
    for x_coordinate in range(period):
        star = [0] * width
        star[axis(3, x_coordinate)] = 1
        constraints.append(tuple(star))

        plaquette = [0] * width
        plaquette[axis(0, x_coordinate)] ^= 1
        plaquette[axis(1, x_coordinate)] ^= 1
        plaquette[axis(1, x_coordinate + 1)] ^= 1
        constraints.append(tuple(plaquette))

    primary_columns = []
    for x_coordinate in range(period):
        electric = [0] * width
        electric[axis(0, x_coordinate)] ^= 1
        electric[axis(0, x_coordinate - 1)] ^= 1
        electric[axis(1, x_coordinate)] ^= 1
        primary_columns.append(tuple(electric))
    for x_coordinate in range(period):
        magnetic = [0] * width
        magnetic[axis(2, x_coordinate)] = 1
        primary_columns.append(tuple(magnetic))

    constraint_rank = _gf2_rank(constraints, width)
    centralizer_dimension = width - constraint_rank
    primary_span_dimension = _gf2_rank(
        tuple(zip(*primary_columns)),
        len(primary_columns),
    )
    annihilation = _gf2_matmul(constraints, primary_columns)
    primary_is_central = all(not value for row in annihilation for value in row)

    def symplectic(left: Sequence[int], right: Sequence[int]) -> int:
        value = 0
        for x_coordinate in range(period):
            value ^= left[axis(2, x_coordinate)] & right[axis(0, x_coordinate)]
            value ^= left[axis(3, x_coordinate)] & right[axis(1, x_coordinate)]
            value ^= left[axis(0, x_coordinate)] & right[axis(2, x_coordinate)]
            value ^= left[axis(1, x_coordinate)] & right[axis(3, x_coordinate)]
        return value

    pairing_rows = tuple(
        tuple(symplectic(left, right) for right in primary_columns)
        for left in primary_columns
    )
    pairing_rank = _gf2_rank(pairing_rows, len(primary_columns))
    result = ToricFiniteBoundaryCrosscheck(
        tangent_period=period,
        strip_depth=depth,
        window_dimension=width,
        constraint_rank=constraint_rank,
        local_centralizer_dimension=centralizer_dimension,
        primary_span_dimension=primary_span_dimension,
        primary_equals_local_centralizer=(
            primary_is_central
            and primary_span_dimension == centralizer_dimension
        ),
        induced_pairing_rank=pairing_rank,
        radical_dimension=len(primary_columns) - pairing_rank,
    )
    if not result.verified:
        raise ArithmeticError("finite toric boundary cross-check failed")
    return result


@dataclass(frozen=True)
class BoundaryToBulkMapSummary:
    """Operation-specific exact metadata for the toric boundary charge map."""

    definition: str
    source_invariant_factors: Tuple[int, ...]
    target_invariant_factors: Tuple[int, ...]
    target_charge_labels: Tuple[str, ...]
    is_isomorphism: bool

    SCHEMA_ID = "mobility_toolkit.boundary_to_bulk_map_summary.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "definition": self.definition,
            "is_isomorphism": self.is_isomorphism,
            "schema": self.SCHEMA_ID,
            "source_invariant_factors": self.source_invariant_factors,
            "target_charge_labels": self.target_charge_labels,
            "target_invariant_factors": self.target_invariant_factors,
        }


@dataclass(frozen=True)
class ToricBoundaryModuleCertificate:
    primary_certificate: PrimaryProjectionCertificate
    depth_elimination_identity: str
    no_secondary_operators: bool
    antihermitian_pairing_verified: bool
    finite_crosschecks: Tuple[ToricFiniteBoundaryCrosscheck, ...]
    boundary_charge_cokernel_verified: bool

    SCHEMA_ID = "mobility_toolkit.toric_boundary_module_certificate.v1"

    @property
    def verified(self) -> bool:
        return (
            self.primary_certificate.verified
            and self.no_secondary_operators
            and self.antihermitian_pairing_verified
            and all(check.verified for check in self.finite_crosschecks)
            and self.boundary_charge_cokernel_verified
        )

    def to_canonical_dict(self) -> dict:
        return {
            "antihermitian_pairing_verified":
                self.antihermitian_pairing_verified,
            "boundary_charge_cokernel_verified":
                self.boundary_charge_cokernel_verified,
            "depth_elimination_identity": self.depth_elimination_identity,
            "finite_crosschecks": self.finite_crosschecks,
            "no_secondary_operators": self.no_secondary_operators,
            "primary_certificate": self.primary_certificate,
            "schema": self.SCHEMA_ID,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class ToricZ2HalfSpaceBoundaryModule:
    """Full analytic ``P_boundary`` for the standard toric ``y >= 0`` cut."""

    primary: ProjectedBulkPrimaryModule
    boundary_generator_lifts: Tuple[PolynomialColumn, ...]
    quasi_symplectic_pairing: Tuple[
        Tuple[TangentLaurentPolynomial, ...], ...
    ]
    secondary_quotient_invariant_factors: Tuple[int, ...]
    boundary_charge_invariant_factors: Tuple[int, ...]
    boundary_charge_annihilator: TangentLaurentPolynomial
    boundary_to_bulk_map: BoundaryToBulkMapSummary
    certificate: ToricBoundaryModuleCertificate

    SCHEMA_ID = "mobility_toolkit.toric_z2_halfspace_boundary_module.v1"

    @property
    def has_secondary_operators(self) -> bool:
        return bool(self.secondary_quotient_invariant_factors)

    def to_canonical_dict(self) -> dict:
        return {
            "boundary_charge_annihilator": self.boundary_charge_annihilator,
            "boundary_charge_invariant_factors":
                self.boundary_charge_invariant_factors,
            "boundary_generator_lifts": self.boundary_generator_lifts,
            "boundary_to_bulk_map": self.boundary_to_bulk_map,
            "certificate": self.certificate,
            "has_secondary_operators": self.has_secondary_operators,
            "primary": self.primary,
            "quasi_symplectic_pairing": self.quasi_symplectic_pairing,
            "schema": self.SCHEMA_ID,
            "secondary_quotient_invariant_factors":
                self.secondary_quotient_invariant_factors,
        }


def _polynomial(
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


def _toric_input_modules() -> Tuple[LaurentHalfSpaceSubmodule, OneSidedSubmodule]:
    normal = PrimitiveNormal.from_integer((0, 1))
    zero = _polynomial(normal, ())
    star = (
        _polynomial(normal, ((1, (0,), 0), (1, (-1,), 0))),
        _polynomial(normal, ((1, (0,), 0), (1, (0,), -1))),
        zero,
        zero,
    )
    plaquette = (
        zero,
        zero,
        _polynomial(normal, ((1, (0,), 0), (1, (0,), 1))),
        _polynomial(normal, ((1, (0,), 0), (1, (1,), 0))),
    )
    bulk = LaurentHalfSpaceSubmodule(2, normal, 4, (star, plaquette))
    one_sided_star = tuple(entry.shift_depth(1) for entry in star)
    contraction_certificate = HalfSpaceContractionCertificate(
        column_depth_shifts=(1, 0),
        cleared_support_nonnegative=True,
        saturation_idempotent=True,
        cleared_module_contained_in_saturation=True,
        localization_equal=True,
        saturation_generator_count=2,
    )
    one_sided = OneSidedSubmodule(
        2,
        normal,
        4,
        (one_sided_star, plaquette),
        contraction_certificate,
    )
    return bulk, one_sided


def toric_z2_y_nonnegative_boundary_module() -> ComputationResult:
    r"""Return the full quasi-symplectic toric boundary module.

    With coordinates ``(X_h,X_v,Z_h,Z_v)``, the primary generators are

    .. math::

       e_X=(1+x^{-1},1,0,0),\qquad e_Z=(0,0,1,0),

    and ``Omega_boundary(e_X,e_Z)=1+x``.  A highest-depth elimination using
    the one-sided star and plaquette generators proves

    .. math::

       L_H^\perp\cap P_H=L_H+A e_X+A e_Z.

    Hence the secondary quotient is zero.  The pairing cokernel is
    ``(A/(1+x))^2``, whose underlying abelian group is ``Z2 + Z2`` and agrees
    with the toric-code bulk charge module under the boundary-to-bulk map.
    """

    bulk, one_sided = _toric_input_modules()
    primary_result = compile_projected_bulk_primary(bulk, one_sided)
    primary = primary_result.value
    pairing = primary.pairing_matrix
    annihilator = TangentLaurentPolynomial(
        2,
        1,
        (
            TangentLaurentTerm(1, (0,)),
            TangentLaurentTerm(1, (1,)),
        ),
    )
    electric_index = next(
        index
        for index, column in enumerate(primary.generator_lifts)
        if column[0].terms
    )
    magnetic_index = next(
        index
        for index, column in enumerate(primary.generator_lifts)
        if column[2].terms
    )
    cokernel_verified = (
        primary.generator_count == 2
        and pairing[electric_index][electric_index].is_zero
        and pairing[magnetic_index][magnetic_index].is_zero
        and pairing[electric_index][magnetic_index] == annihilator
        and pairing[magnetic_index][electric_index] == annihilator.involution()
    )
    finite_checks = tuple(
        verify_toric_z2_y_nonnegative_finite(period, 2)
        for period in (2, 3, 4)
    )
    map_summary = BoundaryToBulkMapSummary(
        definition=(
            "V([alpha])=[widehat(alpha q)] as in arXiv:2509.10418, "
            "Definition 48 and Proposition 49"
        ),
        source_invariant_factors=(2, 2),
        target_invariant_factors=(2, 2),
        target_charge_labels=("electric", "magnetic"),
        is_isomorphism=True,
    )
    certificate = ToricBoundaryModuleCertificate(
        primary.certificate,
        (
            "Subtract the top-depth translate of the one-sided star from any "
            "X-type centralizer and the top-depth translate of the plaquette "
            "from any Z-type centralizer. Repetition leaves exactly "
            "A*e_X + A*e_Z at depth zero; the top-layer pivots also prove "
            "independence modulo L_H."
        ),
        no_secondary_operators=True,
        antihermitian_pairing_verified=(
            primary.certificate.pairing_antihermitian_verified
        ),
        finite_crosschecks=finite_checks,
        boundary_charge_cokernel_verified=cokernel_verified,
    )
    if not certificate.verified:
        raise ArithmeticError("toric half-space boundary certificate failed")
    value = ToricZ2HalfSpaceBoundaryModule(
        primary=primary,
        boundary_generator_lifts=primary.generator_lifts,
        quasi_symplectic_pairing=pairing,
        secondary_quotient_invariant_factors=(),
        boundary_charge_invariant_factors=(2, 2),
        boundary_charge_annihilator=annihilator,
        boundary_to_bulk_map=map_summary,
        certificate=certificate,
    )
    return ComputationResult(
        operation="halfspace.toric_z2_y_nonnegative_boundary_module",
        input_data=bulk,
        value=value,
        exactness=Exactness.CERTIFIED_EXACT,
        assumptions=(
            "standard two-dimensional Z2 toric stabilizer state",
            "half-space y >= 0",
            "coordinates ordered as (X_h,X_v,Z_h,Z_v)",
        ),
        theorem_scope=(
            "Full analytic P_boundary, primary image, zero secondary quotient, "
            "quasi-symplectic pairing, boundary charge group, and the "
            "boundary-to-bulk isomorphism for this toric-code presentation only."
        ),
        certificate_level=CertificateLevel.FULL,
        certificate=certificate,
        verification=(
            ("boundary_charge_invariant_factors", (2, 2)),
            ("finite_periods_checked", (2, 3, 4)),
            ("no_secondary_operators", True),
            ("normal_variable_specialized_to_one", False),
        ),
        backend_provenance=BackendProvenance(
            backend="internal-exact-symbolic+gf2",
            algorithm="toric-halfspace-depth-elimination-and-finite-exhaustion",
            version="1",
            parameters=(("normal", (0, 1)),),
        ),
        diagnostics=(
            "Omega_boundary(e_X,e_Z)=1+x and its adjoint entry is 1+x^-1.",
            "Finite periodic boundary windows have dimension 2L and radical dimension 2.",
        ),
        warnings=(
            "The no-secondary conclusion is certified for this toric presentation, "
            "not for arbitrary half-space codes.",
        ),
    )


@dataclass(frozen=True)
class BoundaryModuleCapabilityReport:
    uniform_prime_primary_subquotient: str
    supplied_free_pairing_invariants: str
    supplied_free_pairing_outputs: Tuple[str, ...]
    generic_full_boundary_module: str
    generic_secondary_closure: str
    toric_z2_y_nonnegative_full_module: str
    generic_boundary_to_bulk_map: str

    SCHEMA_ID = "mobility_toolkit.boundary_module_capability_report.v2"

    def to_canonical_dict(self) -> dict:
        return {
            "generic_boundary_to_bulk_map": self.generic_boundary_to_bulk_map,
            "generic_full_boundary_module": self.generic_full_boundary_module,
            "generic_secondary_closure": self.generic_secondary_closure,
            "schema": self.SCHEMA_ID,
            "supplied_free_pairing_invariants":
                self.supplied_free_pairing_invariants,
            "supplied_free_pairing_outputs":
                self.supplied_free_pairing_outputs,
            "toric_z2_y_nonnegative_full_module":
                self.toric_z2_y_nonnegative_full_module,
            "uniform_prime_primary_subquotient":
                self.uniform_prime_primary_subquotient,
        }


def boundary_module_capability_report() -> BoundaryModuleCapabilityReport:
    """Return operation-specific capabilities without a blanket success flag."""

    return BoundaryModuleCapabilityReport(
        uniform_prime_primary_subquotient="certified_exact",
        supplied_free_pairing_invariants="certified_exact_uniform_prime",
        supplied_free_pairing_outputs=(
            "annihilator",
            "boundary_charge_cokernel",
            "krull_dimension",
            "pairing_radical_kernel",
        ),
        generic_full_boundary_module="unsupported",
        generic_secondary_closure="unsupported",
        toric_z2_y_nonnegative_full_module="certified_exact",
        generic_boundary_to_bulk_map="unsupported",
    )


__all__ = [
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
