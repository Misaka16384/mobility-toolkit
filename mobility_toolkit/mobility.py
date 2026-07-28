"""Translation lattices of charges with binomial Laurent annihilators.

For a charge ``q`` and a lattice displacement ``a``, translating ``q`` by
``a`` preserves its charge sector precisely when

    (x**a - 1) q = 0,

or equivalently ``x**a - 1`` belongs to ``Ann(q)``.  Thus the object computed
here is the subgroup

    H = {a in Z**D | x**a - 1 in Ann(q)}.

There is a complete elementary algorithm when the *given generating set*
consists of Laurent binomials.  After division by a Laurent monomial, each relation is
``x**a = rho``.  These relations define a (partial) character of the exponent
lattice; ``H`` is exactly its kernel.  General polynomial ideals need a more
powerful algorithm and are deliberately reported as inconclusive instead of
being assigned a fabricated mobility rank.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sympy import Matrix
from sympy.matrices.normalforms import hermite_normal_form

from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit import utils


_ALGORITHM_VERSION = "laurent-binomial-character-v1"
_RESULT_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

_LEGACY_AXES = {
    "x": (1, 1),
    "t": (1, -1),
    "y": (2, 1),
    "u": (2, -1),
    "z": (3, 1),
    "w": (3, -1),
}
_VAR_RE = re.compile(r"^[a-z]\d*$")


def clean_wsl_garbage(text: str) -> str:
    """Remove known WSL launcher noise without changing process semantics."""

    cleaned = []
    for line in text.split("\n"):
        normalized = line.replace(" ", "").lower()
        if any(marker in normalized for marker in ("wsl:", "localhost", "connection", "n/ec")):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def safe_run_m2_script(script_content: str, timeout_seconds: float = 60.0):
    """Run M2 while preserving every non-zero exit status.

    Older code silently changed some non-zero statuses to success.  That can
    turn empty or partial output into a confident but false mobility result.
    The binomial algorithm below does not need M2, but this helper remains a
    public compatibility point and is intentionally strict.
    """

    code, stdout, stderr = run_m2_script(script_content, timeout_seconds)
    return code, clean_wsl_garbage(stdout), clean_wsl_garbage(stderr)


def _split_terms(poly: str) -> List[str]:
    """Split an expanded polynomial, retaining signs and negative exponents."""

    compact = poly.replace(" ", "").replace("**", "^")
    if not compact:
        raise ValueError("Polynomial generators must not be empty.")
    if any(ch in compact for ch in "()/"):
        raise ValueError("Parentheses and division are unsupported; fully expand Laurent polynomials.")

    terms: List[str] = []
    start = 0
    for index, char in enumerate(compact):
        if index > start and char in "+-" and compact[index - 1] != "^":
            terms.append(compact[start:index])
            start = index
    terms.append(compact[start:])
    if any(term in ("", "+", "-") for term in terms):
        raise ValueError(f"Malformed polynomial: {poly!r}")
    return terms


def _tokens(strings: Iterable[str]) -> List[str]:
    result: List[str] = []
    for value in strings:
        result.extend(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value))
    return result


def _axis_spec(generators: Sequence[str], all_vars: Optional[Sequence[str]]) -> Tuple[str, int, List[str], Dict[str, Tuple[int, int]], List[str]]:
    """Return notation, dimension, positive axes, aliases and Laurent relations."""

    if all_vars is not None:
        if not isinstance(all_vars, list) or not all_vars:
            raise ValueError("all_vars must be a non-empty list of variable names.")
        if any(not isinstance(var, str) or not _VAR_RE.fullmatch(var) for var in all_vars):
            raise ValueError("all_vars may contain only lowercase variables optionally followed by digits.")

    names = _tokens(list(generators) + (list(all_vars) if all_vars is not None else []))
    if any(not _VAR_RE.fullmatch(name) for name in names):
        bad = next(name for name in names if not _VAR_RE.fullmatch(name))
        raise ValueError(f"Invalid variable name: {bad!r}")

    has_unified = any(re.fullmatch(r"[xt][1-9]\d*", name) for name in names)
    has_legacy = any(name in _LEGACY_AXES for name in names)
    if has_unified and has_legacy:
        raise ValueError("Do not mix legacy variables (x,t,y,u,z,w) with unified variables (x1,t1,...).")

    aliases: Dict[str, Tuple[int, int]] = {}
    if has_unified:
        notation = "unified"
        indices: List[int] = []
        for name in names:
            match = re.fullmatch(r"([xt])([1-9]\d*)", name)
            if match is None:
                raise ValueError(f"Invalid unified Laurent variable: {name!r}")
            index = int(match.group(2))
            indices.append(index)
            aliases[name] = (index, 1 if match.group(1) == "x" else -1)
        dimension = max(indices, default=1)
        axes = [f"x{i}" for i in range(1, dimension + 1)]
        for index in range(1, dimension + 1):
            aliases[f"x{index}"] = (index, 1)
            aliases[f"t{index}"] = (index, -1)
        relations = [f"x{i}*t{i} - 1" for i in range(1, dimension + 1)]
    else:
        notation = "legacy"
        unknown = [name for name in names if name not in _LEGACY_AXES]
        if unknown:
            raise ValueError(f"Invalid legacy Laurent variable: {unknown[0]!r}")
        dimension = max((_LEGACY_AXES[name][0] for name in names), default=1)
        axes = ["x", "y", "z"][:dimension]
        aliases = dict(_LEGACY_AXES)
        inverse_names = ["t", "u", "w"]
        relations = [f"{axes[i]}*{inverse_names[i]} - 1" for i in range(dimension)]

    return notation, dimension, axes, aliases, relations


def _parse_term(term: str, dimension: int, aliases: Dict[str, Tuple[int, int]]) -> Tuple[int, Tuple[int, ...]]:
    sign = 1
    if term[0] in "+-":
        sign = -1 if term[0] == "-" else 1
        term = term[1:]
    if not term:
        raise ValueError("Malformed empty monomial.")

    coefficient = sign
    exponent = [0] * dimension
    for factor in term.split("*"):
        if not factor:
            raise ValueError("Malformed product in polynomial generator.")
        if re.fullmatch(r"\d+", factor):
            coefficient *= int(factor)
            continue
        match = re.fullmatch(r"([a-z]\d*)(?:\^([+-]?\d+))?", factor)
        if match is None or match.group(1) not in aliases:
            raise ValueError(f"Invalid Laurent monomial factor: {factor!r}")
        name = match.group(1)
        power = int(match.group(2) or "1")
        axis_index, orientation = aliases[name]
        if axis_index > dimension:
            raise ValueError(f"Variable {name!r} lies outside the declared spatial ring.")
        exponent[axis_index - 1] += orientation * power
    return coefficient, tuple(exponent)


def _parse_polynomial(poly: str, prime: int, dimension: int, aliases: Dict[str, Tuple[int, int]]) -> Dict[Tuple[int, ...], int]:
    terms: Dict[Tuple[int, ...], int] = {}
    for raw_term in _split_terms(poly):
        coefficient, exponent = _parse_term(raw_term, dimension, aliases)
        coefficient %= prime
        terms[exponent] = (terms.get(exponent, 0) + coefficient) % prime
    return {exponent: coefficient for exponent, coefficient in terms.items() if coefficient}


def _prime_factors(value: int) -> List[int]:
    factors: List[int] = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            factors.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate += 1
    if value > 1:
        factors.append(value)
    return factors


def _discrete_log_table(prime: int) -> Dict[int, int]:
    """Discrete logs in F_p^*.  qudit dimensions are already capped upstream."""

    if prime == 2:
        return {1: 0}
    order = prime - 1
    generator = next(
        candidate
        for candidate in range(2, prime)
        if all(pow(candidate, order // factor, prime) != 1 for factor in _prime_factors(order))
    )
    table: Dict[int, int] = {}
    value = 1
    for exponent in range(order):
        table[value] = exponent
        value = value * generator % prime
    return table


def _extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """Return non-negative gcd and Bezout coefficients."""

    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        old_t, t = t, old_t - quotient * t
    if old_r < 0:
        return -old_r, -old_s, -old_t
    return old_r, old_s, old_t


def _character_kernel_basis(labels: Sequence[int], modulus: int) -> Matrix:
    """A column basis of {c in Z^m | labels*c = 0 mod modulus}."""

    count = len(labels)
    transform = Matrix.eye(count)
    reduced = list(labels)
    for column in range(1, count):
        a, b = reduced[0], reduced[column]
        gcd_value, bezout_a, bezout_b = _extended_gcd(a, b)
        if gcd_value == 0:
            continue
        pair_transform = Matrix([[bezout_a, b // gcd_value], [bezout_b, -a // gcd_value]])
        old_columns = transform[:, [0, column]]
        new_columns = old_columns * pair_transform
        transform[:, 0] = new_columns[:, 0]
        transform[:, column] = new_columns[:, 1]
        reduced[0], reduced[column] = gcd_value, 0

    gcd_labels = abs(reduced[0]) if reduced else 0
    scale = 1 if modulus == 1 or gcd_labels == 0 else modulus // math.gcd(modulus, gcd_labels)
    diagonal = Matrix.diag(scale, *([1] * (count - 1)))
    return transform * diagonal


def _column_lattice_basis(generators: Matrix) -> Matrix:
    """Canonical independent column basis for an integer lattice."""

    if generators.cols == 0 or generators.rank() == 0:
        return Matrix.zeros(generators.rows, 0)
    return hermite_normal_form(generators)


def _lattice_index(super_basis: Matrix, sub_basis: Matrix) -> int:
    """Index of two equal-rank column lattices in the same rational span."""

    rank = super_basis.cols
    if rank == 0:
        return 1
    coordinate_columns = []
    for column in range(sub_basis.cols):
        solution, parameters = super_basis.gauss_jordan_solve(sub_basis[:, column])
        if parameters.rows:
            raise ArithmeticError("Unexpected underdetermined lattice coordinates.")
        if any(value.q != 1 for value in solution):
            raise ArithmeticError("Computed sublattice is not contained in its relation lattice.")
        coordinate_columns.append([int(value) for value in solution])
    coordinates = Matrix.hstack(*(Matrix(column) for column in coordinate_columns))
    coordinate_basis = _column_lattice_basis(coordinates)
    if coordinate_basis.cols != rank:
        raise ArithmeticError("Character kernel unexpectedly changed lattice rank.")
    return abs(int(coordinate_basis.det()))


def _matrix_columns_as_rows(matrix: Matrix) -> List[List[int]]:
    return [[int(matrix[row, column]) for row in range(matrix.rows)] for column in range(matrix.cols)]


def _inconclusive(axes: List[str], relations: List[str], reason: str) -> Dict[str, Any]:
    return {
        "status": "inconclusive",
        "conclusive": False,
        "method": _ALGORITHM_VERSION,
        "mobility_dimension": None,
        "translation_lattice_basis": None,
        "kernel_basis": None,
        "valuation_matrix": None,
        "divisors": [],
        "variables": axes,
        "laurent_relations": relations,
        "reason": reason,
    }


def compute_translation_lattice(
    generators: List[str], qudit_dim: int, all_vars: List[str] = None
) -> Dict[str, Any]:
    """Compute the exact translation lattice for a Laurent-binomial ideal.

    ``mobility_dimension`` is the rank of
    ``H = {a | x^a - 1 in ideal(generators)}``.  The result is exact when every
    nonzero member of the given generating set reduces to a Laurent binomial.
    Otherwise a structured
    inconclusive result is returned.
    """

    utils.log_python_run(
        "mobility_toolkit.mobility",
        "compute_translation_lattice",
        (generators, qudit_dim, all_vars),
        {},
        "PENDING",
    )
    if not isinstance(generators, list) or not generators:
        raise ValueError("generators must be a non-empty list of strings.")
    if any(not isinstance(generator, str) for generator in generators):
        raise ValueError("All generators must be strings.")
    if not isinstance(qudit_dim, int):
        raise TypeError("qudit_dim must be an integer")
    utils.verify_qudit_dim(qudit_dim)
    if qudit_dim > 100000:
        raise ValueError("qudit_dim must be <= 100000")

    _, dimension, axes, aliases, laurent_relations = _axis_spec(generators, all_vars)
    cache_key = (
        _ALGORITHM_VERSION,
        qudit_dim,
        tuple(sorted(generator.replace(" ", "").replace("**", "^") for generator in generators)),
        tuple(axes),
        tuple(laurent_relations),
    )
    if cache_key in _RESULT_CACHE:
        return copy.deepcopy(_RESULT_CACHE[cache_key])

    exponent_relations: List[Tuple[int, ...]] = []
    scalar_relations: List[int] = []
    log_table = _discrete_log_table(qudit_dim)
    for generator in generators:
        polynomial = _parse_polynomial(generator, qudit_dim, dimension, aliases)
        if not polynomial:
            continue
        if len(polynomial) == 1:
            identity = Matrix.eye(dimension)
            result = {
                "status": "trivial",
                "conclusive": True,
                "method": _ALGORITHM_VERSION,
                "mobility_dimension": None,
                "translation_lattice_rank": dimension,
                "translation_lattice_basis": _matrix_columns_as_rows(identity),
                "kernel_basis": _matrix_columns_as_rows(identity),
                "valuation_matrix": [],
                "divisors": [],
                "variables": axes,
                "laurent_relations": laurent_relations,
                "reason": "The Laurent ideal contains a monomial unit, so the charge is zero and physical mobility is undefined.",
            }
            _RESULT_CACHE[cache_key] = copy.deepcopy(result)
            return result
        if len(polynomial) != 2:
            result = _inconclusive(
                axes,
                laurent_relations,
                "At least one generator is not a Laurent binomial. The exact general-ideal translation-lattice algorithm is not implemented.",
            )
            _RESULT_CACHE[cache_key] = copy.deepcopy(result)
            return result

        (left_exp, left_coef), (right_exp, right_coef) = sorted(polynomial.items())
        exponent_relations.append(tuple(left_exp[i] - right_exp[i] for i in range(dimension)))
        rho = (-right_coef * pow(left_coef, -1, qudit_dim)) % qudit_dim
        scalar_relations.append(log_table[rho])

    if not exponent_relations:
        zero_basis = Matrix.zeros(dimension, 0)
        result = {
            "status": "success",
            "conclusive": True,
            "method": _ALGORITHM_VERSION,
            "mobility_dimension": 0,
            "translation_lattice_rank": 0,
            "translation_lattice_basis": [],
            "kernel_basis": [],
            "valuation_matrix": [],
            "divisors": [],
            "variables": axes,
            "laurent_relations": laurent_relations,
            "criterion": "H = {a in Z^D | x^a - 1 belongs to Ann(q)}",
        }
        _RESULT_CACHE[cache_key] = copy.deepcopy(result)
        return result

    relation_matrix = Matrix(dimension, len(exponent_relations), lambda row, col: exponent_relations[col][row])
    relation_lattice = _column_lattice_basis(relation_matrix)
    coefficient_kernel = _character_kernel_basis(scalar_relations, qudit_dim - 1)
    translation_generators = relation_matrix * coefficient_kernel
    translation_lattice = _column_lattice_basis(translation_generators)

    expected_index = (qudit_dim - 1) // math.gcd(qudit_dim - 1, *scalar_relations)
    actual_index = _lattice_index(relation_lattice, translation_lattice)
    if actual_index != expected_index:
        identity = Matrix.eye(dimension)
        result = {
            "status": "trivial",
            "conclusive": True,
            "method": _ALGORITHM_VERSION,
            "mobility_dimension": None,
            "translation_lattice_rank": dimension,
            "translation_lattice_basis": _matrix_columns_as_rows(identity),
            "kernel_basis": _matrix_columns_as_rows(identity),
            "valuation_matrix": [],
            "divisors": [],
            "variables": axes,
            "laurent_relations": laurent_relations,
            "reason": "The binomial scalar relations are inconsistent, so the Laurent ideal is the unit ideal and the charge is zero.",
        }
        _RESULT_CACHE[cache_key] = copy.deepcopy(result)
        return result

    basis = _matrix_columns_as_rows(translation_lattice)
    result = {
        "status": "success",
        "conclusive": True,
        "method": _ALGORITHM_VERSION,
        "guarantee": "exact_for_laurent_binomial_generators",
        "mobility_dimension": translation_lattice.cols,
        "translation_lattice_rank": translation_lattice.cols,
        "translation_lattice_basis": basis,
        # Compatibility alias.  This is a lattice basis, not a valuation nullspace.
        "kernel_basis": basis,
        "valuation_matrix": [],
        "divisors": [],
        "variables": axes,
        "laurent_relations": laurent_relations,
        "criterion": "H = {a in Z^D | x^a - 1 belongs to Ann(q)}",
        "binomial_exponent_relations": [list(vector) for vector in exponent_relations],
    }
    _RESULT_CACHE[cache_key] = copy.deepcopy(result)
    utils.save_discovery("mobility_rank_discovery", result)
    utils.log_python_run(
        "mobility_toolkit.mobility",
        "compute_translation_lattice",
        (generators, qudit_dim, all_vars),
        {},
        result,
    )
    return result
