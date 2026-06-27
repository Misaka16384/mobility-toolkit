import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script
from research_symmetry.extract_general_symmetry_auto import auto_detect_indices, list_to_m2_matrix

def compute_restricted_ideal_2d(model_name: str, SXsym_list, SZsym_list, SXgauge_list, SZgauge_list):
    allowed_indices = auto_detect_indices(SXgauge_list, SZgauge_list)
    m2_indices = ", ".join(str(idx - 1) for idx in allowed_indices)
    
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

def compute_restricted_ideal_3d(model_name: str, SXsym_list, SZsym_list, SXgauge_list, SZgauge_list):
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
    print("=================== 1. DECOMPOSITION STRUCTURE TESTS ===================")
    
    # Example 1: f = x + y
    # Decomposition: P = 1, Q = 1
    # Cv: X = [1, 0, 0], Z = [0, t, u]
    compute_restricted_ideal_2d(
        "f = x + y (P=1, Q=1)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t", "u"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # Example 2: f = 1 + x^2 + y + x*y
    # Decomposition: P = 1+x+y, Q = 0
    # Cv: X = [1, 0, 0], Z = [0, t*(1+t+u), 0] = [0, t+x+t*u, 0]
    compute_restricted_ideal_2d(
        "f = 1 + x^2 + y + x*y (P=1+x+y, Q=0)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t+x+t*u", "0"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # Example 3: f = 1 + x*y
    # Decomposition: P = y, Q = 1
    # Cv: X = [1, 0, 0], Z = [0, t*u, u]
    compute_restricted_ideal_2d(
        "f = 1 + x*y (P=y, Q=1)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t*u", "u"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    # Example 4: f = x + y^3
    # Decomposition: P = 1, Q = 1+y+y^2
    # Cv: X = [1, 0, 0], Z = [0, t, u*(1+u+u^2)] = [0, t, u+u^2+u^3]
    compute_restricted_ideal_2d(
        "f = x + y^3 (P=1, Q=1+y+y^2)",
        SXsym_list=[["1", "0", "0"]],
        SZsym_list=[["0", "t", "u+u^2+u^3"]],
        SXgauge_list=[["0", "0", "0"]],
        SZgauge_list=[["0", "1-y", "1-x"]]
    )
    
    print("\n=================== 2. X-CUBE FRACTON/LINEON MOBILITY TESTS ===================")
    
    # X-cube star operators (Z-type, 2 generators) and cube operators (X-type, 1 generator)
    # Qubits: 3 (representing x, y, z edges)
    # Cube: SX = [1+t+u+t*u, 1+u+w+u*w, 1+t+w+t*w], SZ = [0, 0, 0]
    # Star 1: SX = [0, 0, 0], SZ = [1+z, 1+x, 0]
    # Star 2: SX = [0, 0, 0], SZ = [0, 1+x, 1+y]
    
    # Case A: Lineon Excitations (violations of Star operators)
    # Symmetry constraints: Cube operator (X-type)
    # Gauge stabilizers: Star 1, Star 2 (Z-type)
    # Expected: restricted to 1D lines (annihilator contains e.g. x-1, y-1 for z-lineon)
    compute_restricted_ideal_3d(
        "X-Cube Lineons (Gauge = Stars, Sym = Cube)",
        SXsym_list=[["1+t+u+t*u", "1+u+w+u*w", "1+t+w+t*w"]],
        SZsym_list=[["0", "0", "0"]],
        SXgauge_list=[["0", "0", "0"], ["0", "0", "0"]],
        SZgauge_list=[["1+z", "1+x", "0"], ["0", "1+x", "1+y"]]
    )
    
    # Case B: Fracton Excitations (violations of Cube operator)
    # Symmetry constraints: Star 1, Star 2 (Z-type)
    # Gauge stabilizers: Cube operator (X-type)
    # Expected: completely immobile (annihilator is maximal, e.g. x-1, y-1, z-1)
    compute_restricted_ideal_3d(
        "X-Cube Fractons (Gauge = Cube, Sym = Stars)",
        SXsym_list=[["0", "0", "0"], ["0", "0", "0"]],
        SZsym_list=[["1+z", "1+x", "0"], ["0", "1+x", "1+y"]],
        SXgauge_list=[["1+t+u+t*u", "1+u+w+u*w", "1+t+w+t*w"]],
        SZgauge_list=[["0", "0", "0"]]
    )
