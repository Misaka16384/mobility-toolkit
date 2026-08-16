import math
import re
from typing import Any, Dict, List, Optional, Tuple
import operator

from mobility_toolkit.utils import verify_qudit_dim

def map_variables_to_unified(elem: str) -> str:
    # 1. Normalize power operator
    elem = elem.replace('**', '^')
    
    # 2. Map legacy negative powers (e.g. x^-2 -> t^2)
    elem = re.sub(r'\bx\s*\^\s*-\s*(\d+)\b', lambda m: 't' if int(m.group(1)) == 1 else f't^{m.group(1)}', elem)
    elem = re.sub(r'\by\s*\^\s*-\s*(\d+)\b', lambda m: 'u' if int(m.group(1)) == 1 else f'u^{m.group(1)}', elem)
    elem = re.sub(r'\bz\s*\^\s*-\s*(\d+)\b', lambda m: 'w' if int(m.group(1)) == 1 else f'w^{m.group(1)}', elem)
    
    # 3. Map unified negative powers (e.g. x1^-2 -> t1^2)
    elem = re.sub(r'\bx(\d+)\s*\^\s*-\s*(\d+)\b', lambda m: f't{m.group(1)}' if int(m.group(2)) == 1 else f't{m.group(1)}^{m.group(2)}', elem)
    
    # 4. Map legacy variables to unified variables at word boundaries
    elem = re.sub(r'\bx\b', 'x1', elem)
    elem = re.sub(r'\bt\b', 't1', elem)
    elem = re.sub(r'\by\b', 'x2', elem)
    elem = re.sub(r'\bu\b', 't2', elem)
    elem = re.sub(r'\bz\b', 'x3', elem)
    elem = re.sub(r'\bw\b', 't3', elem)
    
    return elem


def apply_laurent_antipode(elem: str) -> str:
    """Apply the group-ring antipode ``x_i <-> x_i^-1``.

    The returned expression uses unified ``xN``/``tN`` variable names.  This is
    a syntactic ring automorphism; coefficients are fixed.
    """
    unified = map_variables_to_unified(elem)
    return re.sub(
        r"\b([xt])(\d+)\b",
        lambda match: ("t" if match.group(1) == "x" else "x") + match.group(2),
        unified,
    )


Poly = Dict[Tuple[int, ...], int]


def _poly_add(left: Poly, right: Poly, modulus: int, sign: int = 1) -> Poly:
    result = dict(left)
    for monomial, coefficient in right.items():
        value = (result.get(monomial, 0) + sign * coefficient) % modulus
        if value:
            result[monomial] = value
        else:
            result.pop(monomial, None)
    return result


def _poly_mul(left: Poly, right: Poly, modulus: int) -> Poly:
    result: Poly = {}
    for left_exp, left_coefficient in left.items():
        for right_exp, right_coefficient in right.items():
            monomial = tuple(map(operator.add, left_exp, right_exp))
            value = (result.get(monomial, 0) + left_coefficient * right_coefficient) % modulus
            if value:
                result[monomial] = value
            else:
                result.pop(monomial, None)
    return result


def _poly_pow(base: Poly, exponent: int, modulus: int, dimension: int) -> Poly:
    if exponent < 0:
        if len(base) != 1:
            raise ValueError("Negative powers are only allowed on Laurent monomials")
        (monomial, coefficient), = base.items()
        if math.gcd(coefficient, modulus) != 1:
            raise ValueError("A negative power requires an invertible coefficient")
        return {
            tuple(exponent * value for value in monomial):
            pow(pow(coefficient, -1, modulus), -exponent, modulus)
        }

    result: Poly = {(0,) * dimension: 1 % modulus}
    factor = base
    power = exponent
    while power:
        if power & 1:
            result = _poly_mul(result, factor, modulus)
        power >>= 1
        if power:
            factor = _poly_mul(factor, factor, modulus)
    return result


class _LaurentParser:
    """Small stdlib parser used only for exact commutation validation."""

    _TOKEN = re.compile(r"\s*(?:(\d+)|([xt]\d+)|(\*\*)|([()+\-*/^]))")

    def __init__(self, expression: str, dimension: int, modulus: int):
        self.dimension = dimension
        self.modulus = modulus
        self.tokens: List[str] = []
        position = 0
        while position < len(expression):
            match = self._TOKEN.match(expression, position)
            if not match:
                if not expression[position:].strip():
                    break
                raise ValueError(
                    f"Unsupported polynomial syntax near {expression[position:]!r}; "
                    "use integers, variables, +, -, *, ^, and parentheses"
                )
            self.tokens.append(next(group for group in match.groups() if group is not None))
            position = match.end()
        self.position = 0

    def parse(self) -> Poly:
        if not self.tokens:
            raise ValueError("Polynomial entries must not be empty")
        value = self._parse_sum()
        if self.position != len(self.tokens):
            raise ValueError(f"Unexpected token {self.tokens[self.position]!r}")
        return value

    def _peek(self) -> Optional[str]:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _take(self, expected: Optional[str] = None) -> str:
        token = self._peek()
        if token is None or (expected is not None and token != expected):
            raise ValueError(f"Expected {expected!r}, found {token!r}")
        self.position += 1
        return token

    def _parse_sum(self) -> Poly:
        value = self._parse_product()
        while self._peek() in {"+", "-"}:
            operation = self._take()
            value = _poly_add(
                value,
                self._parse_product(),
                self.modulus,
                1 if operation == "+" else -1,
            )
        return value

    def _parse_product(self) -> Poly:
        value = self._parse_unary()
        while self._peek() in {"*", "/"}:
            operation = self._take()
            right = self._parse_unary()
            if operation == "/":
                if len(right) != 1 or next(iter(right)) != (0,) * self.dimension:
                    raise ValueError("Division is only allowed by an integer coefficient")
                divisor = next(iter(right.values()))
                if math.gcd(divisor, self.modulus) != 1:
                    raise ValueError(f"{divisor} is not invertible modulo {self.modulus}")
                right = {(0,) * self.dimension: pow(divisor, -1, self.modulus)}
            value = _poly_mul(value, right, self.modulus)
        return value

    def _parse_power(self) -> Poly:
        value = self._parse_atom()
        if self._peek() in {"^", "**"}:
            self._take()
            sign = 1
            if self._peek() in {"+", "-"}:
                sign = -1 if self._take() == "-" else 1
            token = self._take()
            if not token.isdigit():
                raise ValueError("Polynomial exponents must be integers")
            value = _poly_pow(value, sign * int(token), self.modulus, self.dimension)
        return value

    def _parse_unary(self) -> Poly:
        if self._peek() in {"+", "-"}:
            sign = -1 if self._take() == "-" else 1
            value = self._parse_unary()
            return {
                monomial: (sign * coefficient) % self.modulus
                for monomial, coefficient in value.items()
                if (sign * coefficient) % self.modulus
            }
        return self._parse_power()

    def _parse_atom(self) -> Poly:
        token = self._take()
        if token == "(":
            value = self._parse_sum()
            self._take(")")
            return value
        if token.isdigit():
            coefficient = int(token) % self.modulus
            return {(0,) * self.dimension: coefficient} if coefficient else {}
        variable = re.fullmatch(r"([xt])(\d+)", token)
        if variable:
            index = int(variable.group(2))
            if not 1 <= index <= self.dimension:
                raise ValueError(f"Variable {token} lies outside spatial_dim={self.dimension}")
            exponent = [0] * self.dimension
            exponent[index - 1] = 1 if variable.group(1) == "x" else -1
            return {tuple(exponent): 1}
        raise ValueError(f"Unexpected token {token!r}")


def _parse_laurent_poly(expression: str, dimension: int, modulus: int) -> Poly:
    return _LaurentParser(map_variables_to_unified(expression), dimension, modulus).parse()


def _poly_antipode(poly: Poly) -> Poly:
    return {tuple(-value for value in monomial): coefficient for monomial, coefficient in poly.items()}


def _poly_to_string(poly: Poly, modulus: int) -> str:
    if not poly:
        return "0"
    terms = []
    for monomial, coefficient in sorted(poly.items()):
        factors = []
        for index, exponent in enumerate(monomial, 1):
            if exponent:
                variable = f"x{index}" if exponent > 0 else f"t{index}"
                absolute = abs(exponent)
                factors.append(variable if absolute == 1 else f"{variable}^{absolute}")
        if coefficient != 1 or not factors:
            factors.insert(0, str(coefficient % modulus))
        terms.append("*".join(factors))
    return " + ".join(terms)


def validate_stabilizer_commutation(
    translated_matrix: List[List[str]],
    qudit_dim: int,
    spatial_dim: int,
) -> Dict[str, int]:
    """Validate ``sigma^dagger lambda sigma = 0`` in the Laurent ring."""
    pauli_rank = len(translated_matrix[0])
    if pauli_rank % 2:
        raise ValueError(
            "Pauli rank must be even: each generator row must contain "
            "[X_1, ..., X_q, Z_1, ..., Z_q] coordinates"
        )
    qudits_per_cell = pauli_rank // 2
    parsed = [
        [_parse_laurent_poly(entry, spatial_dim, qudit_dim) for entry in row]
        for row in translated_matrix
    ]

    for left_index, left in enumerate(parsed):
        for right_index in range(left_index, len(parsed)):
            right = parsed[right_index]
            pairing: Poly = {}
            for coordinate in range(qudits_per_cell):
                # lambda = [[0, -I], [I, 0]]
                pairing = _poly_add(
                    pairing,
                    _poly_mul(
                        _poly_antipode(left[coordinate + qudits_per_cell]),
                        right[coordinate],
                        qudit_dim,
                    ),
                    qudit_dim,
                )
                pairing = _poly_add(
                    pairing,
                    _poly_mul(
                        _poly_antipode(left[coordinate]),
                        right[coordinate + qudits_per_cell],
                        qudit_dim,
                    ),
                    qudit_dim,
                    sign=-1,
                )
            if pairing:
                raise ValueError(
                    "Stabilizer generators do not commute: "
                    f"(sigma^dagger lambda sigma)[{left_index + 1},{right_index + 1}] "
                    f"= {_poly_to_string(pairing, qudit_dim)} != 0 in the Laurent ring"
                )

    return {
        "generator_count": len(translated_matrix),
        "pauli_rank": pauli_rank,
        "qudits_per_cell": qudits_per_cell,
    }

def generate_ring_definition(d: int, qudit_dim: int) -> tuple[List[str], str]:
    variables_list = []
    relations = []
    for i in range(1, d + 1):
        variables_list.extend([f"x{i}", f"t{i}"])
        relations.append(f"x{i}*t{i} - 1")
    ring_definition = f"R = ZZ/{qudit_dim}[{', '.join(variables_list)}] / ideal({', '.join(relations)})"
    return variables_list, ring_definition

def translate_stabilizers(
    stabilizer_matrix: List[List[str]],
    qudit_dim: int,
    spatial_dim: Optional[int] = None,
    validate_stabilizer: bool = True,
) -> Dict[str, Any]:
    # 1. Validate stabilizer_matrix
    if not isinstance(stabilizer_matrix, list) or not stabilizer_matrix:
        raise ValueError("stabilizer_matrix must be a non-empty list of lists of strings")
    
    row_len = None
    for row in stabilizer_matrix:
        if not isinstance(row, list) or not row:
            raise ValueError("stabilizer_matrix rows must be non-empty lists")
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise ValueError("All rows of stabilizer_matrix must have the same length")
        for elem in row:
            if not isinstance(elem, str):
                raise ValueError("All elements of stabilizer_matrix must be strings")

    # 2. Validate qudit_dim using verify_qudit_dim
    verify_qudit_dim(qudit_dim)
    
    # Check max limit 100000
    if qudit_dim > 100000:
        raise ValueError("qudit_dim must be <= 100000")

    if spatial_dim is not None and (
        not isinstance(spatial_dim, int) or isinstance(spatial_dim, bool) or spatial_dim < 1
    ):
        raise ValueError("spatial_dim must be a positive integer when provided")
    if not isinstance(validate_stabilizer, bool):
        raise ValueError("validate_stabilizer must be a boolean")

    # 3. Regex validation on every element to prevent command injection
    pattern = r"^[a-zA-Z0-9_\-\+\*\/\^\(\)\s\.]+$"
    for row in stabilizer_matrix:
        for elem in row:
            if not re.match(pattern, elem):
                raise ValueError(f"Invalid character or potential command injection in: {elem}")

    # 4. Scan elements for variables and validate them
    for row in stabilizer_matrix:
        for elem in row:
            words = re.findall(r'\w+', elem)
            for word in words:
                if any(c.isalpha() for c in word):
                    if any(c.isupper() for c in word):
                        raise ValueError(f"Uppercase variables are not allowed: {word}")
                    is_legacy = word in {'x', 'y', 'z', 't', 'u', 'w'}
                    is_unified = bool(re.match(r'^(x|t)[1-9]\d*$', word))
                    if not (is_legacy or is_unified):
                        raise ValueError(f"Invalid variable: {word}")

    # 5. Translate negative variables and map legacy to unified
    translated_matrix = []
    for row in stabilizer_matrix:
        translated_row = []
        for elem in row:
            elem_trans = map_variables_to_unified(elem)
            translated_row.append(elem_trans)
        translated_matrix.append(translated_row)

    # 6. Find highest variable index
    d_model = 0
    for row in translated_matrix:
        for elem in row:
            for m in re.finditer(r'\b[xt](\d+)\b', elem):
                d_model = max(d_model, int(m.group(1)))

    # 7. Resolve the ambient ring.  Explicit spatial_dim declares axes even when
    # their variables do not occur in any stabilizer coefficient.
    if spatial_dim is not None and spatial_dim < d_model:
        raise ValueError(
            f"spatial_dim={spatial_dim} is smaller than variable axis {d_model} used by the model"
        )
    d = spatial_dim if spatial_dim is not None else max(d_model, 1)

    validation_metadata = {
        "enabled": validate_stabilizer,
        "generator_count": len(translated_matrix),
        "pauli_rank": len(translated_matrix[0]),
        "qudits_per_cell": len(translated_matrix[0]) // 2,
    }
    if validate_stabilizer:
        validation_metadata.update(
            validate_stabilizer_commutation(translated_matrix, qudit_dim, d)
        )

    # 8. Generate variables list and relations
    variables_list, ring_definition = generate_ring_definition(d, qudit_dim)

    # Transpose matrix for M2 representation
    num_rows = len(translated_matrix)
    num_cols = len(translated_matrix[0])
    transposed = [[translated_matrix[r][c] for r in range(num_rows)] for c in range(num_cols)]

    m2_matrix_rows = []
    for r in transposed:
        m2_matrix_rows.append("{" + ", ".join(r) + "}")
    matrix_definition = "{" + ", ".join(m2_matrix_rows) + "}"

    antipode_transposed = [
        [apply_laurent_antipode(translated_matrix[r][c]) for r in range(num_rows)]
        for c in range(num_cols)
    ]
    antipode_matrix_definition = "{" + ", ".join(
        "{" + ", ".join(row) + "}" for row in antipode_transposed
    ) + "}"

    # Check if input has unified variables
    has_unified_input = False
    for row in stabilizer_matrix:
        for elem in row:
            if re.search(r'\b[xt][1-9]\d*\b', elem):
                has_unified_input = True
                break

    # Legacy names exist only for the first three axes.  For D>3 expose a
    # completely unified public ring instead of a mixed legacy/unified list
    # that downstream consumers cannot interpret consistently.
    if not has_unified_input and d <= 3:
        # Map variables list
        legacy_vars = []
        for v in variables_list:
            if v == "x1": legacy_vars.append("x")
            elif v == "t1": legacy_vars.append("t")
            elif v == "x2": legacy_vars.append("y")
            elif v == "t2": legacy_vars.append("u")
            elif v == "x3": legacy_vars.append("z")
            elif v == "t3": legacy_vars.append("w")
            else: legacy_vars.append(v)
        variables_list = legacy_vars

        # Map ring_definition
        ring_definition = re.sub(r'\bx1\b', 'x', ring_definition)
        ring_definition = re.sub(r'\bt1\b', 't', ring_definition)
        ring_definition = re.sub(r'\bx2\b', 'y', ring_definition)
        ring_definition = re.sub(r'\bt2\b', 'u', ring_definition)
        ring_definition = re.sub(r'\bx3\b', 'z', ring_definition)
        ring_definition = re.sub(r'\bt3\b', 'w', ring_definition)

        # Map matrix_definition
        matrix_definition = re.sub(r'\bx1\b', 'x', matrix_definition)
        matrix_definition = re.sub(r'\bt1\b', 't', matrix_definition)
        matrix_definition = re.sub(r'\bx2\b', 'y', matrix_definition)
        matrix_definition = re.sub(r'\bt2\b', 'u', matrix_definition)
        matrix_definition = re.sub(r'\bx3\b', 'z', matrix_definition)
        matrix_definition = re.sub(r'\bt3\b', 'w', matrix_definition)

        # Keep the barred presentation in the same public variable style.
        antipode_matrix_definition = re.sub(r'\bx1\b', 'x', antipode_matrix_definition)
        antipode_matrix_definition = re.sub(r'\bt1\b', 't', antipode_matrix_definition)
        antipode_matrix_definition = re.sub(r'\bx2\b', 'y', antipode_matrix_definition)
        antipode_matrix_definition = re.sub(r'\bt2\b', 'u', antipode_matrix_definition)
        antipode_matrix_definition = re.sub(r'\bx3\b', 'z', antipode_matrix_definition)
        antipode_matrix_definition = re.sub(r'\bt3\b', 'w', antipode_matrix_definition)

    variable_pairs = [
        variables_list[index:index + 2]
        for index in range(0, len(variables_list), 2)
    ]

    return {
        "variables": variables_list,
        "ring_definition": ring_definition,
        "matrix_definition": matrix_definition,
        "antipode_matrix_definition": antipode_matrix_definition,
        "spatial_dim": d,
        "variable_pairs": variable_pairs,
        "matrix_convention": {
            "input_rows": "stabilizer generators",
            "pauli_coordinates": "[X_1, ..., X_q, Z_1, ..., Z_q]",
            "m2_matrix": "sigma: L -> P (transpose of input rows)",
            "dagger": "transpose followed by Laurent antipode",
            "symplectic_form": "lambda = [[0, -I], [I, 0]]",
        },
        "stabilizer_validation": validation_metadata,
    }

def map_variables_to_legacy(elem: str) -> str:
    elem = re.sub(r'\bx1\b', 'x', elem)
    elem = re.sub(r'\bt1\b', 't', elem)
    elem = re.sub(r'\bx2\b', 'y', elem)
    elem = re.sub(r'\bt2\b', 'u', elem)
    elem = re.sub(r'\bx3\b', 'z', elem)
    elem = re.sub(r'\bt3\b', 'w', elem)
    return elem

def parse_monomial(term_str: str) -> tuple[int, Dict[int, int]]:
    term_str = term_str.strip().replace(" ", "").replace("**", "^")
    if not term_str:
        return 0, {}
    
    coef_match = re.match(r'^([+-]?\d+)(?:\*(.*))?$', term_str)
    if coef_match:
        coef = int(coef_match.group(1))
        rest = coef_match.group(2) or ""
    else:
        sign = 1
        if term_str.startswith("-"):
            sign = -1
            term_str = term_str[1:]
        elif term_str.startswith("+"):
            term_str = term_str[1:]
        coef = sign
        rest = term_str

    net_exps = {}
    if rest:
        factors = rest.split("*")
        for factor in factors:
            factor = factor.strip()
            if not factor:
                continue
            m = re.match(r'^([xt])(\d+)(?:\^([+-]?\d+))?$', factor)
            if not m:
                if factor.isdigit():
                    coef *= int(factor)
                    continue
                raise ValueError(f"Invalid factor: {factor}")
            var_type = m.group(1)
            var_idx = int(m.group(2))
            exp = int(m.group(3)) if m.group(3) else 1
            if var_type == 'x':
                net_exps[var_idx] = net_exps.get(var_idx, 0) + exp
            else:
                net_exps[var_idx] = net_exps.get(var_idx, 0) - exp
    return coef, net_exps

def normalize_laurent_poly(poly_str: str) -> str:
    """
    Clears denominators and common monomial factors from a Laurent polynomial string.
    e.g. "x1^2*t2 - x2 + 1" -> "x1^2 - x2^2 + x2" (using t2 = x2^-1)
    """
    is_legacy = bool(re.search(r'\b[xyztuw]\b', poly_str))
    poly_trans = map_variables_to_unified(poly_str)
    
    # Split by + and - keeping signs
    terms = re.findall(r'[+-]?[^+-]+', poly_trans)
    
    terms_data = []
    max_idx = 0
    for t in terms:
        coef, net_exps = parse_monomial(t)
        if coef != 0:
            terms_data.append((coef, net_exps))
            if net_exps:
                max_idx = max(max_idx, max(net_exps.keys()))
                
    if not terms_data:
        return "0"
        
    # Find minimum net exponent for each variable
    min_exps = {}
    for i in range(1, max_idx + 1):
        min_exps[i] = min(net_exps.get(i, 0) for _, net_exps in terms_data)
        
    # Adjust exponents
    new_terms = []
    for idx, (coef, net_exps) in enumerate(terms_data):
        term_parts = []
        abs_coef = abs(coef)
        has_vars = False
        for i in range(1, max_idx + 1):
            new_exp = net_exps.get(i, 0) - min_exps[i]
            if new_exp > 0:
                has_vars = True
                term_parts.append(f"x{i}^{new_exp}" if new_exp > 1 else f"x{i}")
                
        if abs_coef != 1 or not has_vars:
            term_parts.insert(0, str(abs_coef))
            
        term_str = "*".join(term_parts)
        if coef < 0:
            new_terms.append(f"- {term_str}")
        else:
            if idx == 0:
                new_terms.append(term_str)
            else:
                new_terms.append(f"+ {term_str}")
                
    res = " ".join(new_terms)
    res = re.sub(r'\s+', ' ', res).strip()
    
    if is_legacy:
        res = map_variables_to_legacy(res)
    return res
