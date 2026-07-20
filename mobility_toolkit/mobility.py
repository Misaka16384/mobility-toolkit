import re
import math
from fractions import Fraction
from typing import List, Dict, Any
from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit import utils

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

    # Leniency heuristic: WSL can leave the launcher exit code non-zero on an
    # otherwise successful M2 run, so a non-zero code with no "error" marker in
    # the output is treated as success. Exit codes 124 (timeout) and 127 (no
    # backend) are NEVER swallowed: their stderr carries no "error" substring,
    # so swallowing them would let an empty/partial result fall through to the
    # caller and be misread as a valid (and wrong) answer.
    if code != 0 and code not in (124, 127):
        normalized_stderr = stderr_clean.lower()
        normalized_stdout = stdout_clean.lower()
        if "error" in normalized_stderr or "error:" in normalized_stdout or "syntax error" in normalized_stdout:
            pass
        else:
            code = 0
    return code, stdout_clean, stderr_clean


def solve_nullspace_fraction(V_matrix: List[List[int]], num_vars: int) -> List[List[int]]:
    if not V_matrix:
        basis = [[0] * num_vars for _ in range(num_vars)]
        for i in range(num_vars):
            basis[i][i] = 1
        return basis
        
    R = len(V_matrix)
    C = num_vars
    
    A = [[Fraction(val) for val in row] for row in V_matrix]
    
    pivot_cols = []
    pivot_row_map = {}
    
    row = 0
    col = 0
    while row < R and col < C:
        pivot_r = -1
        for r in range(row, R):
            if A[r][col] != 0:
                pivot_r = r
                break
        if pivot_r == -1:
            col += 1
            continue
            
        A[row], A[pivot_r] = A[pivot_r], A[row]
        
        pivot_val = A[row][col]
        for c in range(col, C):
            A[row][c] /= pivot_val
            
        for r in range(R):
            if r != row and A[r][col] != 0:
                factor = A[r][col]
                for c in range(col, C):
                    A[r][c] -= factor * A[row][c]
                    
        pivot_cols.append(col)
        pivot_row_map[col] = row
        row += 1
        col += 1
        
    free_cols = [c for c in range(C) if c not in pivot_cols]
    
    basis = []
    for f_col in free_cols:
        v = [Fraction(0)] * C
        v[f_col] = Fraction(1)
        for p_col in pivot_cols:
            p_row = pivot_row_map[p_col]
            v[p_col] = -A[p_row][f_col]
        basis.append(v)
        
    processed_basis = []
    for v in basis:
        denoms = [x.denominator for x in v]
        # ⚡ Bolt: Use math.lcm and math.gcd which are implemented in C and accept multiple arguments
        v_lcm = math.lcm(*denoms, 1)
        v_ints = [int(x * v_lcm) for x in v]
        g = math.gcd(*v_ints, 0)
        if g != 0:
            v_ints = [x // g for x in v_ints]
        first_nonzero = next((x for x in v_ints if x != 0), 0)
        if first_nonzero < 0:
            v_ints = [-x for x in v_ints]
        processed_basis.append(v_ints)
        
    return processed_basis

def compute_true_mobility_dimension(generators: List[str], qudit_dim: int, all_vars: List[str] = None) -> Dict[str, Any]:
    """Computes the true physical mobility dimension of an excitation defined by an annihilator ideal.
    This resolves the discrepancy between Krull dimension and mobility dimension for Type II fractons.

    Args:
        generators (List[str]): Generators of the annihilator ideal.
        qudit_dim (int): Prime qudit dimension N.
        all_vars (List[str], optional): Explicit list of variables to define the ring.

    Returns:
        Dict[str, Any]: Calculated mobility rank, valuation matrix, and kernel basis.
    """
    utils.log_python_run("mobility_toolkit.mobility", "compute_true_mobility_dimension", (generators, qudit_dim, all_vars), {}, "PENDING")
    
    # 1. Input Validation
    if not isinstance(generators, list) or not generators:
        raise ValueError("generators must be a non-empty list of strings.")
    for gen in generators:
        if not isinstance(gen, str):
            raise ValueError("All generators must be strings.")
            
    if not isinstance(qudit_dim, int):
        raise TypeError("qudit_dim must be an integer")
        
    # Extract variables or use all_vars
    if all_vars is not None:
        if not isinstance(all_vars, list) or not all_vars:
            raise ValueError("all_vars must be a non-empty list of strings.")
        for var in all_vars:
            if not isinstance(var, str) or not re.match(r'^[a-z]\d*$', var):
                raise ValueError(f"Invalid variable name in all_vars: '{var}'. Only lowercase variables optionally followed by digits are allowed.")
        sorted_vars = sorted(list(set(all_vars)))
    else:
        variables = set()
        for gen in generators:
            found = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', gen)
            for var in found:
                if not re.match(r'^[a-z]\d*$', var):
                    raise ValueError(f"Invalid variable name: '{var}'. Only lowercase variables optionally followed by digits are allowed.")
                variables.add(var)
        sorted_vars = sorted(list(variables))
        if not sorted_vars:
            sorted_vars = ["x"]
        
    num_vars = len(sorted_vars)
    
    # Check cache first
    from mobility_toolkit.registry import ModelRegistry
    registry = ModelRegistry()
    cached = registry.get_cached_properties(generators, qudit_dim)
    if cached is not None:
        matches = True
        if cached.get("kernel_basis"):
            matches = (len(cached["kernel_basis"][0]) == len(sorted_vars))
        elif cached.get("valuation_matrix"):
            matches = (len(cached["valuation_matrix"][0]) == len(sorted_vars))
        if matches:
            cached["variables"] = sorted_vars
            cached["divisors"] = []
            return cached

    
    # Format generators for M2
    clean_gens = [g.replace("**", "^") for g in generators]
    generators_str = ", ".join(clean_gens)
    vars_str = ", ".join(sorted_vars)
    
    # Construct M2 script to extract prime divisors and valuations
    vars_list_m2 = ", ".join(sorted_vars)
    m2_script = f"""S = ZZ/{qudit_dim}[{vars_str}]
J = ideal({generators_str})
dimJ = dim J
varsList = {{{vars_list_m2}}}
primesList = {{}}
for xi in varsList do (
    Ixi = J + ideal(xi);
    decomp = primaryDecomposition Ixi;
    for Q in decomp do (
        P = radical Q;
        dimP = dim P;
        if dimP == dimJ - 1 then (
            idx = -1;
            for k from 0 to #primesList - 1 do (
                if P == primesList#k then ( idx = k; break; );
            );
            if idx == -1 then (
                primesList = append(primesList, P);
                idx = #primesList - 1;
            );
            val = degree Q // degree P;
            print ("VAL:" | toString xi | ":" | toString idx | ":" | toString val | ":" | toString P);
        );
    );
);
"""

    code, stdout, stderr = safe_run_m2_script(m2_script)
    if code != 0:
        raise RuntimeError(f"Macaulay2 script failed with exit code {code}. Stderr: {stderr}. Stdout: {stdout}")

    # Parse M2 output to construct the valuation matrix
    val_lines = []
    for line in stdout.splitlines():
        sline = line.strip()
        if sline.startswith("VAL:"):
            val_lines.append(sline[4:])
            
    # Parse valuations and identify unique primes
    unique_primes = {}
    parsed_valuations = [] # list of (var, prime_idx, valuation)
    for entry in val_lines:
        parts = entry.split(":", 3)
        if len(parts) == 4:
            var_name, idx_str, val_str, prime_ideal = parts
            try:
                idx = int(idx_str)
                val = int(val_str)
                parsed_valuations.append((var_name, idx, val))
                unique_primes[idx] = prime_ideal
            except ValueError:
                continue
                
    num_primes = len(unique_primes)
    
    # Build the valuation matrix V of shape (num_primes, num_vars)
    V_matrix = [[0] * num_vars for _ in range(num_primes)]
    var_to_col = {var: i for i, var in enumerate(sorted_vars)}
    
    for var_name, idx, val in parsed_valuations:
        col = var_to_col[var_name]
        V_matrix[idx][col] = val
        
    # Solve for the kernel of V over QQ
    basis = solve_nullspace_fraction(V_matrix, num_vars)
    
    result = {
        "mobility_dimension": len(basis),
        "valuation_matrix": V_matrix,
        "divisors": [unique_primes[k] for k in sorted(unique_primes.keys())],
        "kernel_basis": basis,
        "variables": sorted_vars
    }
    
    # Cache the result
    registry.cache_properties(
        generators=generators,
        qudit_dim=qudit_dim,
        mobility_dimension=result["mobility_dimension"],
        valuation_matrix=result["valuation_matrix"],
        kernel_basis=result["kernel_basis"]
    )
    
    utils.save_discovery("mobility_rank_discovery", result)
    utils.log_python_run("mobility_toolkit.mobility", "compute_true_mobility_dimension", (generators, qudit_dim, all_vars), {}, result)
    
    return result

