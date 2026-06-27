import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def list_to_m2_matrix(lst):
    rows_str = []
    for row in lst:
        row_str = "{" + ", ".join(row) + "}"
        rows_str.append(row_str)
    return "matrix(R, {" + ", ".join(rows_str) + "})"

def auto_detect_allowed_components(SXgauge, SZgauge):
    """
    Detects allowed string operator components based on the support of gauge stabilizers.
    For each qubit j:
      - If SXgauge has non-zero in column j, allow Z_j (index Q + j + 1).
      - If SZgauge has non-zero in column j, allow X_j (index j + 1).
    """
    Q = len(SXgauge[0])
    allowed = []
    for j in range(Q):
        col_x_nonzero = False
        for row in SXgauge:
            val = row[j].strip()
            if val != "0" and val != "":
                col_x_nonzero = True
                break
        col_z_nonzero = False
        for row in SZgauge:
            val = row[j].strip()
            if val != "0" and val != "":
                col_z_nonzero = True
                break
                
        if col_x_nonzero:
            allowed.append(Q + j + 1)
        if col_z_nonzero:
            allowed.append(j + 1)
            
    return sorted(allowed)

def extract_restricted_annihilator(model_name: str, dimensions: int, SXsym, SZsym, SXgauge, SZgauge):
    """
    General program to extract the restricted annihilator ideal for any stabilizer code
    under the constraint that the symmetry stabilizers (SXsym, SZsym) are not violated.
    """
    # 1. Auto-detect allowed string components
    allowed_indices = auto_detect_allowed_components(SXgauge, SZgauge)
    m2_indices = ", ".join(str(idx - 1) for idx in allowed_indices)
    
    # 2. Setup variables and ring in M2
    if dimensions == 2:
        ring_def = "R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1)"
        sub_def = "sub(M, {x => t, y => u, t => x, u => y})"
    elif dimensions == 3:
        ring_def = "R = ZZ/2[x, y, z, t, u, w] / ideal(x*t - 1, y*u - 1, z*w - 1)"
        sub_def = "sub(M, {x => t, y => u, z => w, t => x, u => y, w => z})"
    else:
        raise ValueError("Only 2D and 3D are supported in this test script")

    # 3. Convert lists to M2 matrices
    SXsym_m2 = list_to_m2_matrix(SXsym)
    SZsym_m2 = list_to_m2_matrix(SZsym)
    SXgauge_m2 = list_to_m2_matrix(SXgauge)
    SZgauge_m2 = list_to_m2_matrix(SZgauge)
    
    m2_script = f"""{ring_def}

SXsym = {SXsym_m2}
SZsym = {SZsym_m2}
SXgauge = {SXgauge_m2}
SZgauge = {SZgauge_m2}

conjugateMatrix = M -> (
    {sub_def}
)

SZsymconj = conjugateMatrix(SZsym)
SXsymconj = conjugateMatrix(SXsym)
Msym = (transpose(SZsymconj)) || (transpose(SXsymconj))
MsymT = transpose(Msym)

SZgaugeconj = conjugateMatrix(SZgauge)
SXgaugeconj = conjugateMatrix(SXgauge)
Mgauge = (transpose(SZgaugeconj)) || (transpose(SXgaugeconj))
MgaugeT = transpose(Mgauge)

allowed = {{{m2_indices}}}
MsymTsub = submatrix(MsymT, , allowed)
MgaugeTsub = submatrix(MgaugeT, , allowed)

K = kernel MsymTsub
Smatrix = MgaugeTsub * (generators K)

Q = numColumns SXgauge
F = R^(2*Q)

-- To get the ideal in the quotient ring, we prune the image
Smodule = image Smatrix

print "VALUE:SYNDROME_IDEAL_START"
print generators gb Smodule
print "VALUE:SYNDROME_IDEAL_END"
"""

    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        print(f"[{model_name}] Macaulay2 failed: {stderr or stdout}")
        return
        
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        start_idx = lines.index("VALUE:SYNDROME_IDEAL_START")
        end_idx = lines.index("VALUE:SYNDROME_IDEAL_END")
        gens = []
        for i in range(start_idx + 1, end_idx):
            line = lines[i].strip()
            if not line.startswith("i") and not line.startswith("o") and line != "":
                gens.append(line)
        gens_str = " ".join(gens).strip()
        print(f"[{model_name}] (Allowed indices: {allowed_indices})")
        print(f"  Restricted Annihilator Ideal: {gens_str}")
    except ValueError:
        print(f"[{model_name}] Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== GENERAL RESTRICTED ANNIHILATOR EXTRACTION ===================")
    
    # 1. SSET Model A: m-anyons (violations of B_p)
    # Symmetries: C_v (which we enforce to not be violated)
    # Gauge: B_p
    extract_restricted_annihilator(
        "SSET Model A (m-anyons)",
        dimensions=2,
        SXsym=[["1", "0", "0"]],
        SZsym=[["0", "0", "u"]],
        SXgauge=[["0", "0", "0"]],
        SZgauge=[["0", "1-y", "1-x"]]
    )
    
    # 2. SSET Model A: e-anyons (violations of A_v)
    # Symmetries: C_v
    # Gauge: A_v
    extract_restricted_annihilator(
        "SSET Model A (e-anyons)",
        dimensions=2,
        SXsym=[["1", "0", "0"]],
        SZsym=[["0", "0", "u"]],
        SXgauge=[["0", "1+t", "1+u"]],
        SZgauge=[["1+y", "0", "0"]]
    )
    
    # 3. Toric Code: m-anyons (violations of B_p)
    # Symmetries: A_v
    # Gauge: B_p
    extract_restricted_annihilator(
        "Toric Code (m-anyons)",
        dimensions=2,
        SXsym=[["1-t", "1-u"]],
        SZsym=[["0", "0"]],
        SXgauge=[["0", "0"]],
        SZgauge=[["1-y", "1-x"]]
    )
    
    # 4. X-Cube: Fractons (violations of Cube)
    # Symmetries: Stars (which we enforce to not be violated)
    # Gauge: Cube
    extract_restricted_annihilator(
        "X-Cube (Fractons)",
        dimensions=3,
        SXsym=[["0", "0", "0"], ["0", "0", "0"]],
        SZsym=[["1-z", "1-x", "0"], ["0", "1-x", "1-y"]],
        SXgauge=[["1+t+u+t*u", "1+u+w+u*w", "1+t+w+t*w"]],
        SZgauge=[["0", "0", "0"]]
    )
    
    # 5. X-Cube: Lineons (violations of Stars)
    # Symmetries: Cube
    # Gauge: Stars
    extract_restricted_annihilator(
        "X-Cube (Lineons)",
        dimensions=3,
        SXsym=[["1+t+u+t*u", "1+u+w+u*w", "1+t+w+t*w"]],
        SZsym=[["0", "0", "0"]],
        SXgauge=[["0", "0", "0"], ["0", "0", "0"]],
        SZgauge=[["1-z", "1-x", "0"], ["0", "1-x", "1-y"]]
    )
