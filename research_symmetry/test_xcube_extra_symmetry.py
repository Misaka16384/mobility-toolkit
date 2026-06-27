import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script
from research_symmetry.extract_general_symmetry_auto import auto_detect_indices, list_to_m2_matrix

def compute_restricted_ideal_xcube_sym(model_name: str, SXsym_list, SZsym_list, SXgauge_list, SZgauge_list):
    allowed_indices = auto_detect_indices(SXgauge_list, SZgauge_list)
    m2_indices = ", ".join(str(idx - 1) for idx in allowed_indices)
    
    SXsym = list_to_m2_matrix(SXsym_list)
    SZsym = list_to_m2_matrix(SZsym_list)
    SXgauge = list_to_m2_matrix(SXgauge_list)
    SZgauge = list_to_m2_matrix(SZgauge_list)
    
    m2_script = f"""R = ZZ/2[x, y, z, t, u, w] / ideal(x*t - 1, y*u - 1, z*w - 1)

-- Define stabilizers in M2
SXsym = {SXsym}
SZsym = {SZsym}
SXgauge = {SXgauge}
SZgauge = {SZgauge}

-- Define antipode map
conjugateMatrix = M -> (
    sub(M, {{x => t, y => u, z => w, t => x, u => y, w => z}})
)

-- Define MsymT and MgaugeT
SZsymconj = conjugateMatrix(SZsym)
SXsymconj = conjugateMatrix(SXsym)
Msym = (transpose(SZsymconj)) || (transpose(SXsymconj))
MsymT = transpose(Msym)

SZgaugeconj = conjugateMatrix(SZgauge)
SXgaugeconj = conjugateMatrix(SXgauge)
Mgauge = (transpose(SZgaugeconj)) || (transpose(SXgaugeconj))
MgaugeT = transpose(Mgauge)

-- Restrict to allowed components
allowed = {{{m2_indices}}}
MsymTsub = submatrix(MsymT, , allowed)
MgaugeTsub = submatrix(MgaugeT, , allowed)

-- Kernel
K = kernel MsymTsub

-- Syndrome
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
    print("=================== X-CUBE WITH ENFORCED MATTER SYMMETRY ===================")
    
    # We add 1 matter qubit (qubit 4) to X-cube (qubits 1, 2, 3)
    # Cube: SX = [1+t+u+t*u, 1+u+w+u*w, 1+t+w+t*w, 0], SZ = [0, 0, 0, 0]
    # Star 1: SX = [0, 0, 0, 0], SZ = [1+z, 1+x, 0, 0]
    # Star 2: SX = [0, 0, 0, 0], SZ = [0, 1+x, 1+y, 0]
    # Symmetry C_v: SX = [0, 0, 0, 1], SZ = [1+z, 1+x, 0, 0] (which we proved commutes with Cube)
    
    # We study lineons (violations of Star operators)
    # The symmetry constraints are: Cube operator (X-type) AND C_v (which couples qubit 4)
    # The gauge stabilizers under study are: Star 1 and Star 2
    # Since Gauge is Star 1 and Star 2, allowed indices will be X_1, X_2, X_3 (indices 1, 2, 3)
    # Let's run this and see if the matter coupling C_v restricts the lineon mobility even further!
    compute_restricted_ideal_xcube_sym(
        "X-Cube Lineons with C_v Constraint",
        SXsym_list=[
            ["1+t+u+t*u", "1+u+w+u*w", "1+t+w+t*w", "0"], # Cube
            ["0", "0", "0", "1"]                          # C_v X-part
        ],
        SZsym_list=[
            ["0", "0", "0", "0"],                         # Cube
            ["1+z", "1+x", "0", "0"]                      # C_v Z-part
        ],
        SXgauge_list=[
            ["0", "0", "0", "0"],
            ["0", "0", "0", "0"]
        ],
        SZgauge_list=[
            ["1+z", "1+x", "0", "0"],
            ["0", "1+x", "1+y", "0"]
        ]
    )
