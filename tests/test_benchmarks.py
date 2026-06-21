"""Physics benchmarks against models with known literature results.

These are M2-backed and are skipped automatically when no Macaulay2 backend is
available. Sources are documented in docs/VALIDATION.md.

Known results validated here:
  - Z_N toric code GSD on a torus = N^2.
  - Bivariate-bicycle codes WCF / DCY reproduce their stored GSD (144 / 104976).
  - Point-charge Krull dimension classifies mobility: Krull 0 == mobile
    (topological order), Krull > 0 == restricted (fracton order), per
    "Homological Invariants of Pauli Stabilizer Codes" (Comm. Math. Phys. 2024).
"""
import pytest

from mobility_toolkit.engine import describe_m2_backend
from mobility_toolkit import compute_gsd_and_periodicity, compute_ext_krull

pytestmark = pytest.mark.skipif(
    not describe_m2_backend()["available"],
    reason="Macaulay2 backend not available",
)

TORIC = [["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]]
XCUBE = [["1 - x", "1 - y", "1 - z", "0"], ["0", "1 - y", "1 - z", "1 - x"]]
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
@pytest.mark.parametrize("matrix,N,bypass,expected", [
    (TORIC, 2, False, 0),    # topological order: mobile anyons -> Krull 0
    (XCUBE, 2, False, 2),    # fracton order (X-Cube): restricted -> Krull 2
    (CHAMON, 2, False, 1),   # fracton (Chamon cubic): Krull 1
])
def test_point_charge_krull_dimension(matrix, N, bypass, expected):
    res = compute_ext_krull(matrix, N, p_ext=0, prime_bypass=bypass)
    assert res["krull_dimension"] == expected


def test_topological_models_have_mobile_point_charges():
    """The mobility criterion: a topological model (toric code) has Krull-0
    point charges (mobile anyons), while fracton models (X-Cube, Chamon) have
    Krull > 0 (restricted). Only prime-N models are tested here: the Ext/Krull
    machinery requires a field, so composite-N codes (e.g. the N=12 BB codes)
    are classified by GSD, not by this homological path."""
    assert compute_ext_krull(TORIC, 2, p_ext=0)["krull_dimension"] == 0
    assert compute_ext_krull(XCUBE, 2, p_ext=0)["krull_dimension"] > 0
    assert compute_ext_krull(CHAMON, 2, p_ext=0)["krull_dimension"] > 0
