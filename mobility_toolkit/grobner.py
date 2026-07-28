import math
import re
from itertools import product
from typing import List, Dict, Any
from mobility_toolkit.bridge import run_m2_script, validate_input_string
from mobility_toolkit import utils
from mobility_toolkit.utils import verify_modulus

def get_prime_factors(n: int) -> List[int]:
    factors = []
    d = 2
    temp = n
    while d * d <= temp:
        if temp % d == 0:
            factors.append(d)
            while temp % d == 0:
                temp //= d
        d += 1
    if temp > 1:
        factors.append(temp)
    return factors

def get_prime_factors_with_exponents(n: int) -> Dict[int, int]:
    factors = {}
    d = 2
    temp = n
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
    return factors

def check_in_ideal(xi: str, K: int, p_pow: int, m2_ideal_str: str, vars_list: List[str]) -> bool:
    script = f"""S = ZZ[{', '.join(vars_list)}, MonomialOrder => Lex]
I = ideal({m2_ideal_str}) + ideal({p_pow})
print (({xi}^{K} - 1) % I == 0)
"""
    code, stdout, stderr = run_m2_script(script)
    if code == 0 and "true" in stdout:
        return True
    return False

def get_divisors(m: int) -> List[int]:
    divs = []
    for i in range(1, int(math.isqrt(m)) + 1):
        if m % i == 0:
            divs.append(i)
            if i * i != m:
                divs.append(m // i)
    return sorted(divs)

def ceil_log_N(mf: int, N: int) -> int:
    p = 0
    val = 1
    while val < mf:
        val *= N
        p += 1
    return p

def poly_mul(p1: List[int], p2: List[int], N: int) -> List[int]:
    if not p1 or not p2:
        return []
    res = [0] * (len(p1) + len(p2) - 1)
    for i, c1 in enumerate(p1):
        if c1 == 0:
            continue
        for j, c2 in enumerate(p2):
            res[i + j] += c1 * c2
    # ⚡ Bolt: Defer modulo operation to the end to save time in inner loop.
    res = [x % N for x in res]
    while len(res) > 0 and res[-1] == 0:
        res.pop()
    return res

def poly_divmod(num: List[int], den: List[int], N: int) -> tuple[List[int], List[int]]:
    while len(den) > 0 and den[-1] == 0:
        den = den[:-1]
    if not den:
        raise ZeroDivisionError("Polynomial division by zero")
    num = list(num)
    while len(num) > 0 and num[-1] == 0:
        num = num[:-1]
    deg_d = len(den) - 1
    lead_d = den[-1]
    lead_d_inv = 1 if lead_d == 1 else pow(lead_d, N - 2, N)
    quot = [0] * max(0, len(num) - len(den) + 1)

    while len(num) >= len(den):
        deg_n = len(num) - 1
        lead_n = num[-1] % N
        shift = deg_n - deg_d
        coeff = (lead_n * lead_d_inv) % N
        quot[shift] = coeff
        if coeff != 0:
            for i in range(len(den)):
                num[shift + i] -= coeff * den[i]
        num.pop() # The last element is going to be 0 anyway mod N
        while len(num) > 0 and num[-1] % N == 0:
            num.pop()

    num = [x % N for x in num]
    while len(num) > 0 and num[-1] == 0:
        num.pop()
    return quot, num

def poly_powmod(base: List[int], exp: int, mod: List[int], N: int) -> List[int]:
    res = [1]
    curr = list(base)
    while exp > 0:
        if exp % 2 == 1:
            prod = poly_mul(res, curr, N)
            _, res = poly_divmod(prod, mod, N)
        exp //= 2
        # ⚡ Bolt: Skip unnecessary multiply/divmod on final exponentiation step.
        if exp > 0:
            prod = poly_mul(curr, curr, N)
            _, curr = poly_divmod(prod, mod, N)
    return res

def extract_generators(gb_str: str) -> List[str]:
    m = re.search(r'matrix\s*\{\s*\{(.*)\}\s*\}', gb_str, re.DOTALL)
    if not m:
        return []
    content = m.group(1).strip()
    if not content or content == "0":
        return []
    return [p.strip() for p in content.split(",") if p.strip()]

def compute_periodicity_of_var(p_expr: Any, xi: str, qudit_dim: int, m2_ideal_str: str = None, vars_list: List[str] = None) -> int:
    if not p_expr or p_expr == "0":
        return 0
        
    if isinstance(p_expr, str):
        gens_clean = [p_expr] if xi in p_expr else []
    else:
        gens_clean = [g for g in p_expr if xi in g]
        
    if not gens_clean:
        return 0
        
    p_factors_exps = get_prime_factors_with_exponents(qudit_dim)
    p_periodicities = []
    
    for p, a in p_factors_exps.items():
        # 1. Compute periodicity modulo p using Macaulay2 factoring of the univariate GB generator
        factor_script = f"""myF = local myF;
myL = local myL;
myP = local myP;
mydeg = local mydeg;
myidx = local myidx;
myk = local myk;
R = ZZ/{p}[{xi}]
I = ideal({', '.join(gens_clean)})
G = generators gb I
Gflat = flatten entries G
g = if length Gflat > 0 then Gflat#0 else 0_R
print ("GEN_STR:" | toString g)
if g != 0 then (
    myF = factor g;
    myL = toList myF;
    print ("FACTOR_COUNT:" | toString length myL);
    for myidx from 0 to (length myL) - 1 do (
        myP = myL#myidx;
        if toString class myP == "Power" then (
            mydeg = (degree myP#0)#0;
            print ("FACTOR_INFO:" | toString myidx | ":" | toString myP#1 | ":" | toString mydeg);
            for myk from 0 to mydeg do (
                print ("COEF_INFO:" | toString myidx | ":" | toString myk | ":" | toString coefficient({xi}^myk, myP#0));
            )
        ) else (
            mydeg = (degree myP)#0;
            print ("FACTOR_INFO:" | toString myidx | ":1:" | toString mydeg);
            for myk from 0 to mydeg do (
                print ("COEF_INFO:" | toString myidx | ":" | toString myk | ":" | toString coefficient({xi}^myk, myP));
            )
        )
    )
)
"""
        code, stdout, stderr = run_m2_script(factor_script)
        if code != 0:
            raise RuntimeError(f"Macaulay2 factoring script failed: {stderr or stdout}")
            
        lines = [line.strip() for line in stdout.splitlines()]
        
        # Parse GEN_STR
        gen_str = ""
        for line in lines:
            if line.startswith("GEN_STR:"):
                gen_str = line[len("GEN_STR:"):].strip()
                break
                
        if gen_str == "0":
            p_periodicities.append(0)
            continue
        if xi not in gen_str:
            p_periodicities.append(1)
            continue
            
        factors_data = {}
        for line in lines:
            if line.startswith("FACTOR_INFO:"):
                parts = line.split(":")
                if len(parts) == 4:
                    idx = int(parts[1])
                    mult = int(parts[2])
                    deg = int(parts[3])
                    factors_data[idx] = {
                        "mult": mult,
                        "deg": deg,
                        "coefs": {}
                    }
            elif line.startswith("COEF_INFO:"):
                parts = line.split(":")
                if len(parts) == 4:
                    idx = int(parts[1])
                    k = int(parts[2])
                    val = int(parts[3])
                    if idx in factors_data:
                        factors_data[idx]["coefs"][k] = val
                        
        factor_orders = []
        for idx, data in factors_data.items():
            deg = data["deg"]
            if deg < 0:
                # The factor is 0, meaning periodicity is infinite (0)
                factor_orders.append(0)
                continue
            if deg == 0:
                # Constant factor (unit), skip
                continue
            f_coefs = [0] * (deg + 1)
            for k, val in data["coefs"].items():
                f_coefs[k] = val % p
            
            M = (p ** deg) - 1
            divs = get_divisors(M)
            
            order = None
            for divisor in divs:
                rem = poly_powmod([0, 1], divisor, f_coefs, p)
                if rem == [1]:
                    order = divisor
                    break
            
            if order is None:
                order = M
                
            p_log = ceil_log_N(data["mult"], p)
            P_f = order * (p ** p_log)
            factor_orders.append(P_f)
            
        if factor_orders:
            # Bolt: Replaced manual list loop with C-optimized math.lcm
            lcm_p = math.lcm(*factor_orders)
            
            # 2. Lift to p^a if a > 1 and m2_ideal_str is provided
            if lcm_p > 0 and a > 1 and m2_ideal_str and vars_list:
                K = lcm_p
                for _ in range(a - 1):
                    # Check if current K is a valid period mod I mod p^a
                    if check_in_ideal(xi, K, p ** a, m2_ideal_str, vars_list):
                        break
                    K = K * p
                lcm_p = K
                
            p_periodicities.append(lcm_p)
        else:
            p_periodicities.append(1)
            
    # Bolt: Replaced manual list loop with C-optimized math.lcm
    total_periodicity = math.lcm(*p_periodicities) if p_periodicities else 1
        
    return total_periodicity

def parse_leading_term(lt_str: str, vars_list: List[str]) -> tuple:
    lt_str = lt_str.strip().replace(" ", "")
    if not lt_str:
        return 0, {v: 0 for v in vars_list}
    
    if lt_str.startswith("-"):
        sign = -1
        lt_str = lt_str[1:]
    elif lt_str.startswith("+"):
        sign = 1
        lt_str = lt_str[1:]
    else:
        sign = 1
        
    if lt_str.isdigit():
        return sign * int(lt_str), {v: 0 for v in vars_list}
        
    exponents = {v: 0 for v in vars_list}
    
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

def count_quotient_size(parsed_gb: List[tuple], vars_list: List[str], qudit_dim: int, is_gsd: bool = False) -> int:
    bounds = {}
    for v in vars_list:
        v_bounds = []
        for coef, exponents in parsed_gb:
            if coef == 1 and exponents[v] >= 1:
                if all(exponents[other] == 0 for other in vars_list if other != v):
                    v_bounds.append(exponents[v])
        if not v_bounds:
            raise ValueError("GSD quotient ring is infinite." if is_gsd else "Quotient ring is infinite.")
        bounds[v] = min(v_bounds)
        
    num_vars = len(vars_list)
    monic_gens = []
    non_monic_gens = []

    # Pre-process generators into tuples and filter out inactive ones
    for coef, exponents in parsed_gb:
        exp_tuple = tuple(exponents[v] for v in vars_list)
        # ⚡ Bolt: If any generator exponent exceeds the variable's upper bound, it can never divide any basis monomial
        if any(exp_tuple[i] >= bounds[vars_list[i]] for i in range(num_vars)):
            continue
        if coef == 1:
            monic_gens.append(exp_tuple)
        else:
            non_monic_gens.append((coef, exp_tuple))

    # Fast path: No active generators below the bounds (rare but perfectly valid)
    if not monic_gens and not non_monic_gens:
        basis_count = 1
        for v in vars_list:
            basis_count *= bounds[v]
        return qudit_dim ** basis_count

    ranges = [range(bounds[v]) for v in vars_list]

    # ⚡ Bolt: Fast path for simple monomial ideals without coefficient interference
    if not non_monic_gens:
        basis_count = 0
        for combo in product(*ranges):
            # Inline for loop is faster than all() generator overhead in Python
            for mg in monic_gens:
                for i in range(num_vars):
                    if combo[i] < mg[i]:
                        break
                else:
                    break
            else:
                basis_count += 1
        return qudit_dim ** basis_count

    quotient_size = 1
    for combo in product(*ranges):
        for mg in monic_gens:
            for i in range(num_vars):
                if combo[i] < mg[i]:
                    break
            else:
                break
        else:
            dividing_coefs = []
            for coef, nmg in non_monic_gens:
                for i in range(num_vars):
                    if combo[i] < nmg[i]:
                        break
                else:
                    dividing_coefs.append(coef)
            # Bolt: Replaced manual gcd loop with C-optimized math.gcd
            quotient_size *= math.gcd(qudit_dim, *dividing_coefs)
            
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

def compute_gsd_and_periodicity(stabilizer_matrix: List[List[str]], Lx: Any = None, Ly: Any = None, qudit_dim: int = None, L: List[int] = None) -> Dict[str, Any]:
    # Resolve arguments
    if L is not None:
        if qudit_dim is None:
            raise ValueError("qudit_dim must be specified.")
    elif isinstance(Lx, list):
        L = Lx
        qudit_dim = Ly
    else:
        if Lx is None or Ly is None:
            raise ValueError("Must specify either L or both Lx and Ly.")
        L = [Lx, Ly]

    # Log run at start
    utils.log_python_run("mobility_toolkit.grobner", "compute_gsd_and_periodicity", (stabilizer_matrix, Lx, Ly, qudit_dim), {"L": L}, "PENDING")

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
            
            if not re.match(r'^[a-zA-Z0-9_\s\+\-\*\^\(\)]*$', val):
                raise ValueError(f"Invalid characters in stabilizer matrix: {val}")

    if not isinstance(L, list) or len(L) == 0:
        raise ValueError("L must be a non-empty list of integers.")
    for val in L:
        if not isinstance(val, int) or isinstance(val, bool) or val <= 0:
            raise ValueError("Torus sizes must be positive integers.")
        if val > 100000:
            raise ValueError("Torus dimensions exceed the limit of 100000.")

    # GSD arithmetic is defined for arbitrary cyclic modulus, including
    # composite local dimension.
    verify_modulus(qudit_dim)

    # 2. Map legacy variables to unified variables
    from mobility_toolkit.translate import map_variables_to_unified
    translated_matrix = []
    for row in stabilizer_matrix:
        translated_row = []
        for entry in row:
            translated_row.append(map_variables_to_unified(entry))
        translated_matrix.append(translated_row)

    # Find highest variable index
    d_model = 0
    for row in translated_matrix:
        for elem in row:
            for m in re.finditer(r'\b[xt](\d+)\b', elem):
                d_model = max(d_model, int(m.group(1)))

    if d_model > len(L):
        raise ValueError(f"Model dimension ({d_model}) exceeds torus dimension ({len(L)}).")
    d = max(d_model, len(L))

    # Identify active dimensions in the model
    active_dims = set()
    for row in translated_matrix:
        for elem in row:
            for m in re.finditer(r'\b[xt](\d+)\b', elem):
                active_dims.add(int(m.group(1)))

    # Construct Macaulay2 Ideal
    clean_entries = []
    for row in translated_matrix:
        for entry in row:
            if entry.strip() != "0":
                clean_entries.append(entry.strip())
                
    generators = [f"({qudit_dim})"]
    for i in range(1, d + 1):
        generators.append(f"x{i}*t{i} - 1")
        if i not in active_dims and i > len(L):
            generators.extend([f"x{i} - 1", f"t{i} - 1"])
    generators.extend(clean_entries)
    m2_ideal_str = ", ".join(generators)

    # Order variables in Lex order: t1, ..., td, x1, ..., xd
    vars_list = [f"t{i}" for i in range(1, d + 1)] + [f"x{i}" for i in range(1, d + 1)]

    # Construct Macaulay2 Script
    m2_script_parts = [
        f"S = ZZ[{', '.join(vars_list)}, MonomialOrder => Lex]",
        f"I = ideal({m2_ideal_str})",
    ]
    # Transpose matrix for M2 representation
    num_rows = len(translated_matrix)
    num_cols = len(translated_matrix[0])
    transposed = [[translated_matrix[r][c] for r in range(num_rows)] for c in range(num_cols)]
    m2_matrix_rows = []
    for r in transposed:
        m2_matrix_rows.append("{" + ", ".join(r) + "}")
    matrix_definition = "{" + ", ".join(m2_matrix_rows) + "}"

    # Symbolic cokernel size computation in Macaulay2 for each prime factor
    factors_dict = get_prime_factors_with_exponents(qudit_dim)
    for p, a in factors_dict.items():
        ring_generators = [f"({p**a})"]
        for j in range(1, d + 1):
            ring_generators.append(f"x{j}*t{j} - 1")
            if j not in active_dims and j > len(L):
                ring_generators.extend([f"x{j} - 1", f"t{j} - 1"])
            if j <= len(L):
                ring_generators.append(f"x{j}^{L[j-1]} - 1")
        ring_ideal_str = ", ".join(ring_generators)
        m2_script_parts.append("use S")
        m2_script_parts.append(f"IRT{p} = ideal({ring_ideal_str})")
        m2_script_parts.append(f"R{p} = S / IRT{p}")
        m2_script_parts.append(f"use R{p}")
        m2_script_parts.append(f"M{p} = matrix(R{p}, {matrix_definition})")
        m2_script_parts.append(f"C{p} = coker M{p}")
        for j in range(a + 1):
            val = p ** j
            m2_script_parts.append(f"Csub{p}{j+1} = image ({val} * id_(C{p}))")
        for j in range(a):
            m2_script_parts.append(f"V{p}{j+1} = Csub{p}{j+1} / Csub{p}{j+2}")
            m2_script_parts.append(f"print (\"VALUE:COKER_DIM:{p}:{j}:\" | toString (numgens (source (basis V{p}{j+1}))))")

    m2_script_parts.append("use S")

    # GB for original ideal (to compute quotient size)
    m2_script_parts.append('print "VALUE:START_GB"')
    m2_script_parts.append("G = gens gb I")
    m2_script_parts.append("Lflat = flatten entries G")
    m2_script_parts.append('for felem in Lflat do (print ("VALUE:" | toString felem); print ("VALUE:" | toString leadTerm felem))')

    # Elimination for each dimension
    for i in range(1, d + 1):
        elim_vars = [v for v in vars_list if v != f"x{i}"]
        m2_script_parts.append(f"Ielim{i} = eliminate({{{', '.join(elim_vars)}}}, I)")
        m2_script_parts.append(f'print "VALUE:PER_GEN_{i}"')
        m2_script_parts.append(f"print toString (generators gb Ielim{i})")

    m2_script = "\n".join(m2_script_parts)

    # 3. Run Macaulay2 Script
    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        raise RuntimeError(f"Macaulay2 script failed with exit code {code}. Stderr: {stderr}. Stdout: {stdout}")

    # 4. Parse stdout
    lines = [line.strip() for line in stdout.splitlines()]

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

    # Parse the fusion-group GB
    try:
        idx_gb = lines.index("VALUE:START_GB")
    except ValueError as e:
        raise RuntimeError(f"Failed to find expected markers in Macaulay2 output: {e}. Output: {stdout}")

    def collect_gb_lines(start_idx: int) -> List[str]:
        res_list = []
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            if line.startswith("VALUE:"):
                val = line[len("VALUE:"):].strip()
                if val == "START_GB" or val.startswith("PER_GEN_") or val.startswith("COKER_DIM:"):
                    break
                res_list.append(val)
        return res_list

    gb_vals = collect_gb_lines(idx_gb)

    if len(gb_vals) % 2 != 0:
        raise RuntimeError(f"Expected even number of lines for GB, got {len(gb_vals)}")
    
    parsed_gb = []
    for idx in range(0, len(gb_vals), 2):
        gen = gb_vals[idx]
        lt = gb_vals[idx+1]
        coef, exponents = parse_leading_term(lt, vars_list)
        parsed_gb.append((coef, exponents))

    # 5. Finiteness check and quotient sizing
    try:
        quotient_size = count_quotient_size(parsed_gb, vars_list, qudit_dim, is_gsd=False)
        fusion_rules = compute_fusion_rules_str(qudit_dim, quotient_size)
    except ValueError as e:
        if "Quotient ring is infinite." in str(e):
            quotient_size = float('inf')
            fusion_rules = "infinite"
        else:
            raise

    # Parse cokernel dimensions from Macaulay2 output using re.search
    coker_exponents = {}
    for line in lines:
        m = re.search(r'VALUE:COKER_DIM:(\d+):(\d+):(\d+)', line)
        if m:
            p = int(m.group(1))
            j = int(m.group(2))
            val = int(m.group(3))
            coker_exponents.setdefault(p, {})[j] = val
            
    nrows = len(stabilizer_matrix)
    ncols = len(stabilizer_matrix[0])
    
    T_active = 1
    for j in range(1, d + 1):
        if j <= len(L):
            T_active *= L[j-1]
            
    Q = 1
    for p, j_dict in coker_exponents.items():
        sum_dims = sum(j_dict.values())
        coker_size_p = p ** sum_dims
        a = factors_dict.get(p, 1)
        corr_p = - (ncols - nrows) * T_active * a
        if corr_p >= 0:
            Q_p = coker_size_p * (p ** corr_p)
        else:
            Q_p = coker_size_p // (p ** (-corr_p))
        Q *= Q_p
        
    if nrows % 2 == 0:
        gsd = Q
    else:
        gsd = Q ** 2

    # 6. Compute periodicities using Python-Side elimination-ideal method
    periods = []
    for i in range(1, d + 1):
        gens_str = get_val_after_marker(f"VALUE:PER_GEN_{i}")
        if gens_str is None:
            raise ValueError(f"Could not parse elimination ideal for dimension {i} from Macaulay2 output: {stdout}")
        
        gens = extract_generators(gens_str)
        xi_name = f"x{i}"
        
        period = compute_periodicity_of_var(gens, xi_name, qudit_dim, m2_ideal_str, vars_list)
        periods.append(period)

    result = {
        "gsd": gsd,
        "periodicities": {
            "l_x": periods[0] if len(periods) >= 1 else 0,
            "l_y": periods[1] if len(periods) >= 2 else 0,
            **{f"l_{i}": periods[i-1] for i in range(1, len(periods) + 1)}
        },
        "fusion_rules": fusion_rules
    }

    utils.save_discovery("grobner_discovery", result)
    utils.log_python_run("mobility_toolkit.grobner", "compute_gsd_and_periodicity", (stabilizer_matrix, Lx, Ly, qudit_dim), {"L": L}, result)

    return result
