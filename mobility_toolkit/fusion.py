import re
import math
import itertools
from typing import List, Dict, Any, Optional
from fractions import Fraction
from mobility_toolkit.bridge import run_m2_script, run_macaulay2
from mobility_toolkit.translate import translate_stabilizers
from mobility_toolkit import utils

class GF2Poly:
    def __init__(self, val: int):
        self.val = val
        
    @property
    def degree(self) -> int:
        if self.val == 0:
            return -1
        return self.val.bit_length() - 1
        
    def add(self, other: 'GF2Poly') -> 'GF2Poly':
        return GF2Poly(self.val ^ other.val)
        
    def multiply(self, other: 'GF2Poly') -> 'GF2Poly':
        res = 0
        a = self.val
        b = other.val
        while b > 0:
            if b & 1:
                res ^= a
            a <<= 1
            b >>= 1
        return GF2Poly(res)
        
    def divmod(self, other: 'GF2Poly') -> tuple['GF2Poly', 'GF2Poly']:
        if other.val == 0:
            raise ZeroDivisionError("GF2Poly division by zero")
        q = 0
        r = self.val
        d_other = other.degree
        val_other = other.val
        while True:
            d_r = r.bit_length() - 1
            if r == 0 or d_r < d_other:
                break
            shift = d_r - d_other
            q ^= (1 << shift)
            r ^= (val_other << shift)
        return GF2Poly(q), GF2Poly(r)
        
    def rem(self, other: 'GF2Poly') -> 'GF2Poly':
        return self.divmod(other)[1]
        
    def __eq__(self, other):
        if isinstance(other, GF2Poly):
            return self.val == other.val
        return False

def clean_wsl_garbage(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        normalized = line.replace(" ", "").lower()
        if "wsl:" in normalized or "localhost" in normalized or "connection" in normalized or "n/ec" in normalized:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def safe_run_m2_script(script_content: str, timeout_seconds: float = 60.0):
    code, stdout, stderr = run_m2_script(script_content, timeout_seconds)
    stdout_clean = clean_wsl_garbage(stdout)
    stderr_clean = clean_wsl_garbage(stderr)

    return code, stdout_clean, stderr_clean

def safe_run_macaulay2(script: str, timeout: int = 30):
    res = run_macaulay2(script, timeout)
    stdout_clean = clean_wsl_garbage(res["stdout"])
    stderr_clean = clean_wsl_garbage(res["stderr"])
    return {
        "exit_code": res["exit_code"],
        "stdout": stdout_clean,
        "stderr": stderr_clean,
        "timeout": res["timeout"]
    }

def gf2_poly_powmod(base: GF2Poly, exp: int, mod: GF2Poly) -> GF2Poly:
    res = GF2Poly(1)
    curr = base
    while exp > 0:
        if exp % 2 == 1:
            res = res.multiply(curr).rem(mod)
        exp //= 2
        # ⚡ Bolt: Skip unnecessary multiply/rem on final exponentiation step.
        if exp > 0:
            curr = curr.multiply(curr).rem(mod)
    return res

def get_divisors(n: int) -> list:
    divs = []
    for i in range(1, int(n**0.5) + 1):
        if n % i == 0:
            divs.append(i)
            if i * i != n:
                divs.append(n // i)
    divs.sort()
    return divs

def parse_gf2_poly(poly_str: str) -> GF2Poly:
    terms = poly_str.replace(" ", "").split("+")
    val = 0
    for term in terms:
        term = term.strip()
        if term == "1":
            val ^= 1
        elif term == "q":
            val ^= 2
        elif term.startswith("q^"):
            exp = int(term[2:])
            val ^= (1 << exp)
    return GF2Poly(val)

class Z2Polynomial:
    def __init__(self, terms: set[tuple[int, int]] = None):
        # terms is a set of exponent tuples (exp_x, exp_y) with coefficient 1
        self.terms = terms if terms is not None else set()
        
    def __add__(self, other: 'Z2Polynomial') -> 'Z2Polynomial':
        # Over Z2, addition is XOR (symmetric difference)
        return Z2Polynomial(self.terms ^ other.terms)
        
    def __sub__(self, other: 'Z2Polynomial') -> 'Z2Polynomial':
        # Over Z2, subtraction is the same as addition
        return Z2Polynomial(self.terms ^ other.terms)
        
    def __mul__(self, other: 'Z2Polynomial') -> 'Z2Polynomial':
        res_terms = set()
        for (ax, ay) in self.terms:
            for (bx, by) in other.terms:
                term = (ax + bx, ay + by)
                if term in res_terms:
                    res_terms.remove(term)
                else:
                    res_terms.add(term)
        return Z2Polynomial(res_terms)
        
    def __pow__(self, power: int) -> 'Z2Polynomial':
        if not isinstance(power, int) or power < 0:
            raise ValueError("Power must be a non-negative integer")
        if power == 0:
            return Z2Polynomial({(0, 0)})
        res = Z2Polynomial({(0, 0)})
        base = self
        while power > 0:
            if power % 2 == 1:
                res = res * base
            power //= 2
            # ⚡ Bolt: Skip unnecessary square on final exponentiation step.
            if power > 0:
                # ⚡ Bolt: Over GF(2), (A+B)^2 = A^2 + B^2 (Freshman's Dream)
                # This avoids O(N^2) multiplication when squaring.
                base = Z2Polynomial({(ax * 2, ay * 2) for ax, ay in base.terms})
        return res

def tokenize(s: str) -> List[str]:
    s = s.replace(" ", "")
    s = s.replace("**", "^")
    return re.findall(r'\d+|x|y|\(|\)|\+|\-|\*|\^', s)

class Z2PolynomialParser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0
        
    def peek(self) -> str:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None
        
    def consume(self, expected: str = None) -> str:
        t = self.peek()
        if expected is not None and t != expected:
            raise ValueError(f"Expected {expected}, got {t}")
        self.pos += 1
        return t
        
    def parse_expression(self) -> Z2Polynomial:
        res = self.parse_term()
        while self.peek() in ('+', '-'):
            op = self.consume()
            right = self.parse_term()
            res = res + right # subtraction is also addition mod 2
        return res
        
    def parse_term(self) -> Z2Polynomial:
        res = self.parse_factor()
        while self.peek() == '*':
            self.consume('*')
            right = self.parse_factor()
            res = res * right
        return res
        
    def parse_factor(self) -> Z2Polynomial:
        if self.peek() == '-':
            self.consume('-')
            return self.parse_factor()
        elif self.peek() == '+':
            self.consume('+')
            return self.parse_factor()
            
        res = self.parse_primary()
        if self.peek() == '^':
            self.consume('^')
            power_str = self.consume()
            if not power_str.isdigit():
                raise ValueError(f"Expected integer power exponent, got {power_str}")
            res = res ** int(power_str)
        return res
        
    def parse_primary(self) -> Z2Polynomial:
        t = self.peek()
        if t == '(':
            self.consume('(')
            res = self.parse_expression()
            self.consume(')')
            return res
        elif t == 'x':
            self.consume('x')
            return Z2Polynomial({(1, 0)})
        elif t == 'y':
            self.consume('y')
            return Z2Polynomial({(0, 1)})
        elif t is not None and t.isdigit():
            val = int(self.consume())
            return Z2Polynomial({(0, 0)}) if val % 2 == 1 else Z2Polynomial(set())
        else:
            raise ValueError(f"Unexpected token in primary: {t}")

def parse_poly_str(poly_str: str) -> set[tuple[int, int]]:
    if not poly_str or poly_str.strip() == "0":
        return set()
    tokens = tokenize(poly_str)
    parser = Z2PolynomialParser(tokens)
    poly = parser.parse_expression()
    if parser.pos < len(tokens):
        raise ValueError(f"Extra tokens left unparsed: {tokens[parser.pos:]}")
    return poly.terms

def shift_poly(terms: set[tuple[int, int]]) -> set[tuple[int, int]]:
    if not terms:
        return set()
    min_x = min(t[0] for t in terms)
    min_y = min(t[1] for t in terms)
    return {(t[0] - min_x, t[1] - min_y) for t in terms}

def format_direction(u: int, v: int) -> str:
    x_part = ""
    if u == 1:
        x_part = "x"
    elif u > 1:
        x_part = f"x^{u}"
    
    y_part = ""
    if v == 1:
        y_part = "y"
    elif v > 1:
        y_part = f"y^{v}"
    
    if x_part and y_part:
        return f"{x_part}*{y_part}"
    elif x_part:
        return x_part
    else:
        return y_part

def format_term(exp_x: int, exp_y: int) -> str:
    if exp_x == 0 and exp_y == 0:
        return "1"
    x_part = ""
    if exp_x == 1:
        x_part = "x"
    elif exp_x > 1:
        x_part = f"x^{exp_x}"
    
    y_part = ""
    if exp_y == 1:
        y_part = "y"
    elif exp_y > 1:
        y_part = f"y^{exp_y}"
        
    if x_part and y_part:
        return f"{x_part}*{y_part}"
    elif x_part:
        return x_part
    else:
        return y_part

def format_poly(terms: set[tuple[int, int]]) -> str:
    if not terms:
        return "0"
    sorted_terms = sorted(list(terms), key=lambda t: (t[0] + t[1], t[1], t[0]))
    formatted_parts = [format_term(tx, ty) for tx, ty in sorted_terms]
    return " + ".join(formatted_parts)

def validate_variables_only_x_y(poly_str: str):
    words = re.findall(r'[a-zA-Z_]+', poly_str)
    for word in words:
        if word not in {'x', 'y'}:
            raise ValueError(f"Invalid variable '{word}' found. Only 'x' and 'y' are allowed.")

def fuse_vector_sets(set1, set2):
    fused_set = set()
    for K1 in set1:
        for K2 in set2:
            choices = []
            for k1, k2 in zip(K1, K2):
                if k1 != k2:
                    choices.append([max(k1, k2)])
                elif k1 == 0:
                    choices.append([0])
                else:
                    choices.append(list(range(k1 + 1)))
            for K_f in itertools.product(*choices):
                fused_set.add(K_f)
    return fused_set

def construct_monomial(shift: List[int], variables: List[str] = None) -> str:
    is_unified = False
    if variables:
        is_unified = any(re.match(r'^x\d+$', v) for v in variables)
        
    if is_unified:
        terms = []
        for idx, val in enumerate(shift):
            var_idx = idx + 1
            if val > 0:
                terms.append(f"x{var_idx}^{val}" if val > 1 else f"x{var_idx}")
            elif val < 0:
                power = -val
                terms.append(f"t{var_idx}^{power}" if power > 1 else f"t{var_idx}")
        if not terms:
            return "1"
        return "*".join(terms)
    else:
        pos_vars = ['x', 'y', 'z']
        inv_vars = ['t', 'u', 'w']
        terms = []
        for idx, val in enumerate(shift):
            if idx >= len(pos_vars):
                break
            if val > 0:
                terms.append(f"{pos_vars[idx]}^{val}" if val > 1 else pos_vars[idx])
            elif val < 0:
                power = -val
                terms.append(f"{inv_vars[idx]}^{power}" if power > 1 else inv_vars[idx])
        if not terms:
            return "1"
        return "*".join(terms)


def parse_poly_str_unified(poly_str: str, variables: List[str]) -> set[tuple[int, ...]]:
    from mobility_toolkit.translate import map_variables_to_unified, parse_monomial
    poly_trans = map_variables_to_unified(poly_str)
    poly_trans = poly_trans.replace(" ", "")
    if not poly_trans or poly_trans == "0":
        return set()
        
    var_indices = []
    for v in variables:
        v_trans = map_variables_to_unified(v)
        m = re.match(r'^[xt](\d+)$', v_trans)
        var_indices.append(int(m.group(1)) if m else 1)
        
    terms = re.findall(r'[+-]?[^+-]+', poly_trans)
    res = set()
    for t in terms:
        coef, net_exps = parse_monomial(t)
        if coef != 0:
            tup = tuple(net_exps.get(idx, 0) for idx in var_indices)
            if tup in res:
                res.remove(tup)
            else:
                res.add(tup)
    return res

def shift_poly_general(terms: set[tuple[int, ...]]) -> set[tuple[int, ...]]:
    if not terms:
        return set()
    d = len(next(iter(terms)))
    min_vals = tuple(min(t[i] for t in terms) for i in range(d))
    return {tuple(t[i] - min_vals[i] for i in range(d)) for t in terms}

def check_collinear_general(nonzero_exps: List[tuple[int, ...]]) -> tuple[bool, Optional[tuple[int, ...]]]:
    if not nonzero_exps:
        return True, None
    d = len(nonzero_exps[0])
    first = nonzero_exps[0]
    g = math.gcd(*first)
    if g == 0:
        return True, tuple(0 for _ in range(d))
    dir_vec = tuple(x // g for x in first)
    
    for exp in nonzero_exps[1:]:
        g_exp = math.gcd(*exp)
        if g_exp == 0:
            continue
        exp_dir = tuple(x // g_exp for x in exp)
        if exp_dir != dir_vec:
            return False, None
    return True, dir_vec

def format_direction_general(dir_vec: tuple[int, ...], variables: List[str]) -> str:
    parts = []
    for idx, val in enumerate(dir_vec):
        if val > 0:
            var_name = variables[idx]
            parts.append(f"{var_name}^{val}" if val > 1 else var_name)
    return "*".join(parts) if parts else "1"

def format_poly_general(terms: set[tuple[int, ...]], variables: List[str]) -> str:
    if not terms:
        return "0"
    sorted_terms = sorted(list(terms), key=lambda t: (sum(t), t[::-1]))
    formatted_parts = []
    for t in sorted_terms:
        parts = []
        for idx, val in enumerate(t):
            if val > 0:
                var_name = variables[idx]
                parts.append(f"{var_name}^{val}" if val > 1 else var_name)
        term_str = "*".join(parts)
        if not term_str:
            term_str = "1"
        formatted_parts.append(term_str)
    return " + ".join(formatted_parts)

def check_ideal_principal(ring_def: str, generators: List[str]) -> tuple[bool, Optional[str]]:
    """
    Runs Macaulay2 trim to verify if the ideal is principal and extract its generator.
    """
    from mobility_toolkit.translate import normalize_laurent_poly
    normalized_gens = []
    for g in generators:
        norm = normalize_laurent_poly(g)
        if norm != "0" and norm.strip() != "":
            normalized_gens.append(norm)
    seen = set()
    dedup_gens = []
    for g in normalized_gens:
        if g not in seen:
            seen.add(g)
            dedup_gens.append(g)
            
    if not dedup_gens:
        return True, "0"
    if len(dedup_gens) == 1:
        return True, dedup_gens[0]
        
    generators_str = ", ".join(dedup_gens)
    script = f"""{ring_def}
I = ideal({generators_str})
J = trim I
print "VALUE:NUMGENS"
print (numgens J)
print "VALUE:GENERATORS"
print J
"""
    code, stdout, stderr = safe_run_m2_script(script)
    if code != 0:
        raise RuntimeError(f"Macaulay2 failed to check principal ideal: {stderr or stdout}")
        
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        numgens_idx = lines.index("VALUE:NUMGENS")
        gens_idx = lines.index("VALUE:GENERATORS")
    except ValueError:
        raise RuntimeError(f"Could not parse Macaulay2 output: {stdout}")
        
    numgens_val = None
    for i in range(numgens_idx + 1, gens_idx):
        line = lines[i].strip()
        if not re.match(r'^[io]\d+\s*[:=]', line) and line != "":
            numgens_val = line
            break
            
    if numgens_val is None:
        raise ValueError(f"Could not parse numgens from Macaulay2 output: {stdout}")
    numgens = int(re.search(r'\d+', numgens_val).group(0))
    
    if numgens > 1:
        return False, None
    elif numgens == 0:
        return True, "0"
        
    gen_lines = []
    for i in range(gens_idx + 1, len(lines)):
        line = lines[i].strip()
        if not re.match(r'^[io]\d+\s*[:=]', line) and line != "":
            gen_lines.append(line)
            
    gen_content = " ".join(gen_lines).strip()
    match = re.search(r'ideal\s*\((.*?)\)', gen_content)
    if match:
        return True, match.group(1).strip()
        
    matrix_match = re.search(r'matrix\s*\{\{(.*?)\}\}', gen_content)
    if matrix_match:
        return True, matrix_match.group(1).strip()
        
    braces_match = re.search(r'\{\{(.*?)\}\}', gen_content)
    if braces_match:
        return True, braces_match.group(1).strip()
        
    bar_match = re.search(r'\|(.*?)\|', gen_content)
    if bar_match:
        return True, bar_match.group(1).strip()
        
    return True, gen_content

def classify_divisor(g_terms: set[tuple[int, ...]], qudit_dim: int = 2, variables: Optional[List[str]] = None) -> Dict[str, Any]:
    if variables is None:
        variables = ['x', 'y']
    d = len(variables)
    
    g_terms = shift_poly_general(g_terms)
    
    if len(g_terms) == 1 and all(x == 0 for x in next(iter(g_terms))):
        return {
            "mobility_class": "alpha",
            "lfsr_period": 1,
            "characteristic_polynomial": "1"
        }
        
    nonzero_exps = [t for t in g_terms if any(x != 0 for x in t)]
    if not nonzero_exps:
        return {
            "mobility_class": "alpha",
            "lfsr_period": 1,
            "characteristic_polynomial": "1"
        }
        
    is_collinear, dir_vec = check_collinear_general(nonzero_exps)
    
    if not is_collinear:
        return {
            "mobility_class": "gamma",
            "lfsr_period": None,
            "characteristic_polynomial": format_poly_general(g_terms, variables)
        }
        
    nonzero_idx = next(idx for idx, val in enumerate(dir_vec) if val > 0)
    p_val = dir_vec[nonzero_idx]
    
    t_terms = []
    for exp in g_terms:
        k = exp[nonzero_idx] // p_val
        t_terms.append(k)
        
    t_expr_parts = []
    for k in sorted(t_terms):
        if k == 0:
            t_expr_parts.append("1")
        elif k == 1:
            t_expr_parts.append("q")
        else:
            t_expr_parts.append(f"q^{k}")
    t_expr = " + ".join(t_expr_parts)
    
    m2_script = f"""R = ZZ/{qudit_dim}[q]
t_poly = promote(({t_expr}), R)
F = factor t_poly
for i from 0 to #F-1 do (
    P = F#i;
    print ("UFACTOR:" | toString P#0 | ":" | toString P#1 | ":" | toString (degree P#0)#0)
)
"""
    code, stdout, stderr = safe_run_m2_script(m2_script)
    if code != 0:
        raise RuntimeError(f"Macaulay2 script failed: {stderr or stdout}")
        
    factor_lines = []
    for line in stdout.splitlines():
        sline = line.strip()
        if sline.startswith("UFACTOR:"):
            factor_lines.append(sline[8:])
            
    periods = []
    for f_line in factor_lines:
        parts = f_line.split(":")
        if len(parts) == 3:
            factor_str, mult_str, deg_str = parts
            mult = int(mult_str)
            deg = int(deg_str)
            if deg > 25:
                raise ValueError("Degree of factor is too high for periodicity calculation.")
            
            # Compute divisors of qudit_dim^deg - 1 in python
            M = (qudit_dim ** deg) - 1
            divs = get_divisors(M)
            
            # Generate Macaulay2 script to find the order
            check_lines = []
            for k in divs:
                check_lines.append(f"if qc^{k} == 1 then ( print \"ORDER:{k}\"; ) else")
            check_lines.append("( print \"ORDER:None\"; )")
            checks_str = " ".join(check_lines)
            
            order_script = f"""R = ZZ/{qudit_dim}[q]
I = ideal(promote(({factor_str}), R))
S = R/I
qc = promote(q, S)
{checks_str}
"""
            code_ord, stdout_ord, stderr_ord = safe_run_m2_script(order_script)
            if code_ord != 0:
                raise RuntimeError(f"Macaulay2 order check failed: {stderr_ord or stdout_ord}")
                
            order = None
            for ord_line in stdout_ord.splitlines():
                ord_line = ord_line.strip()
                if ord_line.startswith("ORDER:"):
                    ord_val = ord_line[6:]
                    if ord_val != "None":
                        order = int(ord_val)
                        break
                        
            if order is None:
                order = M
                
            scaled_period = order * (qudit_dim ** math.ceil(math.log(mult, qudit_dim)))
            periods.append(scaled_period)
            
    # Bolt: replaced manual lcm calculation with C-optimized math.lcm
    total_period = math.lcm(*periods) if periods else 1
        
    dir_str = format_direction_general(dir_vec, variables)
    return {
        "mobility_class": f"beta_{{{dir_str}, {total_period}}}",
        "lfsr_period": total_period,
        "characteristic_polynomial": format_poly_general(g_terms, variables)
    }


def analyze_fusion_interference(stabilizer_matrix: List[List[str]], qudit_dim: int, shifts: List[List[int]]) -> Dict[str, Any]:
    """Computes point excitation annihilator ideal dimension and determines if any shift causes a dimension drop.
    
    Args:
        stabilizer_matrix: List of lists of strings representing the stabilizers.
        qudit_dim: Qudit dimension (must be a prime number).
        shifts: List of shift vectors (each shift is a list of integers).
        
    Returns:
        A dictionary containing:
            - annihilator_dimension: Krull dimension of the point excitation annihilator variety (int).
            - dimension_drop: True if the dimension drops under any shift, False otherwise (bool).
    """
    utils.log_python_run("mobility_toolkit.fusion", "analyze_fusion_interference", (stabilizer_matrix, qudit_dim, shifts), {}, "PENDING")
    
    # Validate shifts
    if not isinstance(shifts, list):
        raise ValueError("shifts must be a list.")
    for s in shifts:
        if not isinstance(s, list):
            raise ValueError("Each shift must be a list of integers.")
        for val in s:
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValueError("Shift values must be integers.")

    # 1. Translate matrix
    shift_dim = max(len(s) for s in shifts) if shifts else 0
    translation = translate_stabilizers(stabilizer_matrix, qudit_dim, spatial_dim=shift_dim)
    ring_def = translation["ring_definition"]
    # Use the same barred presentation as the corrected Ruba--Yang Q^0 path.
    matrix_def = translation["antipode_matrix_definition"]
    variables = translation["variables"]

    # 2. Determine saturation product (product of active positive variables)
    active_pos_vars = [
        v for v in variables 
        if v in {'x', 'y', 'z'} or (v.startswith('x') and v[1:].isdigit())
    ]
    sat_prod = "*".join(active_pos_vars) if active_pos_vars else "1"

    # 3. Construct Macaulay2 script
    script_lines = [
        ring_def,
        f"M = matrix(R, {matrix_def})",
        "PL = coker M",
        "E = Ext^1(PL, R^1)",
        "I = annihilator E",
        'print "VALUE:DIM_ORIG_START"',
        "print (dim I)"
    ]

    for idx, shift in enumerate(shifts):
        monomial = construct_monomial(shift, variables)
        script_lines.extend([
            f"P{idx} = ideal(1 - ({monomial}))",
            f"J{idx} = I : P{idx}",
            f"Jsat{idx} = saturate(J{idx}, {sat_prod})",
            f'print "VALUE:DIM_SHIFT_{idx}"',
            f"print (dim Jsat{idx})"
        ])

    script_content = "\n".join(script_lines)

    # 4. Execute M2 script
    res = safe_run_macaulay2(script_content)
    if res["exit_code"] != 0:
        raise RuntimeError(f"Macaulay2 execution failed: {res['stderr'] or res['stdout']}")

    # 5. Parse output
    stdout = res["stdout"]
    lines = [line.strip() for line in stdout.split('\n')]

    def get_val_after_marker(marker: str) -> str:
        try:
            idx = lines.index(marker)
            for i in range(idx + 1, len(lines)):
                line = lines[i]
                if not re.match(r'^i\d+\s*:', line) and line != "":
                    return line
        except ValueError:
            pass
        return None

    def parse_dim(dim_str: str) -> int:
        dim_str = dim_str.strip()
        if dim_str == "-1" or "infinity" in dim_str or "inf" in dim_str:
            return -1
        num_match = re.search(r'-?\d+', dim_str)
        if num_match:
            return int(num_match.group(0))
        raise ValueError(f"Could not convert dimension '{dim_str}' to integer.")

    orig_dim_str = get_val_after_marker("VALUE:DIM_ORIG_START")
    if orig_dim_str is None:
        raise ValueError(f"Could not parse original dimension from Macaulay2 output: {stdout}")
    original_dim = parse_dim(orig_dim_str)

    dimension_drop = False
    for idx in range(len(shifts)):
        shift_dim_str = get_val_after_marker(f"VALUE:DIM_SHIFT_{idx}")
        if shift_dim_str is None:
            raise ValueError(f"Could not parse dimension for shift {idx} from Macaulay2 output: {stdout}")
        shift_dim = parse_dim(shift_dim_str)
        if shift_dim < original_dim:
            dimension_drop = True

    result = {
        "annihilator_dimension": original_dim,
        "dimension_drop": dimension_drop,
        "definition": "shift-colon dimension test on Ann Ext^1_R(bar(P/L), R)",
        "provenance": "independent fusion-interference helper; not Ruba--Yang Cech braiding",
    }
    
    utils.save_discovery("fusion_interference_discovery", result)
    utils.log_python_run("mobility_toolkit.fusion", "analyze_fusion_interference", (stabilizer_matrix, qudit_dim, shifts), {}, result)
    
    return result

def solve_sset_fusion(
    poly_f: str,
    poly_g: str,
    qudit_dim: int = 2,
    variables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Solves SSET characteristic polynomial, LFSR periodicities, and fusion rules.

    Args:
        poly_f (str): First polynomial.
        poly_g (str): Second polynomial.
        qudit_dim (int): Qudit dimension.
        variables (list): Active variables list.
    Returns:
        Dict[str, Any]: SSET fusion properties and characteristic polynomials.
    """
    utils.verify_qudit_dim(qudit_dim)
    log_kwargs = {"qudit_dim": qudit_dim, "variables": variables}
    utils.log_python_run(
        "mobility_toolkit.fusion",
        "solve_sset_fusion",
        (poly_f, poly_g),
        log_kwargs,
        "PENDING",
    )
    
    class_fusion_mode = any(cls in poly_g for cls in ["beta_", "alpha", "gamma"])
    
    if variables is None:
        variables = ['x', 'y']
            
    ring_vars = ", ".join(variables)
    d = len(variables)
    
    if not class_fusion_mode and set(variables) == {'x', 'y'}:
        validate_variables_only_x_y(poly_f)
        validate_variables_only_x_y(poly_g)
        
    # Check for zero polynomials and separability in M2
    script_lines = [
        f"R = ZZ/{qudit_dim}[{ring_vars}]",
        f"f = promote(({poly_f}), R)",
        "isSeparable = true",
        "F_fac = factor f",
        "for i from 0 to #F_fac-1 do (",
        "    P = F_fac#i;",
        "    if #(support(P#0)) > 1 then isSeparable = false;",
        ")",
        'print ("SEPARABLE:" | toString isSeparable)',
        'print ("F_VAL:" | toString f)'
    ]
    if not class_fusion_mode:
        script_lines.extend([
            f"m = promote(({poly_g}), R)",
            'print ("G_VAL:" | toString m)'
        ])
        
    code, stdout, stderr = safe_run_m2_script("\n".join(script_lines))
    if code != 0:
        if "division by zero" in stderr.lower() or "division by zero" in stdout.lower():
            raise ValueError("Division by zero in polynomial definition.")
        raise ValueError(f"Invalid polynomial syntax: {stderr or stdout}")
        
    is_separable = False
    f_val = ""
    g_val = ""
    for line in stdout.splitlines():
        sline = line.strip()
        if sline.startswith("SEPARABLE:"):
            is_separable = (sline[10:] == "true")
        elif sline.startswith("F_VAL:"):
            f_val = sline[6:]
        elif sline.startswith("G_VAL:"):
            g_val = sline[6:]
            
    if f_val == "0":
        raise ValueError("f cannot be the zero polynomial.")
    if not class_fusion_mode and g_val == "0":
        raise ValueError("g cannot be the zero polynomial.")
        
    if class_fusion_mode and not is_separable:
        raise NotImplementedError("Non-separable multivariate polynomial factorization over FF(2) is not supported.")
        
    if class_fusion_mode:
        # Factor f using Macaulay2
        factor_script = f"""R = ZZ/{qudit_dim}[{ring_vars}]
f = promote(({poly_f}), R)
F = factor f
for i from 0 to #F-1 do (
    P = F#i;
    print ("FACTOR:" | toString P#0 | ":" | toString P#1)
)
"""
        code, stdout, stderr = safe_run_m2_script(factor_script)
        if code != 0:
            raise RuntimeError(f"Macaulay2 factorization failed: {stderr or stdout}")
            
        factors_with_mult = []
        for line in stdout.splitlines():
            sline = line.strip()
            if sline.startswith("FACTOR:"):
                parts = sline[7:].rsplit(":", 1)
                if len(parts) == 2:
                    factors_with_mult.append((parts[0], int(parts[1])))
                    
        sorted_factors_info = []
        for factor_str, mult in factors_with_mult:
            parsed_f = parse_poly_str_unified(factor_str, variables)
            formatted_str = format_poly_general(parsed_f, variables)
            sorted_factors_info.append((formatted_str, factor_str, mult))
            
        sorted_factors_info.sort(key=lambda item: item[0])
        
        ranges = [list(range(info[2] + 1)) for info in sorted_factors_info]
        exps_list = list(itertools.product(*ranges))
        
        # Expand all divisors in M2
        div_script_lines = [f"R = ZZ/{qudit_dim}[{ring_vars}]"]
        for idx, info in enumerate(sorted_factors_info):
            div_script_lines.append(f"p{idx} = ({info[1]})")
            
        for K in exps_list:
            terms = []
            for idx, k in enumerate(K):
                if k > 0:
                    terms.append(f"(p{idx})^{k}")
            if not terms:
                g_expr = "1"
            else:
                g_expr = " * ".join(terms)
            tuple_str = ",".join(str(k) for k in K)
            div_script_lines.append(f'print ("DIVISOR:" | "{tuple_str}:" | toString(({g_expr})))')
            
        code, stdout, stderr = safe_run_m2_script("\n".join(div_script_lines))
        if code != 0:
            raise RuntimeError(f"Macaulay2 divisors expansion failed: {stderr or stdout}")
            
        divisors_map = {}
        for line in stdout.splitlines():
            sline = line.strip()
            if sline.startswith("DIVISOR:"):
                parts = sline[8:].split(":", 1)
                if len(parts) == 2:
                    t_str, poly_str = parts
                    K = tuple(int(x) for x in t_str.split(","))
                    divisors_map[K] = poly_str
                    
        class_to_vectors = {}
        vector_to_class = {}
        vector_to_info = {}
        
        for K in exps_list:
            poly_str = divisors_map[K]
            g_terms = parse_poly_str_unified(poly_str, variables)
            info = classify_divisor(g_terms, qudit_dim, variables)
            c_name = info["mobility_class"]
            
            if c_name not in class_to_vectors:
                class_to_vectors[c_name] = set()
            class_to_vectors[c_name].add(K)
            vector_to_class[K] = c_name
            vector_to_info[K] = info
            
        fusion_classes = [c.strip() for c in poly_g.split('*')]
        for next_class in fusion_classes:
            if next_class not in class_to_vectors:
                raise ValueError(f"Class name '{next_class}' does not exist in class_to_vectors")
                
        curr_vectors = class_to_vectors.get(fusion_classes[0], set())
        for next_class in fusion_classes[1:]:
            next_vectors = class_to_vectors.get(next_class, set())
            curr_vectors = fuse_vector_sets(curr_vectors, next_vectors)
            
        resulting_classes = set()
        for K in curr_vectors:
            resulting_classes.add(vector_to_class[K])
            
        sorted_resulting_classes = sorted(list(resulting_classes))
        
        if len(resulting_classes) == 1:
            max_vector = tuple(max(v[i] for v in curr_vectors) for i in range(len(sorted_factors_info)))
            max_info = vector_to_info[max_vector]
            result = {
                "characteristic_polynomial": max_info["characteristic_polynomial"],
                "lfsr_period": max_info["lfsr_period"],
                "fusion_rules": sorted_resulting_classes
            }
        else:
            result = {
                "fusion_rules": sorted_resulting_classes
            }
            
    else:
        # Single excitation case
        gcd_script = f"""R = ZZ/{qudit_dim}[{ring_vars}]
f = promote(({poly_f}), R)
m = promote(({poly_g}), R)
g_cd = gcd(f, m)
g = f // g_cd
print ("G_RESULT:" | toString g)
"""
        code, stdout, stderr = safe_run_m2_script(gcd_script)
        if code != 0:
            raise RuntimeError(f"Macaulay2 GCD/division failed: {stderr or stdout}")
            
        g_str = ""
        for line in stdout.splitlines():
            sline = line.strip()
            if sline.startswith("G_RESULT:"):
                g_str = sline[9:]
                break
                
        g_terms = parse_poly_str_unified(g_str, variables)
        info = classify_divisor(g_terms, qudit_dim, variables)
        result = {
            "characteristic_polynomial": info["characteristic_polynomial"],
            "lfsr_period": info["lfsr_period"],
            "mobility_class": info["mobility_class"],
            "fusion_rules": [info["mobility_class"]]
        }
        
    utils.save_discovery("hoca_discovery", result)
    utils.log_python_run(
        "mobility_toolkit.fusion",
        "solve_sset_fusion",
        (poly_f, poly_g),
        log_kwargs,
        result,
    )
    return result

def analyze_annihilator_fusion(
    generators: List[str],
    qudit_dim: int,
    variables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    L2 -> L3: Direct computation of mobility fusion rules from annihilator generators.
    """
    from mobility_toolkit.translate import translate_stabilizers, normalize_laurent_poly
    
    # We can create a dummy stabilizer matrix to reuse translate_stabilizers variable mapping
    dummy_matrix = [[g] for g in generators]
    # This synthetic one-row matrix is only a convenient way to reuse Laurent
    # variable/ring translation.  It is not a physical Pauli stabilizer map.
    translation = translate_stabilizers(
        dummy_matrix,
        qudit_dim,
        validate_stabilizer=False,
    )
    ring_def = translation["ring_definition"]
    detected_vars = translation["variables"]
    
    is_principal, gen = check_ideal_principal(ring_def, generators)
    if not is_principal:
        raise ValueError("Annihilator ideal is not principal; SSET mobility fusion rules are only defined for principal annihilator ideals.")
        
    normalized_gen = normalize_laurent_poly(gen)
    
    result = solve_sset_fusion(
        normalized_gen,
        "1",
        qudit_dim=qudit_dim,
        variables=detected_vars,
    )
    return {
        "is_principal": True,
        "normalized_generator": normalized_gen,
        "mobility_class": result["mobility_class"],
        "characteristic_polynomial": result["characteristic_polynomial"],
        "lfsr_period": result["lfsr_period"],
        "fusion_rules": result["fusion_rules"]
    }
