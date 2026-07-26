"""Physics benchmarks against models with known literature results.

These are M2-backed and are skipped automatically when no Macaulay2 backend is
available. Sources are documented in docs/VALIDATION.md.

Known results validated here:
  - Z_N toric code GSD on a torus = N^2.
  - Bivariate-bicycle codes WCF / DCY reproduce their stored GSD (144 / 104976).
  - The full X-Cube presentation of Ruba--Yang Eq. (98) has a point-charge
    module of Krull dimension 1 and vanishing higher charge modules.
  - For Q^0 only, Krull dimension 0 means all local point charges are mobile;
    positive dimension means that not all are fully mobile.  It does not by
    itself determine planon/lineon/fracton labels or topological order.
"""
import pytest

from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.homology import compute_ext_krull

pytestmark = pytest.mark.skipif(
    not describe_m2_backend()["available"],
    reason="Macaulay2 backend not available",
)

# Each input row is one generator [X_1,...,X_q | Z_1,...,Z_q].
# TORIC is the conventional isotropic sigma (written as generator rows).
TORIC = [["1 - t", "1 - u", "0", "0"], ["0", "0", "y - 1", "1 - x"]]

# Ruba--Yang Eq. (98) is a 6x3 sigma, hence three generator rows of length six
# in the toolkit's row-oriented input convention.
XCUBE = [
    ["1 + t + u + t*u", "1 + u + w + u*w", "1 + t + w + t*w", "0", "0", "0"],
    ["0", "0", "0", "1 + z", "1 + x", "0"],
    ["0", "0", "0", "0", "1 + x", "1 + y"],
]
CHAMON = [["y + z + x*y + x*z", "x + z + x*y + y*z"]]
WCF = [["t - 5", "u - 5", "0", "0"], ["0", "0", "y - 5", "5 - x"]]
DCY = [["t^2 - 11*t + 10", "u^2 - 11*u + 10", "0", "0"],
       ["0", "0", "y^2 - 11*y + 10", "-x^2 + 11*x - 10"]]


# --- Ground-state degeneracy -------------------------------------------------
@pytest.mark.parametrize("N,L", [(2, 3), (3, 2), (5, 3)])
def test_zn_toric_gsd_is_n_squared(N, L):
    """Z_N toric code on an L x L torus has GSD = N^2 (size-independent)."""
    res = compute_gsd_and_periodicity(TORIC, L, L, N)
    assert res["gsd"] == N * N


def test_bivariate_bicycle_wcf_gsd():
    res = compute_gsd_and_periodicity(WCF, 2, 2, 12)
    assert res["gsd"] == 144


def test_bivariate_bicycle_dcy_gsd():
    res = compute_gsd_and_periodicity(DCY, 3, 3, 12)
    assert res["gsd"] == 104976


# --- Point-charge mobility (Krull dimension of the p=0 charge module) ---------
@pytest.mark.parametrize("matrix,N,expected", [
    (TORIC, 2, 0),
    (XCUBE, 2, 1),
    (CHAMON, 2, 1),
])
def test_point_charge_krull_dimension(matrix, N, expected):
    res = compute_ext_krull(matrix, N, p_ext=0)
    assert res["krull_dimension"] == expected


def test_q0_mobility_criterion_distinguishes_all_mobile_from_not_all_mobile():
    """Corollary 37 at module level, without over-classifying individual charges.

    Only prime-N models are exercised because that is a limitation of the
    current M2 implementation, not a limitation of Ruba--Yang's theory.
    """
    assert compute_ext_krull(TORIC, 2, p_ext=0)["krull_dimension"] == 0
    assert compute_ext_krull(XCUBE, 2, p_ext=0)["krull_dimension"] > 0
    assert compute_ext_krull(CHAMON, 2, p_ext=0)["krull_dimension"] > 0


@pytest.mark.parametrize("p_ext", [1, 2])
def test_full_xcube_higher_charge_modules_vanish(p_ext):
    """Ruba--Yang Sec. 7.7: injective sigma makes L free, so Q^i=0 for i>0."""
    result = compute_ext_krull(XCUBE, 2, p_ext=p_ext)
    assert result["krull_dimension"] == -1
