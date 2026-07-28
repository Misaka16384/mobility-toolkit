"""Canonical model fixtures with explicit literature provenance."""

from mobility_toolkit.models.periodic_2d import (
    FISH_TORIC_SOURCE,
    FishToricCliffordEquivalence,
    apply_fish_cnot_shear,
    z2_fish_toric_clifford_equivalence,
    z2_fish_toric_model,
    z2_standard_toric_model,
)
from mobility_toolkit.models.periodic_3d import (
    LiteraturePeriodicModel,
    z2_haah_cubic_code_a_model,
    z2_xcube_model,
    zd_3d_toric_model,
)

__all__ = [
    "FISH_TORIC_SOURCE",
    "FishToricCliffordEquivalence",
    "LiteraturePeriodicModel",
    "apply_fish_cnot_shear",
    "z2_fish_toric_clifford_equivalence",
    "z2_fish_toric_model",
    "z2_haah_cubic_code_a_model",
    "z2_standard_toric_model",
    "z2_xcube_model",
    "zd_3d_toric_model",
]
