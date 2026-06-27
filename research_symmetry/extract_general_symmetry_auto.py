import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def auto_detect_indices(SXgauge_list, SZgauge_list):
    Q = len(SXgauge_list[0])
    allowed = []
    for j in range(Q):
        col_x_nonzero = False
        for row in SXgauge_list:
            val = row[j].strip()
            if val != "0" and val != "":
                col_x_nonzero = True
                break
        col_z_nonzero = False
        for row in SZgauge_list:
            val = row[j].strip()
            if val != "0" and val != "":
                col_z_nonzero = True
                break
                
        if col_x_nonzero:
            allowed.append(Q + j + 1)  # allow Z_j to violate X_j
        if col_z_nonzero:
            allowed.append(j + 1)      # allow X_j to violate Z_j
            
    return sorted(allowed)

def list_to_m2_matrix(lst):
    rows_str = []
    for row in lst:
        row_str = "{" + ", ".join(row) + "}"
        rows_str.append(row_str)
    return "matrix(R, {" + ", ".join(rows_str) + "})"

def compute_restricted_ideal_auto(model_name: str, SXsym_list, SZsym_list, SXgauge_list, SZgauge_list):
    """
    Computes the restricted anyon annihilator ideal for a general stabilizer code
    with automatically detected allowed string operator components.
    """
    # 1. Auto-detect allowed indices
    allowed_indices = auto_detect_indices(SXgauge_list, SZgauge_list)
    m2_indices = ", ".join(str(idx - 1) for idx in allowed_indices)
    
    # 2. Convert lists to M2 matrix strings
    SXsym = list_to_m2_matrix(SXsym_list)
    SZsym = list_to_m2_matrix(SZsym_list)
    SXgauge = list_to_m2_matrix(SXgauge_list)
    SZgauge = list_to_m2_matrix(SZgauge_list)
    
    m2_script = f"""R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1)

-- Define stabilizers in M2
SXsym = {SXsym}
SZsym = {SZsym}
SXgauge = {SXgauge}
SZgauge = {SZgauge}

-- Define antipode map
conjugateMatrix = M -> (
    sub(M, {{x => t, y => u, t => x, u => y}})
)

-- Define commutation matrices MsymT and MgaugeT
SZsymconj = conjugateMatrix(SZsym)
SXsymconj = conjugateMatrix(SXsym)
Msym = (transpose(SZsymconj)) || (transpose(SXsymconj))
MsymT = transpose(Msym)

SZgaugeconj = conjugateMatrix(SZgauge)
SXgaugeconj = conjugateMatrix(SXgauge)
Mgauge = (transpose(SZgaugeconj)) || (transpose(SXgaugeconj))
MgaugeT = transpose(Mgauge)

-- Restrict MsymT and MgaugeT to the allowed components of W
-- allowed_indices: {m2_indices}
allowed = {{{m2_indices}}}
MsymTsub = submatrix(MsymT, , allowed)
MgaugeTsub = submatrix(MgaugeT, , allowed)

-- Allowed string operators WT are in the kernel of MsymTsub
K = kernel MsymTsub

-- Syndrome module of allowed string operators under gauge stabilizers
Smatrix = MgaugeTsub * (generators K)
Smodule = image Smatrix

print "VALUE:SYNDROME_IDEAL_START"
print generators gb Smodule
print "VALUE:SYNDROME_IDEAL_END"
"""

    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        print(f"[{model_name}] Macaulay2 failed: {stderr or stdout}")
        return
        
    # Parse output
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
    print("=================== AUTOMATIC RESTRICTED ANNIHILATOR EXTRACTION ===================")
    
    # 1. CSS Model A:
    compute_restricted_ideal_auto(
        "CSS Model A",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "0", "u"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # 2. Non-CSS Model A (Hadamard on Q2)
    compute_restricted_ideal_auto(
        "Non-CSS Model A (Hadamard on Q2)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "0", "u"]],
        SXgauge_list=[["0", "1-y", "0"]],
        SZgauge_list=[["0", "0", "1-x"]]
    )
    
    # 3. CSS Model B
    compute_restricted_ideal_auto(
        "CSS Model B",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t+t*u^2", "u^2+t*u^2"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # 4. Non-CSS Model B (Hadamard on Q2)
    compute_restricted_ideal_auto(
        "Non-CSS Model B (Hadamard on Q2)",
        SXsym_list=[["1", "t+t*u^2", "0"]],
        SZsym_list=[["0", "0", "u^2+t*u^2"]],
        SXgauge_list=[["0", "1-y", "0"]],
        SZgauge_list=[["0", "0", "1-x"]]
    )
    
    # 5. CSS Model C
    compute_restricted_ideal_auto(
        "CSS Model C",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t+t*u", "u^4+t*u^4"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # 6. Non-CSS Model C (Hadamard on Q2)
    compute_restricted_ideal_auto(
        "Non-CSS Model C (Hadamard on Q2)",
        SXsym_list=[["1", "t+t*u", "0"]],
        SZsym_list=[["0", "0", "u^4+t*u^4"]],
        SXgauge_list=[["0", "1-y", "0"]],
        SZgauge_list=[["0", "0", "1-x"]]
    )
    
    # 7. Non-CSS Model A (Phase gate S on Q2 - which makes A_v non-CSS, but doesn't change B_p or C_v)
    # This is to verify that a non-CSS change to other stabilizers doesn't affect the restricted annihilator ideal.
    compute_restricted_ideal_auto(
        "Non-CSS Model A (Phase gate S on Q2)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "0", "u"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
