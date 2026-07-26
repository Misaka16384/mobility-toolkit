# mobility_toolkit package

# Single source of truth for the version. `pyproject.toml` derives the package
# version from this attribute (dynamic = ["version"]), and `tools/release.py`
# bumps this line. Keep it a plain string literal so setuptools can read it
# statically at build time without importing the package.
__version__ = "0.1.5"

import sys
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(1000000)



from mobility_toolkit.bridge import run_m2_script, run_macaulay2
from mobility_toolkit.translate import translate_stabilizers, translate_to_algebra
from mobility_toolkit.homology import compute_ext_krull, compute_homology_and_mobility
from mobility_toolkit.mobility import (
    compute_translation_lattice,
    compute_true_mobility_dimension,
)
from mobility_toolkit.fusion import analyze_fusion_interference, solve_sset_fusion, analyze_annihilator_fusion
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.search import search_koszul_models
from mobility_toolkit.registry import ModelRegistry, query_vector_db
from mobility_toolkit.physics import classify_mobility
from mobility_toolkit.services import (
    ServiceExecution,
    ServiceRequest,
    default_service_catalog,
    execute_service_payload,
    execute_service_request,
)

__all__ = [
    "__version__",
    "run_m2_script",
    "run_macaulay2",
    "translate_stabilizers",
    "translate_to_algebra",
    "compute_ext_krull",
    "compute_homology_and_mobility",
    "compute_translation_lattice",
    "compute_true_mobility_dimension",
    "analyze_fusion_interference",
    "solve_sset_fusion",
    "analyze_annihilator_fusion",
    "compute_gsd_and_periodicity",
    "search_koszul_models",
    "ModelRegistry",
    "query_vector_db",
    "classify_mobility",
    "ServiceExecution",
    "ServiceRequest",
    "default_service_catalog",
    "execute_service_payload",
    "execute_service_request",
]
