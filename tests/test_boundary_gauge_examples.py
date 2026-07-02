"""Regression tests against the current modular program output.

These tests do not compare against the original notebook. They freeze the
current confirmed behavior so later refactors can remove legacy notebook
dependencies without accidentally changing results.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("MPMATH_NOGMPY", "1")
os.environ.setdefault("SYMPY_GROUND_TYPES", "python")

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "mobility_toolkit" / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from common import iter_cases, run_case, summarize_result


EXPECTED_CURRENT_SUMMARIES = {
    1: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    2: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    3: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    4: {
        "bulk_count": 30,
        "s_mat_shape": (30, 100),
        "ops_shape": (5, 100),
        "final_generator_count": 5,
        "weights": [1, 1, 3, 3, 4],
    },
    5: {
        "bulk_count": 30,
        "s_mat_shape": (30, 100),
        "ops_shape": (5, 100),
        "final_generator_count": 5,
        "weights": [1, 1, 3, 3, 4],
    },
    6: {
        "bulk_count": 30,
        "s_mat_shape": (30, 100),
        "ops_shape": (4, 100),
        "final_generator_count": 4,
        "weights": [1, 1, 3, 3],
    },
    7: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    8: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    9: {
        "bulk_count": 40,
        "s_mat_shape": (40, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    10: {
        "bulk_count": 85,
        "s_mat_shape": (85, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    11: {
        "bulk_count": 85,
        "s_mat_shape": (85, 100),
        "ops_shape": (2, 100),
        "final_generator_count": 2,
        "weights": [1, 3],
    },
    12: {
        "bulk_count": 80,
        "s_mat_shape": (80, 100),
        "ops_shape": (3, 100),
        "final_generator_count": 3,
        "weights": [1, 1, 5],
    },
    13: {
        "bulk_count": 117,
        "s_mat_shape": (89, 216),
        "ops_shape": (3, 216),
        "final_generator_count": 3,
        "weights": [1, 1, 5],
    },
    14: {
        "bulk_count": 117,
        "s_mat_shape": (89, 216),
        "ops_shape": (3, 216),
        "final_generator_count": 3,
        "weights": [1, 3, 3],
    },
    15: {
        "bulk_count": 117,
        "s_mat_shape": (89, 216),
        "ops_shape": (3, 216),
        "final_generator_count": 3,
        "weights": [1, 1, 5],
    },
    16: {
        "bulk_count": 208,
        "s_mat_shape": (153, 384),
        "ops_shape": (2, 384),
        "final_generator_count": 2,
        "weights": [3, 4],
    },
    17: {
        "bulk_count": 208,
        "s_mat_shape": (153, 384),
        "ops_shape": (2, 384),
        "final_generator_count": 2,
        "weights": [1, 8],
    },
    18: {
        "bulk_count": 208,
        "s_mat_shape": (153, 384),
        "ops_shape": (2, 384),
        "final_generator_count": 2,
        "weights": [3, 4],
    },
    19: {
        "bulk_count": 200,
        "s_mat_shape": (200, 500),
        "ops_shape": (2, 500),
        "final_generator_count": 2,
        "weights": [3, 5],
    },
    20: {
        "bulk_count": 200,
        "s_mat_shape": (200, 500),
        "ops_shape": (2, 500),
        "final_generator_count": 2,
        "weights": [3, 5],
    },
}


def _current_summary(case):
    with contextlib.redirect_stdout(io.StringIO()):
        bulk, ops, s_mat = run_case(case, visualize=False)
    summary = summarize_result(bulk, ops, s_mat)
    summary["ops_shape"] = tuple(ops.shape)
    return summary


@pytest.mark.parametrize(
    "case",
    iter_cases(haah_visual_split=False),
    ids=lambda case: f"{case.index:02d}-{case.title}",
)
def test_current_example_summary(case):
    assert _current_summary(case) == EXPECTED_CURRENT_SUMMARIES[case.index]

