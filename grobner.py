import math
import re
from itertools import product
from typing import List, Dict, Any
from mobility_toolkit.bridge import run_m2_script, validate_input_string
from mobility_toolkit import utils
from mobility_toolkit.utils import verify_qudit_dim

def parse_leading_term(lt_str: str) -> tuple:
    """Parses a leading term string from Macaulay2 into (coefficient, exponents).
    Exponents is a dict mapping 'u', 't', 'y', 'x' to their integer powers.
    """
    lt_str = lt_str.strip().replace(" ", "")
    if not lt_str:
        return 0, {"u": 0, "t": 0, "y": 0, "x": 0}
    
    if lt_str.startswith("-"):
        sign = -1
        lt_str = lt_str[1:]
    elif lt_str.startswith("+"):
        sign = 1
        lt_str = lt_str[1:]
    else:
        sign = 1
        
    if lt_str.isdigit():
        return sign * int(lt_str), {"u": 0, "t": 0, "y": 0, "x": 0}
        
    exponents = {"u": 0, "t": 0, "y": 0, "x": 0}
    
    if "*" in lt_str:
        parts = lt_str.split("*")
        first_part = parts[0]
        if first_part.isdigit():
            coef = int(first_part)
            var_parts = parts[1:]
        else:
            coef = 1
            var_parts = parts
        
        for part in var_parts:
            _parse_var_part(part, exponents)
    else:
        coef = 1
        _parse_var_part(lt_str, exponents)
        
    return sign * coef, exponents

def _parse_var_part(part: str, exponents: dict):
    if "^" in part:
        var_name, power_str = part.split("^")
        if var_name in exponents:
            exponents[var_name] = int(power_str)
    else:
        if part in exponents:
            exponents[part] = 1

def count_quotient_size(parsed_gb: List[tuple], qudit_dim: int, is_gsd: bool = False) -> int:
    bounds = {}
    for v in ["u", "t", "y", "x"]:
        v_bounds = []
        for coef, exponents in parsed_gb:
            if coef == 1 and exponents[v] >= 1:
                # Check if all other variables have power 0
                if all(exponents[other] == 0 for other in ["u", "t", "y", "x"] if other != v):
                    v_bounds.append(exponents[v])
        if not v_bounds:
            if not is_gsd:
                raise ValueError("Quotient ring is infinite.")
            else:
                raise ValueError("GSD quotient ring is infinite.")
        bounds[v] = min(v_bounds)
        
    k_u = bounds["u"]
    k_t = bounds["t"]
    k_y = bounds["y"]
    k_x = bounds["x"]
    
    basis_monomials = []
    for a, b, c, d in product(range(k_u), range(k_t), range(k_y), range(k_x)):
        divisible = False
        for coef, exponents in parsed_gb:
            if coef == 1:
                ea = exponents.get("u", 0)
                eb = exponents.get("t", 0)
                ec = exponents.get("y", 0)
                ed = exponents.get("x", 0)
                if a >= ea and b >= eb and c >= ec and d >= ed:
                    divisible = True
                    break
        if not divisible:
            basis_monomials.append((a, b, c, d))
            
    quotient_size = 1
    for a, b, c, d in basis_monomials:
        dividing_coefs = []
        for coef, exponents in parsed_gb:
            ea = exponents.get("u", 0)
            eb = exponents.get("t", 0)
            ec = exponents.get("y", 0)
            ed = exponents.get("x", 0)
            if a >= ea and b >= eb and c >= ec and d >= ed:
                dividing_coefs.append(coef)
        
        curr_gcd = qudit_dim
        for val in dividing_coefs:
            curr_gcd = math.gcd(curr_gcd, val)
        quotient_size *= curr_gcd
        
    return quotient_size

def compute_fusion_rules_str(qudit_dim: int, quotient_size: int) -> str:
    if quotient_size <= 1:
        return "0"
        
    factors = {}
    temp = qudit_dim
    d = 2
    while d * d <= temp:
        if temp % d == 0:
            count = 0
            while temp % d == 0:
                count += 1
                temp //= d
            factors[d] = count
        d += 1
    if temp > 1:
        factors[temp] = 1
        
    if not factors:
        return "0"
        
    parts = []
    for p in sorted(factors.keys()):
        k_i = factors[p]
        j_i = 0
        q_temp = quotient_size
        while q_temp % p == 0:
            j_i += 1
            q_temp //= p
            
        if j_i > 0:
            power_val = p ** k_i
            exponent_val = (2 * j_i) // k_i
            parts.append(f"Z_{power_val}^{exponent_val}")
            
    if not parts:
        return "0"
    return " + ".join(parts)

def compute_gsd_and_periodicity(stabilizer_matrix: List[List[str]], Lx: int, Ly: int, qudit_dim: int) -> Dict[str, Any]:
    """Computes GSD and anyon periodicities on a torus Lx x Ly via Gröbner bases over Z in M2.

    Args:
        stabilizer_matrix (List[List[str]]): Stabilizer generator matrix.
        Lx (int): Torus size Lx.
        Ly (int): Torus size Ly.
        qudit_dim (int): Qudit dimension N.

    Returns:
        Dict[str, Any]: Calculated GSD and periodicities.
    """
    # Log run at start
    utils.log_python_run("mobility_toolkit.grobner", "compute_gsd_and_periodicity", (stabilizer_matrix, Lx, Ly, qudit_dim), {}, "PENDING")

    # 1. Input Validation
    if not isinstance(stabilizer_matrix, list) or len(stabilizer_matrix) == 0:
        raise ValueError("stabilizer_matrix must be a non-empty list.")
    
    first_row_len = -1
    for i, row in enumerate(stabilizer_matrix):
        if not isinstance(row, list):
            raise ValueError(f"stabilizer_matrix[{i}] is not a list.")
        if len(row) == 0:
            raise ValueError(f"stabilizer_matrix[{i}] is empty.")
        if first_row_len == -1:
            first_row_len = len(row)
        elif len(row) != first_row_len:
            raise ValueError("All rows in stabilizer_matrix must have the same length.")
        for j, val in enumerate(row):
            if not isinstance(val, str):
                raise ValueError(f"stabilizer_matrix[{i}][{j}] is not a string.")
            
            # Sanitization call
            validate_input_string(val)
            
            if not re.match(r'^[a-zA-Z0-9_\s\+\-\*\^]*$', val):
                raise ValueError(f"Invalid characters in stabilizer matrix: {val}")
            vars_found = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', val)
            for var in vars_found:
                if var not in {'u', 't', 'y', 'x'}:
                    raise ValueError(f"Invalid variable '{var}' in stabilizer matrix. Allowed variables are u, t, y, x.")

    if not isinstance(Lx, int) or isinstance(Lx, bool) or Lx <= 0:
        raise ValueError("Lx must be a positive integer.")
    if not isinstance(Ly, int) or isinstance(Ly, bool) or Ly <= 0:
        raise ValueError("Ly must be a positive integer.")
        
    if Lx > 100000 or Ly > 100000:
        raise ValueError("Torus dimensions Lx or Ly exceed the limit of 100000.")

    # Call verify_qudit_dim with prime_bypass=True
    verify_qudit_dim(qudit_dim, prime_bypass=True)

    # 2. Construct Macaulay2 Script
    clean_entries = []
    has_x = False
    has_y = False
    for row in stabilizer_matrix:
        for entry in row:
            clean = entry.strip().replace("**", "^")
            if clean != "0":
                clean_entries.append(clean)
                if "x" in clean or "t" in clean:
                    has_x = True
                if "y" in clean or "u" in clean:
                    has_y = True
                    
    generators = [f"({qudit_dim})", "x*t - 1", "y*u - 1"]
    if not has_x:
        generators.extend(["x - 1", "t - 1"])
    if not has_y:
        generators.extend(["y - 1", "u - 1"])
    generators.extend(clean_entries)
    m2_ideal_str = ", ".join(generators)
    
    m2_script = f"""S = ZZ[u, t, y, x, MonomialOrder => Lex]
I = ideal({m2_ideal_str})
IGSD = I + ideal(x^{Lx} - 1, y^{Ly} - 1)
print "VALUE:START_GB"
G = gens gb I
L = flatten entries G
for felem in L do (print ("VALUE:" | toString felem); print ("VALUE:" | toString leadTerm felem))
print "VALUE:START_PER"
i = 1
while i < 100000 do (if (x^i - 1) % I == 0 then (break); i = i + 1)
print ("VALUE:" | toString i)
j = 1
while j < 100000 do (if (y^j - 1) % I == 0 then (break); j = j + 1)
print ("VALUE:" | toString j)
print "VALUE:START_GSD"
GGSD = gens gb IGSD
LGSDflat = flatten entries GGSD
for felem in LGSDflat do (print ("VALUE:" | toString felem); print ("VALUE:" | toString leadTerm felem))
"""

    # 3. Run Macaulay2 Script
    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        raise RuntimeError(f"Macaulay2 script failed with exit code {code}. Stderr: {stderr}. Stdout: {stdout}")

    # 4. Parse stdout
    clean_lines = []
    for line in stdout.splitlines():
        sline = line.strip()
        if sline.startswith("VALUE:"):
            clean_lines.append(sline[len("VALUE:"):])

    try:
        idx_gb = clean_lines.index("START_GB")
        idx_per = clean_lines.index("START_PER")
        idx_gsd = clean_lines.index("START_GSD")
    except ValueError as e:
        raise RuntimeError(f"Failed to find expected markers in Macaulay2 output: {e}. Clean lines: {clean_lines}")

    gb_lines = clean_lines[idx_gb + 1 : idx_per]
    per_lines = clean_lines[idx_per + 1 : idx_gsd]
    gsd_lines = clean_lines[idx_gsd + 1 :]

    if len(per_lines) < 2:
        raise RuntimeError(f"Expected at least 2 lines for periodicities, got: {per_lines}")
    try:
        l_x = int(per_lines[0].strip())
        l_y = int(per_lines[1].strip())
    except ValueError as e:
        raise RuntimeError(f"Failed to parse periodicities as integers: {per_lines}. Error: {e}")

    if len(gb_lines) % 2 != 0:
        raise RuntimeError(f"Expected even number of lines for GB, got {len(gb_lines)}")
    
    parsed_gb = []
    for idx in range(0, len(gb_lines), 2):
        gen = gb_lines[idx]
        lt = gb_lines[idx+1]
        coef, exponents = parse_leading_term(lt)
        parsed_gb.append((coef, exponents))

    if len(gsd_lines) % 2 != 0:
        raise RuntimeError(f"Expected even number of lines for GSD GB, got {len(gsd_lines)}")
    
    parsed_gsd = []
    for idx in range(0, len(gsd_lines), 2):
        gen = gsd_lines[idx]
        lt = gsd_lines[idx+1]
        coef, exponents = parse_leading_term(lt)
        parsed_gsd.append((coef, exponents))

    # 5. Finiteness check and quotient sizing
    try:
        quotient_size = count_quotient_size(parsed_gb, qudit_dim, is_gsd=False)
        # 6. Compute fusion rules
        fusion_rules = compute_fusion_rules_str(qudit_dim, quotient_size)
    except ValueError as e:
        if str(e) == "Quotient ring is infinite.":
            quotient_size = float('inf')
            fusion_rules = "infinite"
        else:
            raise

    gsd_quotient_size = count_quotient_size(parsed_gsd, qudit_dim, is_gsd=True)

    # 7. GSD calculation
    gsd = gsd_quotient_size ** 2

    result = {
        "gsd": gsd,
        "periodicities": {
            "l_x": l_x,
            "l_y": l_y
        },
        "fusion_rules": fusion_rules
    }
    
    utils.save_discovery("grobner_discovery", result)
    utils.log_python_run("mobility_toolkit.grobner", "compute_gsd_and_periodicity", (stabilizer_matrix, Lx, Ly, qudit_dim), {}, result)
    
    return result
