import pytest

pytest.importorskip("flint")

from mobility_toolkit.anyons2d import (
    CondensateEnumerationBudget,
    color_code_metric_model,
    double_semion_metric_model,
    enumerate_condensates,
    zd_toric_metric_model,
)
from mobility_toolkit.core import Exactness
from mobility_toolkit.finite import FlintIntegerBackend


@pytest.fixture(scope="module")
def backend():
    return FlintIntegerBackend()


def _all_candidates(model, backend):
    checkpoint = None
    candidates = []
    final_certificate = None
    for _ in range(10_000):
        page = enumerate_condensates(
            model.metric,
            backend,
            CondensateEnumerationBudget(
                max_work_units=200_000,
                max_results=10_000,
                max_elements=256,
                max_subgroups=200_000,
            ),
            checkpoint,
        )
        candidates.extend(page.candidates)
        final_certificate = page.certificate
        checkpoint = page.checkpoint
        if checkpoint is None:
            break
    else:
        raise AssertionError("literature-model enumeration did not terminate")
    assert final_certificate is not None
    assert final_certificate.exactness is Exactness.CERTIFIED_EXACT
    return tuple(candidates), final_certificate


@pytest.mark.parametrize("dimension,expected", ((2, 2), (4, 3)))
def test_zd_toric_raw_lagrangian_counts(dimension, expected, backend):
    model = zd_toric_metric_model(dimension, backend)
    candidates, certificate = _all_candidates(model, backend)
    assert sum(candidate.lagrangian for candidate in candidates) == expected
    assert certificate.lagrangian_subgroups == expected
    assert model.expected_raw_lagrangian_subgroups == expected
    assert not model.stabilizer_extraction_constructed
    assert not model.local_boundary_completion_constructed


def test_double_semion_has_one_raw_lagrangian_subgroup(backend):
    model = double_semion_metric_model(backend)
    candidates, certificate = _all_candidates(model, backend)
    lagrangians = tuple(item for item in candidates if item.lagrangian)
    assert len(lagrangians) == 1
    assert certificate.lagrangian_subgroups == 1
    assert lagrangians[0].invariant_factors == (2,)


def test_color_code_metric_has_six_raw_lagrangian_subgroups(backend):
    model = color_code_metric_model(backend)
    candidates, certificate = _all_candidates(model, backend)
    lagrangians = tuple(item for item in candidates if item.lagrangian)
    assert len(lagrangians) == 6
    assert certificate.lagrangian_subgroups == 6
    assert all(item.order == 4 for item in lagrangians)
    assert all(item.invariant_factors == (2, 2) for item in lagrangians)
    assert "without quotienting" in model.literature_scope
