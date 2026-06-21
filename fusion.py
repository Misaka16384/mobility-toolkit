import re
import math
import itertools
from typing import List, Dict, Any
from fractions import Fraction
from mobility_toolkit.bridge import run_m2_script, run_macaulay2
from mobility_toolkit.translate import translate_to_algebra
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
    
    if code != 0:
        normalized_stderr = stderr_clean.lower()
        normalized_stdout = stdout_clean.lower()
        if "error" in normalized_stderr or "error:" in normalized_stdout or "syntax error" in normalized_stdout:
            pass
        else:
            code = 0
    return code, stdout_clean, stderr_clean

def safe_run_macaulay2(script: str, timeout: int = 30):
    res = run_macaulay2(script, timeout)
    stdout_clean = clean_wsl_garbage(res["stdout"])
    stderr_clean = clean_wsl_garbage(res["stderr"])
    exit_code = res["exit_code"]
    
    if exit_code != 0 and exit_code not in (124, 127):
        normalized_stderr = stderr_clean.lower()
        normalized_stdout = stdout_clean.lower()
        if "error" in normalized_stderr or "error:" in normalized_stdout or "syntax error" in normalized_stdout:
            pass
        else:
            exit_code = 0
    return {
        "exit_code": exit_code,
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
        curr = curr.multiply(curr).rem(mod)
        exp //= 2
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

def parse_term(term_str: str) -> tuple[int, int]:
    term_str = term_str.strip()
    if term_str == "1":
        return (0, 0)
    if term_str == "0" or not term_str:
        return None
    
    match_x = re.search(r'\bx\^(\d+)\b', term_str)
    if match_x:
        exp_x = int(match_x.group(1))
    elif re.search(r'\bx\b', term_str):
        exp_x = 1
    else:
        exp_x = 0
        
    match_y = re.search(r'\by\^(\d+)\b', term_str)
    if match_y:
        exp_y = int(match_y.group(1))
    elif re.search(r'\by\b', term_str):
        exp_y = 1
    else:
        exp_y = 0
        
    return (exp_x, exp_y)

def parse_poly_str(poly_str: str) -> set[tuple[int, int]]:
    poly_str = poly_str.replace(" ", "").replace("\n", "").replace("\r", "")
    if poly_str == "0" or not poly_str:
        return set()
    terms = set()
    for term_str in poly_str.split("+"):
        parsed = parse_term(term_str)
        if parsed is not None:
            terms.add(parsed)
    return terms

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

def construct_monomial(shift: List[int]) -> str:
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

def classify_divisor(g_terms: set[tuple[int, int]]) -> Dict[str, Any]:
    g_terms = shift_poly(g_terms)
    
    if len(g_terms) == 1 and (0, 0) in g_terms:
        return {
            "mobility_class": "alpha",
            "lfsr_period": 1,
            "characteristic_polynomial": "1"
        }
        
    nonzero_exps = [t for t in g_terms if t != (0, 0)]
    if not nonzero_exps:
        return {
            "mobility_class": "alpha",
            "lfsr_period": 1,
            "characteristic_polynomial": "1"
        }
        
    collinear = True
    first_monomial = nonzero_exps[0]
    u0, v0 = first_monomial
    d0 = math.gcd(u0, v0)
    p_u, p_v = u0 // d0, v0 // d0
    
    for monomial in nonzero_exps[1:]:
        u, v = monomial
        d = math.gcd(u, v)
        if u // d != p_u or v // d != p_v:
            collinear = False
            break
            
    if not collinear:
        return {
            "mobility_class": "gamma",
            "lfsr_period": None,
            "characteristic_polynomial": format_poly(g_terms)
        }
        
    t_terms = []
    for tx, ty in g_terms:
        if p_u > 0:
            k = tx // p_u
        else:
            k = ty // p_v
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
    
    m2_script = f"""R = ZZ/2[q]
t_poly = promote(({t_expr}), R)
F = factor t_poly
for i from 0 to #F-1 do (
    P = F#i;
    print ("UFACTOR:" | toString P#0 | ":" | toString P#1)
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
        parts = f_line.rsplit(":", 1)
        if len(parts) == 2:
            factor_str, mult_str = parts
            mult = int(mult_str)
            mod_poly = parse_gf2_poly(factor_str)
            d = mod_poly.degree
            if d > 30:
                raise ValueError(f"Irreducible factor degree {d} is greater than 30")
            M = (1 << d) - 1
            divs = get_divisors(M)
            order = None
            for k_div in divs:
                if gf2_poly_powmod(GF2Poly(2), k_div, mod_poly) == GF2Poly(1):
                    order = k_div
                    break
            if order is None:
                order = M
            scaled_period = order * (2 ** math.ceil(math.log2(mult)))
            periods.append(scaled_period)
            
    total_period = 1
    for p_val in periods:
        total_period = (total_period * p_val) // math.gcd(total_period, p_val)
        
    dir_str = format_direction(p_u, p_v)
    return {
        "mobility_class": f"beta_{{{dir_str}, {total_period}}}",
        "lfsr_period": total_period,
        "characteristic_polynomial": format_poly(g_terms)
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
    translation = translate_to_algebra(stabilizer_matrix, qudit_dim)
    ring_def = translation["ring_definition"]
    matrix_def = translation["matrix_definition"]
    variables = translation["variables"]

    # 2. Determine saturation product (product of active positive variables)
    active_pos_vars = [v for v in variables if v in {'x', 'y', 'z'}]
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
        monomial = construct_monomial(shift)
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
        "dimension_drop": dimension_drop
    }
    
    utils.save_discovery("fusion_interference_discovery", result)
    utils.log_python_run("mobility_toolkit.fusion", "analyze_fusion_interference", (stabilizer_matrix, qudit_dim, shifts), {}, result)
    
    return result

def solve_sset_fusion(poly_f: str, poly_g: str) -> Dict[str, Any]:
    """Solves SSET characteristic polynomial, LFSR periodicities, and fusion rules.

    Args:
        poly_f (str): First polynomial.
        poly_g (str): Second polynomial.

    Returns:
        Dict[str, Any]: SSET fusion properties and characteristic polynomials.
    """
    utils.log_python_run("mobility_toolkit.fusion", "solve_sset_fusion", (poly_f, poly_g), {}, "PENDING")
    
    class_fusion_mode = any(cls in poly_g for cls in ["beta_", "alpha", "gamma"])
    
    if not class_fusion_mode:
        validate_variables_only_x_y(poly_f)
        validate_variables_only_x_y(poly_g)
        
    # Check for zero polynomials and separability in M2
    script_lines = [
        "R = ZZ/2[x, y]",
        f"f = promote(({poly_f}), R)",
        "fx = sub(f, {y => 0})",
        "fy = sub(f, {x => 0})",
        "isSeparable = (f == fx * fy)",
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
        factor_script = f"""R = ZZ/2[x, y]
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
            parsed_f = parse_poly_str(factor_str)
            formatted_str = format_poly(parsed_f)
            sorted_factors_info.append((formatted_str, factor_str, mult))
            
        sorted_factors_info.sort(key=lambda item: item[0])
        
        ranges = [list(range(info[2] + 1)) for info in sorted_factors_info]
        exps_list = list(itertools.product(*ranges))
        
        # Expand all divisors in M2
        div_script_lines = ["R = ZZ/2[x, y]"]
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
            g_terms = parse_poly_str(poly_str)
            info = classify_divisor(g_terms)
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
        gcd_script = f"""R = ZZ/2[x, y]
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
                    
        g_terms = parse_poly_str(g_str)
        info = classify_divisor(g_terms)
        result = {
            "characteristic_polynomial": info["characteristic_polynomial"],
            "lfsr_period": info["lfsr_period"],
            "mobility_class": info["mobility_class"],
            "fusion_rules": [info["mobility_class"]]
        }
        
    utils.save_discovery("hoca_discovery", result)
    utils.log_python_run("mobility_toolkit.fusion", "solve_sset_fusion", (poly_f, poly_g), {}, result)
    return result
