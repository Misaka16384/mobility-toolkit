import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit.translate import translate_stabilizers
from mobility_toolkit.utils import is_prime, log_python_run, save_discovery


_INVARIANT_VERSION = "ruba-yang-qbar-v2"
_MATRIX_CONVENTION = "generator-rows-x-then-z"


def _parse_m2_result(stdout: str) -> Tuple[int, List[str], List[str]]:
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        idx_ext = lines.index("VALUE:EXT_START")
        idx_dim = lines.index("VALUE:DIM_START")
        idx_ann = lines.index("VALUE:ANN_START")
        idx_ann_string = lines.index("VALUE:ANN_STRING_START")
    except ValueError as error:
        raise RuntimeError(
            f"Failed to find expected output markers in Macaulay2 stdout: {stdout}"
        ) from error

    def payload(start: int, end: int) -> List[str]:
        return [
            line for line in lines[start:end]
            if line and not re.match(r"^[io]\d+\s*[:=]", line)
        ]

    ext_string = " ".join(payload(idx_ext + 1, idx_dim)).strip()
    ext_modules = [ext_string] if ext_string else ["0"]

    dim_lines = payload(idx_dim + 1, idx_ann)
    if not dim_lines:
        raise ValueError(f"Could not parse dimension from Macaulay2 output: {stdout}")
    dim_string = dim_lines[0]
    if "infinity" in dim_string.lower() or "inf" in dim_string.lower():
        krull_dimension = -1
    else:
        match = re.search(r"-?\d+", dim_string)
        if not match:
            raise ValueError(f"Could not convert dimension {dim_string!r} to an integer")
        krull_dimension = int(match.group(0))

    # The final toString line is substantially more stable than pretty-printed
    # matrix output.  Keep the pretty print only as a fallback for old M2 builds.
    ann_string = " ".join(payload(idx_ann_string + 1, len(lines))).strip()
    ann_pretty = " ".join(payload(idx_ann + 1, idx_ann_string)).strip()
    ann_content = ann_string or ann_pretty
    compact = ann_content.replace(" ", "")
    if "matrix{}" in compact or "{{}}" in compact:
        generators = []
    else:
        match = re.search(r"matrix\s*\{\{(.*?)\}\}", ann_content)
        if not match:
            match = re.search(r"\{\{(.*?)\}\}", ann_content)
        if match:
            generators = [item.strip() for item in match.group(1).split(",") if item.strip()]
        else:
            generators = [
                item.strip()
                for bar in re.findall(r"\|(.*?)\|", ann_pretty)
                for item in bar.split()
                if item.strip()
            ]

    return krull_dimension, ext_modules, generators


def _theorem_metadata(
    p_ext: int,
    spatial_dim: int,
    krull_dimension: int,
    saturated: Optional[bool],
) -> Dict[str, Any]:
    is_zero = krull_dimension < 0
    universal_bound = spatial_dim - 1 - p_ext
    universal_bound_passed = is_zero or krull_dimension <= universal_bound
    vanishing_applicable = p_ext >= spatial_dim
    vanishing_passed = not vanishing_applicable or is_zero

    checks: Dict[str, Any] = {
        "prop25_universal_dimension_bound": {
            "statement": "dim(Q^p) <= D - 1 - p",
            "bound": universal_bound,
            "passed": universal_bound_passed,
        },
        "prop25_vanishing": {
            "statement": "Q^p = 0 for p >= D",
            "applicable": vanishing_applicable,
            "passed": vanishing_passed,
        },
    }
    if saturated is True:
        saturated_bound = spatial_dim - 2 - p_ext
        checks["prop25_saturated_dimension_bound"] = {
            "statement": "dim(Q^p) <= D - 2 - p for saturated L",
            "bound": saturated_bound,
            "passed": is_zero or krull_dimension <= saturated_bound,
        }

    invariant_consistency = all(check["passed"] for check in checks.values())
    return {
        "definition": "Q^p = Ext_R^{p+1}(bar(P/L), R)",
        "computed_degree": p_ext + 1,
        "ambient_spatial_dimension": spatial_dim,
        "antipode_applied": True,
        "zero_module_convention": {
            "krull_dimension": -1,
            "mathematical_dimension": "-infinity",
        },
        "saturated_assumption": saturated,
        "checks": checks,
        "invariant_consistency": invariant_consistency,
    }


def _decorate_result(
    core: Dict[str, Any],
    translation: Dict[str, Any],
    p_ext: int,
    saturated: Optional[bool],
) -> Dict[str, Any]:
    theorem = _theorem_metadata(
        p_ext,
        translation["spatial_dim"],
        core["krull_dimension"],
        saturated,
    )
    result = dict(core)
    result.update({
        "definition": theorem["definition"],
        "ring_definition": translation["ring_definition"],
        "variables": translation["variables"],
        "variable_pairs": translation["variable_pairs"],
        "spatial_dim": translation["spatial_dim"],
        "matrix_definition": translation["matrix_definition"],
        "antipode_matrix_definition": translation["antipode_matrix_definition"],
        "matrix_convention": translation["matrix_convention"],
        "stabilizer_validation": translation["stabilizer_validation"],
        "theorem_metadata": theorem,
        "invariant_consistency": theorem["invariant_consistency"],
    })
    return result


def compute_ext_krull(
    stabilizer_matrix: List[List[str]],
    qudit_dim: int,
    p_ext: int = 0,
    prime_bypass: bool = False,
    spatial_dim: Optional[int] = None,
    validate_stabilizer: bool = True,
    saturated: Optional[bool] = None,
) -> Dict[str, Any]:
    """Compute Ruba--Yang's charge module ``Q^p`` and its support dimension.

    Input rows are stabilizer generators.  If callers intentionally want Ext of
    an arbitrary presentation rather than a stabilizer code, they may explicitly
    pass ``validate_stabilizer=False``; the returned validation metadata records
    that choice.
    """
    if not isinstance(p_ext, int) or isinstance(p_ext, bool) or p_ext < 0:
        raise ValueError("p_ext must be a non-negative integer")
    if saturated is not None and not isinstance(saturated, bool):
        raise ValueError("saturated must be True, False, or None")
    if prime_bypass and isinstance(qudit_dim, int) and not is_prime(qudit_dim):
        raise NotImplementedError(
            "Ruba--Yang's theory supports Z_n coefficients, but this homology "
            "backend currently implements Ext only for a uniform prime field; "
            "prime_bypass is available for translation, not homology"
        )

    translation = translate_stabilizers(
        stabilizer_matrix,
        qudit_dim,
        prime_bypass=prime_bypass,
        spatial_dim=spatial_dim,
        validate_stabilizer=validate_stabilizer,
    )

    log_kwargs = {
        "p_ext": p_ext,
        "prime_bypass": prime_bypass,
        "spatial_dim": spatial_dim,
        "validate_stabilizer": validate_stabilizer,
        "saturated": saturated,
    }
    log_python_run(
        module_name="mobility_toolkit.homology",
        function_name="compute_ext_krull",
        args=(stabilizer_matrix, qudit_dim),
        kwargs=log_kwargs,
        result="PENDING",
    )

    from mobility_toolkit.registry import ModelRegistry
    registry = ModelRegistry()
    cached = registry.get_cached_annihilator(
        stabilizer_matrix,
        qudit_dim,
        p_ext,
        spatial_dim=translation["spatial_dim"],
        validate_stabilizer=validate_stabilizer,
        convention=_MATRIX_CONVENTION,
        invariant_version=_INVARIANT_VERSION,
    )
    if cached is not None:
        result = _decorate_result(cached, translation, p_ext, saturated)
        if not result["invariant_consistency"]:
            raise RuntimeError(
                "Cached Ext result violates Ruba--Yang Proposition 25; discard the cache"
            )
        return result

    ring_definition = translation["ring_definition"]
    barred_matrix_definition = translation["antipode_matrix_definition"]
    script_content = f"""{ring_definition}
barSigma = matrix(R, {barred_matrix_definition})
barPL = coker barSigma
Q = Ext^{p_ext + 1}(barPL, R^1)
I = ann Q
print \"VALUE:EXT_START\"
print Q
print \"VALUE:DIM_START\"
print (dim Q)
print \"VALUE:ANN_START\"
print generators gb I
print \"VALUE:ANN_STRING_START\"
print toString(generators gb I)
"""

    exit_code, stdout, stderr = run_m2_script(script_content)
    if exit_code != 0:
        raise RuntimeError(f"Macaulay2 execution failed: {stderr or stdout}")

    krull_dimension, ext_modules, generators = _parse_m2_result(stdout)
    core = {
        "krull_dimension": krull_dimension,
        "ext_modules": ext_modules,
        "annihilator_generators": generators,
    }
    result = _decorate_result(core, translation, p_ext, saturated)
    if not result["invariant_consistency"]:
        raise RuntimeError(
            "Computed Ext result violates Ruba--Yang Proposition 25: "
            f"{result['theorem_metadata']['checks']}"
        )

    registry.cache_annihilator(
        stabilizer_matrix,
        qudit_dim,
        p_ext,
        krull_dimension,
        ext_modules,
        generators,
        spatial_dim=translation["spatial_dim"],
        validate_stabilizer=validate_stabilizer,
        convention=_MATRIX_CONVENTION,
        invariant_version=_INVARIANT_VERSION,
    )

    log_python_run(
        module_name="mobility_toolkit.homology",
        function_name="compute_ext_krull",
        args=(stabilizer_matrix, qudit_dim),
        kwargs=log_kwargs,
        result=result,
    )

    matrix_hash = hashlib.md5(str(stabilizer_matrix).encode("utf-8")).hexdigest()[:8]
    discovery_name = f"discovery_q{qudit_dim}_p{p_ext}_{matrix_hash}"
    save_discovery(discovery_name, result)
    save_discovery("homological_discovery", result)
    return result


def compute_homology_and_mobility(
    stabilizer_matrix: List[List[str]],
    qudit_dim: int,
    p_ext: int = 0,
    prime_bypass: bool = False,
    spatial_dim: Optional[int] = None,
    validate_stabilizer: bool = True,
    saturated: Optional[bool] = None,
) -> Dict[str, Any]:
    """Deprecated compatibility alias for :func:`compute_ext_krull`.

    The core function computes an algebraic charge module; it does not by
    itself determine an excitation mobility class.
    """
    return compute_ext_krull(
        stabilizer_matrix,
        qudit_dim,
        p_ext,
        prime_bypass=prime_bypass,
        spatial_dim=spatial_dim,
        validate_stabilizer=validate_stabilizer,
        saturated=saturated,
    )
