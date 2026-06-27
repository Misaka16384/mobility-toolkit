import sympy as sp
import re
from typing import List, Dict, Any

# Define variables in SymPy
x, y, t, u = sp.symbols('x y t u')

def clean_poly_str(p_str: str) -> str:
    """Clean polynomial string for parsing."""
    p_str = p_str.replace(" ", "")
    # replace inverses
    p_str = p_str.replace("x^-1", "t").replace("x**-1", "t")
    p_str = p_str.replace("y^-1", "u").replace("y**-1", "u")
    return p_str

def parse_to_sympy(p_str: str):
    """Parse a polynomial string to SymPy expression."""
    cleaned = clean_poly_str(p_str)
    if not cleaned or cleaned == "0":
        return sp.Integer(0)
    # SymPy parsing
    try:
        # replace implicit multiplications if any
        expr = sp.sympify(cleaned)
        return expr
    except Exception as e:
        # manual fallback for simple cases
        return sp.sympify(cleaned.replace("*", "*"))

def mod2_sympy(expr):
    if expr.is_Integer:
        return sp.Integer(expr % 2)
    elif expr.is_Symbol:
        return expr
    elif expr.is_Add:
        return sum(mod2_sympy(arg) for arg in expr.args)
    elif expr.is_Mul:
        coeff, rest = expr.as_coeff_Mul()
        return sp.Integer(coeff % 2) * rest
    elif expr.is_Pow:
        base, exp = expr.as_base_exp()
        return mod2_sympy(base) ** exp
    return expr

def conjugate_sympy(expr):
    """Apply the antipode map (x -> t, y -> u, t -> x, u -> y)."""
    if expr == 0:
        return sp.Integer(0)
    return expr.subs({x: t, y: u, t: x, u: y})

def detect_sset_symmetry(stabilizer_matrix: List[List[str]]) -> Dict[str, Any]:
    """
    Automatically detects the matter qubits and the subsystem symmetry polynomial f(x, y)
    from a given stabilizer matrix.
    
    Stabilizer matrix format:
    Each row has 2*Q elements, first Q are X-parts, last Q are Z-parts.
    """
    num_rows = len(stabilizer_matrix)
    if num_rows == 0:
        return {"error": "Empty stabilizer matrix"}
        
    num_cols = len(stabilizer_matrix[0])
    Q = num_cols // 2
    
    # Parse to SymPy
    parsed_matrix = []
    for row in stabilizer_matrix:
        parsed_row = [parse_to_sympy(cell) for cell in row]
        parsed_matrix.append(parsed_row)
        
    # Separate into X and Z parts
    X_parts = [row[:Q] for row in parsed_matrix]
    Z_parts = [row[Q:] for row in parsed_matrix]
    
    print(f"Analyzing stabilizer code with Q={Q} qubits and {num_rows} generators...")
    
    # 1. Search for matter qubits
    # A matter qubit is a qubit index `m` where there exists a generator `r` such that:
    # - X_parts[r][m] is a non-zero unit (e.g. 1 or monomial), and X_parts[r][j] == 0 for all j != m.
    # - In other words, it is a localized X-term.
    matter_qubits = []
    matter_generators = []
    for m in range(Q):
        for r in range(num_rows):
            # Check if X_parts[r] is non-zero only at m
            is_local_x = False
            val = X_parts[r][m]
            if val != 0:
                other_zeros = all(X_parts[r][j] == 0 for j in range(Q) if j != m)
                if other_zeros:
                    is_local_x = True
            
            if is_local_x:
                matter_qubits.append(m)
                matter_generators.append(r)
                print(f"Found matter qubit at index {m} (qubit {m+1}) from generator row {r+1} with X-term: {val}")
                break
                
    if not matter_qubits:
        return {
            "success": False,
            "message": "No matter qubits (localized X-term stabilizer generators) detected. This model does not fit the SSET gauging structure directly."
        }
        
    # 2. Extract the decoration polynomial f(x, y)
    # The decoration polynomial coupling f(x, y) can be identified in two ways:
    # Way A: Look at the Z-type stabilizers that couple to the matter qubit.
    # Way B: Use the commutation relations (symplectic product) between the stabilizers.
    
    results = []
    for m, gen_idx in zip(matter_qubits, matter_generators):
        # Let's find Z-couplings on qubit `m` in other generator rows
        z_couplings = []
        for r in range(num_rows):
            if r == gen_idx:
                continue
            z_val = Z_parts[r][m]
            if z_val != 0:
                z_couplings.append((r, z_val))
                
        print(f"Z-couplings on matter qubit {m+1} from other generators:")
        for r, z_val in z_couplings:
            print(f"  Row {r+1}: {z_val}")
            
        # Way B: Commutation relation validation.
        # Let C_v be the matter generator (row gen_idx).
        # Any other stabilizer A_v (row r) must commute with C_v.
        # Symplectic product of C_v and A_v (conjugating C_v):
        # sum_{j} (C_X[j]^\dagger * A_Z[j] + C_Z[j]^\dagger * A_X[j]) = 0
        # Since C_X is non-zero only at m (value val), and C_Z is Z_parts[gen_idx]:
        # val^\dagger * A_Z[m] + sum_{j} C_Z[j]^\dagger * A_X[j] = 0
        # Thus, the coupling A_Z[m] = val^\dagger * sum_{j} C_Z[j]^\dagger * A_X[j] (mod 2)
        # This gives a relation between the symmetry f(x, y) (A_Z[m]) and the coupling terms in C_v!
        
        # Let's reconstruct f(x,y) from the first non-trivial Z-coupling found
        f_candidate = None
        if z_couplings:
            f_candidate = z_couplings[0][1]
            # Normalize to conventional variables (substitute t -> 1/x etc. if needed, or keep in SymPy form)
            # Expand mod 2
            f_candidate = sp.expand(f_candidate)
            # Apply mod 2 coefficients
            f_candidate = mod2_sympy(f_candidate)
            
        results.append({
            "matter_qubit": m + 1,
            "matter_generator_row": gen_idx + 1,
            "symmetry_polynomial_f": str(f_candidate) if f_candidate is not None else "0",
            "z_couplings": [(r+1, str(z)) for r, z in z_couplings]
        })
        
    return {
        "success": True,
        "results": results
    }

# Let's run a test on SSET Model A, B, and C
if __name__ == "__main__":
    print("=================== SSET SYMMETRY DETECTION TEST ===================")
    
    # 1. Model A stabilizer matrix: f = 1 + y. Qubits: 3 (1 matter, 2 gauge)
    # A_v row: X = [0, 1+t, 1+u], Z = [1+y, 0, 0]
    # B_p row: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # C_v row: X = [1, 0, 0], Z = [0, 0, u]
    model_a = [
        ["0", "1 + t", "1 + u", "1 + y", "0", "0"],
        ["0", "0", "0", "0", "1 - y", "1 - x"],
        ["1", "0", "0", "0", "0", "u"]
    ]
    
    res_a = detect_sset_symmetry(model_a)
    print("Model A Results:", res_a)
    print()
    
    # 2. Model B stabilizer matrix: f = (1+x)(1+y) = 1 + x + y + x*y.
    # P = 1 + y^2, Q = y + x*y -> in inverses: P_bar = 1 + u^2, Q_bar = u + t*u.
    # C_v row: X = [1, 0, 0], Z = [0, t*P_bar, u*Q_bar] -> [0, t*(1+u^2), u*(u+t*u)] -> [0, t + t*u^2, u^2 + t*u^2]
    # A_v row: X = [0, 1+t, 1+u], Z = [f, 0, 0]
    # B_p row: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    model_b = [
        ["0", "1 + t", "1 + u", "1 + x + y + x*y", "0", "0"],
        ["0", "0", "0", "0", "1 - y", "1 - x"],
        ["1", "0", "0", "0", "t + t*u**2", "u**2 + t*u**2"]
    ]
    
    res_b = detect_sset_symmetry(model_b)
    print("Model B Results:", res_b)
    print()
    
    # 3. Toric Code (No matter qubits)
    # Qubits: 2
    toric = [
        ["1 - t", "1 - u", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    res_toric = detect_sset_symmetry(toric)
    print("Toric Code Results:", res_toric)
