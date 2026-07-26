"""Exact cellular relative homology for explicit finite pairs.

The pair ``(X, A)`` is represented by a :class:`FiniteCellComplex` ``X`` and
explicit cell IDs for ``A`` in every degree.  Construction rejects ``A`` unless
it is boundary closed.  The relative chain complex is then the literal
coordinate quotient

``C_k(X, A) = C_k(X) / C_k(A)``,

with the canonically sorted cells of ``X_k \\ A_k`` as quotient basis.  This
finite construction is independent of the Laurent/half-space boundary
machinery elsewhere in the package.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from mobility_toolkit.core.canonical import canonical_hash
from mobility_toolkit.core.integer import SparseIntMatrix
from mobility_toolkit.finite.backend import FiniteIntegerBackend
from mobility_toolkit.finite.groups import FiniteQuotient
from mobility_toolkit.geometry.cell_complex import FiniteCellComplex, cellular_homology


@dataclass(frozen=True, order=True)
class SubcomplexBoundaryRecord:
    """The complete integral boundary of one selected cell of ``A``."""

    degree: int
    cell_id: str
    boundary: Tuple[Tuple[str, int], ...]

    SCHEMA_ID = "mobility_toolkit.subcomplex_boundary_record.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "boundary": self.boundary,
            "cell_id": self.cell_id,
            "degree": self.degree,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class RelativeCellularPair:
    """A validated finite cellular pair ``(X, A)``.

    ``subcomplex_cell_ids_by_dimension`` may be supplied in any order.  It is
    normalized to sorted set semantics before the closure test, so the
    canonical identity is independent of input order.
    """

    ambient: FiniteCellComplex
    subcomplex_cell_ids_by_dimension: Tuple[Tuple[str, ...], ...]

    SCHEMA_ID = "mobility_toolkit.relative_cellular_pair.v1"

    def __post_init__(self) -> None:
        if not isinstance(self.ambient, FiniteCellComplex):
            raise TypeError("relative cellular ambient must be a FiniteCellComplex")
        raw_levels = tuple(
            tuple(level) for level in self.subcomplex_cell_ids_by_dimension
        )
        if len(raw_levels) != len(self.ambient.cell_ids_by_dimension):
            raise ValueError(
                "relative subcomplex needs one cell-ID collection per ambient degree"
            )
        for level in raw_levels:
            if any(not isinstance(cell_id, str) or not cell_id for cell_id in level):
                raise ValueError("relative subcomplex cell IDs must be nonempty strings")
        levels = tuple(tuple(sorted(set(level))) for level in raw_levels)
        object.__setattr__(self, "subcomplex_cell_ids_by_dimension", levels)
        self._validate_cells_exist()
        self._validate_boundary_closed()

    @classmethod
    def create(
        cls,
        ambient: FiniteCellComplex,
        subcomplex_cell_ids_by_dimension: Sequence[Sequence[str]],
    ) -> "RelativeCellularPair":
        return cls(
            ambient,
            tuple(tuple(level) for level in subcomplex_cell_ids_by_dimension),
        )

    def _validate_cells_exist(self) -> None:
        for degree, selected in enumerate(self.subcomplex_cell_ids_by_dimension):
            ambient_ids = set(self.ambient.cell_ids_by_dimension[degree])
            missing = tuple(cell_id for cell_id in selected if cell_id not in ambient_ids)
            if missing:
                raise ValueError(
                    f"relative subcomplex degree {degree} names unknown cells: {missing}"
                )

    def _validate_boundary_closed(self) -> None:
        for degree in range(1, self.ambient.dimension + 1):
            upper_ids = self.ambient.cell_ids_by_dimension[degree]
            lower_ids = self.ambient.cell_ids_by_dimension[degree - 1]
            selected_upper = set(self.subcomplex_cell_ids_by_dimension[degree])
            selected_lower = set(self.subcomplex_cell_ids_by_dimension[degree - 1])
            for row, column, coefficient in self.ambient.boundary_maps[degree].entries:
                if (
                    coefficient
                    and upper_ids[column] in selected_upper
                    and lower_ids[row] not in selected_lower
                ):
                    raise ValueError(
                        "relative subcomplex is not boundary closed: "
                        f"boundary of degree-{degree} cell {upper_ids[column]!r} "
                        f"contains unselected cell {lower_ids[row]!r} with "
                        f"coefficient {coefficient}"
                    )

    @property
    def quotient_basis_by_dimension(self) -> Tuple[Tuple[str, ...], ...]:
        return tuple(
            tuple(cell_id for cell_id in ambient if cell_id not in set(selected))
            for ambient, selected in zip(
                self.ambient.cell_ids_by_dimension,
                self.subcomplex_cell_ids_by_dimension,
            )
        )

    @property
    def canonical_identity(self) -> str:
        return canonical_hash(self.SCHEMA_ID, self)

    def to_canonical_dict(self) -> dict:
        return {
            "ambient": self.ambient,
            "schema": self.SCHEMA_ID,
            "subcomplex_cell_ids_by_dimension":
                self.subcomplex_cell_ids_by_dimension,
        }


@dataclass(frozen=True)
class RelativeChainCertificate:
    """Replay data proving the canonical quotient-chain construction."""

    pair_identity: str
    ambient_identity: str
    subcomplex_cell_ids_by_dimension: Tuple[Tuple[str, ...], ...]
    quotient_basis_by_dimension: Tuple[Tuple[str, ...], ...]
    quotient_boundary_maps: Tuple[SparseIntMatrix, ...]
    subcomplex_boundaries: Tuple[SubcomplexBoundaryRecord, ...]
    relative_complex_identity: str

    SCHEMA_ID = "mobility_toolkit.relative_chain_certificate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "ambient_identity": self.ambient_identity,
            "pair_identity": self.pair_identity,
            "quotient_basis_by_dimension": self.quotient_basis_by_dimension,
            "quotient_boundary_maps": self.quotient_boundary_maps,
            "relative_complex_identity": self.relative_complex_identity,
            "schema": self.SCHEMA_ID,
            "subcomplex_boundaries": self.subcomplex_boundaries,
            "subcomplex_cell_ids_by_dimension":
                self.subcomplex_cell_ids_by_dimension,
        }


@dataclass(frozen=True)
class RelativeChainComplex:
    pair: RelativeCellularPair
    chain_complex: FiniteCellComplex
    certificate: RelativeChainCertificate

    SCHEMA_ID = "mobility_toolkit.relative_chain_complex.v1"

    def __post_init__(self) -> None:
        verify_relative_chain_certificate(self.pair, self.certificate)
        if self.chain_complex.cell_ids_by_dimension != (
            self.certificate.quotient_basis_by_dimension
        ):
            raise ValueError("relative chain complex disagrees with certified quotient bases")
        if self.chain_complex.boundary_maps != self.certificate.quotient_boundary_maps:
            raise ValueError("relative chain complex disagrees with certified boundaries")

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "chain_complex": self.chain_complex,
            "pair": self.pair,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class RelativeHomologyCertificate:
    pair_identity: str
    relative_complex_identity: str
    degree: int
    coefficient_modulus: int
    invariant_factors: Tuple[int, ...]
    order: int

    SCHEMA_ID = "mobility_toolkit.relative_homology_certificate.v1"

    def to_canonical_dict(self) -> dict:
        return {
            "coefficient_modulus": self.coefficient_modulus,
            "degree": self.degree,
            "invariant_factors": self.invariant_factors,
            "order": self.order,
            "pair_identity": self.pair_identity,
            "relative_complex_identity": self.relative_complex_identity,
            "schema": self.SCHEMA_ID,
        }


@dataclass(frozen=True)
class RelativeHomologyResult:
    relative_chain_complex: RelativeChainComplex
    degree: int
    coefficient_modulus: int
    homology: FiniteQuotient
    certificate: RelativeHomologyCertificate

    SCHEMA_ID = "mobility_toolkit.relative_homology_result.v1"

    def __post_init__(self) -> None:
        if self.degree < 0 or self.degree > self.relative_chain_complex.chain_complex.dimension:
            raise ValueError("relative homology degree is out of range")
        if self.coefficient_modulus <= 1:
            raise ValueError("relative homology coefficient modulus must exceed one")
        expected = RelativeHomologyCertificate(
            pair_identity=self.relative_chain_complex.pair.canonical_identity,
            relative_complex_identity=(
                self.relative_chain_complex.certificate.relative_complex_identity
            ),
            degree=self.degree,
            coefficient_modulus=self.coefficient_modulus,
            invariant_factors=self.homology.invariant_factors,
            order=self.homology.order,
        )
        if self.certificate != expected:
            raise ValueError(
                "relative homology certificate disagrees with the supplied quotient"
            )

    @property
    def invariant_factors(self) -> Tuple[int, ...]:
        return self.homology.invariant_factors

    @property
    def order(self) -> int:
        return self.homology.order

    def to_canonical_dict(self) -> dict:
        return {
            "certificate": self.certificate,
            "coefficient_modulus": self.coefficient_modulus,
            "degree": self.degree,
            "homology": self.homology,
            "relative_chain_complex": self.relative_chain_complex,
            "schema": self.SCHEMA_ID,
        }


def _subcomplex_boundary_records(
    pair: RelativeCellularPair,
) -> Tuple[SubcomplexBoundaryRecord, ...]:
    records = []
    for degree in range(1, pair.ambient.dimension + 1):
        upper_ids = pair.ambient.cell_ids_by_dimension[degree]
        lower_ids = pair.ambient.cell_ids_by_dimension[degree - 1]
        selected = set(pair.subcomplex_cell_ids_by_dimension[degree])
        by_column = {}
        for row, column, coefficient in pair.ambient.boundary_maps[degree].entries:
            if upper_ids[column] in selected:
                by_column.setdefault(column, []).append((lower_ids[row], coefficient))
        for column, cell_id in enumerate(upper_ids):
            if cell_id in selected:
                records.append(
                    SubcomplexBoundaryRecord(
                        degree,
                        cell_id,
                        tuple(sorted(by_column.get(column, ()))),
                    )
                )
    return tuple(records)


def _relative_boundaries(
    pair: RelativeCellularPair,
) -> Tuple[SparseIntMatrix, ...]:
    quotient_basis = pair.quotient_basis_by_dimension
    boundaries = [SparseIntMatrix.zero(0, len(quotient_basis[0]))]
    for degree in range(1, pair.ambient.dimension + 1):
        ambient_lower = pair.ambient.cell_ids_by_dimension[degree - 1]
        ambient_upper = pair.ambient.cell_ids_by_dimension[degree]
        lower_keep = set(quotient_basis[degree - 1])
        upper_keep = set(quotient_basis[degree])
        lower_indices = tuple(
            index for index, cell_id in enumerate(ambient_lower)
            if cell_id in lower_keep
        )
        upper_indices = tuple(
            index for index, cell_id in enumerate(ambient_upper)
            if cell_id in upper_keep
        )
        boundaries.append(
            pair.ambient.boundary_maps[degree]
            .select_rows(lower_indices)
            .select_columns(upper_indices)
        )
    return tuple(boundaries)


def construct_relative_chain_complex(
    pair: RelativeCellularPair,
) -> RelativeChainComplex:
    """Construct and certify ``C_*(X)/C_*(A)`` in canonical quotient bases."""

    if not isinstance(pair, RelativeCellularPair):
        raise TypeError("relative chain construction requires a RelativeCellularPair")
    quotient_basis = pair.quotient_basis_by_dimension
    boundaries = _relative_boundaries(pair)
    relative = FiniteCellComplex(
        quotient_basis,
        boundaries,
        pair.ambient.assumptions
        + ("canonical cellular quotient by a boundary-closed subcomplex",),
    )
    certificate = RelativeChainCertificate(
        pair_identity=pair.canonical_identity,
        ambient_identity=canonical_hash(
            FiniteCellComplex.SCHEMA_ID, pair.ambient
        ),
        subcomplex_cell_ids_by_dimension=
            pair.subcomplex_cell_ids_by_dimension,
        quotient_basis_by_dimension=quotient_basis,
        quotient_boundary_maps=boundaries,
        subcomplex_boundaries=_subcomplex_boundary_records(pair),
        relative_complex_identity=canonical_hash(
            FiniteCellComplex.SCHEMA_ID, relative
        ),
    )
    return RelativeChainComplex(pair, relative, certificate)


def verify_relative_chain_certificate(
    pair: RelativeCellularPair,
    certificate: RelativeChainCertificate,
) -> None:
    """Replay a relative-chain certificate from the semantic pair.

    This verifier deliberately recomputes closure through the validated pair
    constructor.  A forged certificate cannot turn a non-subcomplex selection
    into a valid relative chain complex.
    """

    if not isinstance(pair, RelativeCellularPair):
        raise TypeError("certificate verification requires a RelativeCellularPair")
    if not isinstance(certificate, RelativeChainCertificate):
        raise TypeError("invalid relative-chain certificate type")
    replayed_pair = RelativeCellularPair.create(
        pair.ambient, certificate.subcomplex_cell_ids_by_dimension
    )
    expected_basis = replayed_pair.quotient_basis_by_dimension
    expected_boundaries = _relative_boundaries(replayed_pair)
    expected_relative = FiniteCellComplex(
        expected_basis,
        expected_boundaries,
        pair.ambient.assumptions
        + ("canonical cellular quotient by a boundary-closed subcomplex",),
    )
    errors = []
    if certificate.pair_identity != pair.canonical_identity:
        errors.append("pair identity mismatch")
    if replayed_pair != pair:
        errors.append("certificate subcomplex differs from the supplied pair")
    if certificate.ambient_identity != canonical_hash(
        FiniteCellComplex.SCHEMA_ID, pair.ambient
    ):
        errors.append("ambient identity mismatch")
    if certificate.quotient_basis_by_dimension != expected_basis:
        errors.append("quotient basis mismatch")
    if certificate.quotient_boundary_maps != expected_boundaries:
        errors.append("quotient boundary mismatch")
    if certificate.subcomplex_boundaries != _subcomplex_boundary_records(replayed_pair):
        errors.append("subcomplex boundary transcript mismatch")
    if certificate.relative_complex_identity != canonical_hash(
        FiniteCellComplex.SCHEMA_ID, expected_relative
    ):
        errors.append("relative-complex identity mismatch")
    if errors:
        raise ValueError("invalid relative-chain certificate: " + "; ".join(errors))


def relative_cellular_homology(
    pair: RelativeCellularPair,
    degree: int,
    coefficient_modulus: int,
    backend: FiniteIntegerBackend,
) -> RelativeHomologyResult:
    """Compute exact ``H_degree(X,A; Z/coefficient_modulus)``."""

    relative = construct_relative_chain_complex(pair)
    homology = cellular_homology(
        relative.chain_complex, degree, coefficient_modulus, backend
    )
    certificate = RelativeHomologyCertificate(
        pair_identity=pair.canonical_identity,
        relative_complex_identity=relative.certificate.relative_complex_identity,
        degree=degree,
        coefficient_modulus=coefficient_modulus,
        invariant_factors=homology.invariant_factors,
        order=homology.order,
    )
    return RelativeHomologyResult(
        relative,
        degree,
        coefficient_modulus,
        homology,
        certificate,
    )


def verify_relative_homology_result(
    result: RelativeHomologyResult,
    backend: FiniteIntegerBackend,
) -> None:
    """Semantically replay the quotient and exact finite homology calculation."""

    if not isinstance(result, RelativeHomologyResult):
        raise TypeError("relative homology verification requires a result")
    replay = relative_cellular_homology(
        result.relative_chain_complex.pair,
        result.degree,
        result.coefficient_modulus,
        backend,
    )
    if replay != result:
        raise ValueError("relative homology semantic replay does not match")


# Read naturally in either word order without maintaining a second implementation.
cellular_relative_homology = relative_cellular_homology


__all__ = [
    "RelativeCellularPair",
    "RelativeChainCertificate",
    "RelativeChainComplex",
    "RelativeHomologyCertificate",
    "RelativeHomologyResult",
    "SubcomplexBoundaryRecord",
    "cellular_relative_homology",
    "construct_relative_chain_complex",
    "relative_cellular_homology",
    "verify_relative_chain_certificate",
    "verify_relative_homology_result",
]
