import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def compute_restricted_ideal_no_indices(model_name: str, SXcommute: str, SZcommute: str, SXgauge: str, SZgauge: str):
    """
    Computes the restricted anyon annihilator ideal for a general stabilizer code
    WITHOUT specifying allowed indices (allowing all Pauli components).
    """
    m2_script = f"""R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1)

-- Define commute and gauge stabilizers in M2
SXcommute = {SXcommute}
SZcommute = {SZcommute}
SXgauge = {SXgauge}
SZgauge = {SZgauge}

-- Define antipode map
conjugateMatrix = M -> (
    sub(M, {{x => t, y => u, t => x, u => y}})
)

-- Define commutation matrices McommuteT and MgaugeT
SZcommuteconj = conjugateMatrix(SZcommute)
SXcommuteconj = conjugateMatrix(SXcommute)
Mcommute = (transpose(SZcommuteconj)) || (transpose(SXcommuteconj))
McommuteT = transpose(Mcommute)

SZgaugeconj = conjugateMatrix(SZgauge)
SXgaugeconj = conjugateMatrix(SXgauge)
Mgauge = (transpose(SZgaugeconj)) || (transpose(SXgaugeconj))
MgaugeT = transpose(Mgauge)

-- String operators WT are in the kernel of McommuteT
K = kernel McommuteT

-- Syndrome module of allowed string operators under gauge stabilizers
Smatrix = MgaugeT * (generators K)
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
        print(f"[{model_name}] Restricted Annihilator Ideal (Syndrome Ideal): {gens_str}")
    except ValueError:
        print(f"[{model_name}] Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== GENERAL RESTRICTED ANNIHILATOR (NO INDICES) ===================")
    
    # 1. CSS Model A:
    # S_commute = {C_v, A_v}
    # C_v: X = [1, 0, 0], Z = [0, 0, u]
    # A_v: X = [0, 1+t, 1+u], Z = [1+y, 0, 0]
    # S_gauge = {B_p}
    # B_p: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    compute_restricted_ideal_no_indices(
        "CSS Model A",
        SXcommute="matrix(R, {{1, 0, 0}, {0, 1+t, 1+u}})",
        SZcommute="matrix(R, {{0, 0, u}, {1+y, 0, 0}})",
        SXgauge="matrix(R, {{0, 0, 0}})",
        SZgauge="matrix(R, {{0, 1-y, 1-x}})"
    )
    
    # 2. Non-CSS Model A (Hadamard on Q2)
    # Perform Hadamard on qubit 2 (swap component 2 of X and Z)
    # C_v': X = [1, 0, 0], Z = [0, 0, u]
    # A_v': X = [0, 1+y, 1+u], Z = [1+y, 1+t, 0]  -- wait, Z_2 of A_v was 0, X_2 was 1+t. After Hadamard, X_2 becomes 1+y (wait, antipode of 1+t is 1+y), and Z_2 becomes 1+t. Let's write them carefully.
    # Original A_v: X = [0, 1+t, 1+u], Z = [1+y, 0, 0]
    # Rotated A_v': X = [0, 0, 1+u], Z = [1+y, 1+t, 0] --- wait! If Hadamard is performed on qubit 2:
    # X_2 <-> Z_2. So the X_2 component of A_v (which was 1+t) becomes the Z_2 component of A_v'.
    # And the Z_2 component of A_v (which was 0) becomes the X_2 component of A_v'.
    # So A_v': X = [0, 0, 1+u], Z = [1+y, 1+t, 0].
    # C_v': X = [1, 0, 0], Z = [0, 0, u] (no change because Q2 has 0 in both X and Z).
    # B_p': X = [0, 1-y, 0], Z = [0, 0, 1-x] (since original B_p was X = [0, 0, 0], Z = [0, 1-y, 1-x], after swap: X_2 is 1-y, Z_2 is 0).
    compute_restricted_ideal_no_indices(
        "Non-CSS Model A (Hadamard on Q2)",
        SXcommute="matrix(R, {{1, 0, 0}, {0, 0, 1+u}})",
        SZcommute="matrix(R, {{0, 0, u}, {1+y, 1+t, 0}})",
        SXgauge="matrix(R, {{0, 1-y, 0}})",
        SZgauge="matrix(R, {{0, 0, 1-x}})"
    )
