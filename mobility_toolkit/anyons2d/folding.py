"""Direct sums and orientation-reversing folding of finite metric groups."""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Tuple

from mobility_toolkit.anyons2d.metric import FiniteMetricGroup
from mobility_toolkit.core.integer import PresentedModule, SparseIntMatrix
from mobility_toolkit.finite import FiniteAbelianGroup, FiniteIntegerBackend


def _lcm(left: int, right: int) -> int:
    return abs(left * right) // gcd(left, right)


def _block_diagonal(left: SparseIntMatrix, right: SparseIntMatrix) -> SparseIntMatrix:
    return SparseIntMatrix(
        left.nrows + right.nrows,
        left.ncols + right.ncols,
        tuple(left.entries)
        + tuple(
            (row + left.nrows, column + left.ncols, value)
            for row, column, value in right.entries
        ),
    )


def _scaled(matrix: SparseIntMatrix, factor: int) -> SparseIntMatrix:
    return SparseIntMatrix(
        matrix.nrows,
        matrix.ncols,
        tuple((row, column, factor * value) for row, column, value in matrix.entries),
    )


def _labels(group: FiniteAbelianGroup, prefix: str) -> Tuple[str, ...]:
    if group.coordinate_labels:
        return tuple(f"{prefix}:{label}" for label in group.coordinate_labels)
    return tuple(f"{prefix}:{index}" for index in range(group.presentation_rank))


@dataclass(frozen=True)
class MetricDirectSum:
    metric: FiniteMetricGroup
    left_presentation_rank: int
    right_presentation_rank: int
    second_form_reversed: bool

    SCHEMA_ID = "mobility_toolkit.metric_direct_sum.v1"

    def left_embedding(self, vector: Tuple[int, ...]) -> Tuple[int, ...]:
        if len(vector) != self.left_presentation_rank:
            raise ValueError("left anyon representative has the wrong rank")
        return tuple(vector) + (0,) * self.right_presentation_rank

    def right_embedding(self, vector: Tuple[int, ...]) -> Tuple[int, ...]:
        if len(vector) != self.right_presentation_rank:
            raise ValueError("right anyon representative has the wrong rank")
        return (0,) * self.left_presentation_rank + tuple(vector)

    def to_canonical_dict(self) -> dict:
        return {
            "left_presentation_rank": self.left_presentation_rank,
            "metric": self.metric,
            "right_presentation_rank": self.right_presentation_rank,
            "schema": self.SCHEMA_ID,
            "second_form_reversed": self.second_form_reversed,
        }


def direct_sum_metric_groups(
    left: FiniteMetricGroup,
    right: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
    reverse_second: bool = False,
) -> MetricDirectSum:
    """Take a metric direct sum, optionally reversing the second orientation."""

    common_modulus = _lcm(left.phase_modulus, right.phase_modulus)
    left_scale = common_modulus // left.phase_modulus
    right_scale = common_modulus // right.phase_modulus
    if reverse_second:
        right_scale = -right_scale
    relations = _block_diagonal(
        left.group.relation_lattice_basis,
        right.group.relation_lattice_basis,
    )
    labels = _labels(left.group, "left") + _labels(right.group, "right")
    group = FiniteAbelianGroup.from_presentation(
        PresentedModule(relations.nrows, relations, labels), backend
    )
    braiding = _block_diagonal(
        _scaled(left.braiding_matrix, left_scale),
        _scaled(right.braiding_matrix, right_scale),
    )
    spins = tuple(left_scale * value for value in left.generator_spins) + tuple(
        right_scale * value for value in right.generator_spins
    )
    metric = FiniteMetricGroup.create(
        group,
        common_modulus,
        braiding,
        spins,
        backend,
        require_nondegenerate=(
            left.certificate.nondegenerate and right.certificate.nondegenerate
        ),
    )
    return MetricDirectSum(
        metric,
        left.group.presentation_rank,
        right.group.presentation_rank,
        reverse_second,
    )


def fold_metric_groups(
    left: FiniteMetricGroup,
    right: FiniteMetricGroup,
    backend: FiniteIntegerBackend,
) -> MetricDirectSum:
    """Fold an interface as ``left`` direct-sum orientation-reversed ``right``."""

    return direct_sum_metric_groups(left, right, backend, reverse_second=True)


__all__ = ["MetricDirectSum", "direct_sum_metric_groups", "fold_metric_groups"]
