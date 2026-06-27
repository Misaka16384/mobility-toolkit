import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def compute_non_css_restricted_ideal(model_name: str, SXsym: str, SZsym: str, SXgauge: str, SZgauge: str, allowed_indices: list):
    """
    Computes the restricted anyon annihilator ideal for a general (CSS or non-CSS) stabilizer code,
    with specified allowed string operator components (1-based indices into 2Q-dimensional Pauli vector).
    No underscores in M2 variables to prevent M2 subscripting parsing errors.
    """
    # Convert allowed_indices to M2 0-based indices list
    m2_indices = ", ".join(str(idx - 1) for idx in allowed_indices)
    
    m2_script = f"""R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1)

-- Define stabilizers in M2
SXsym = {SXsym}
SZsym = {SZsym}
SXgauge = {SXgauge}
SZgauge = {SZgauge}

-- Define a function to conjugate a matrix (antipode map)
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
            # skip command prompt
            if not line.startswith("i") and not line.startswith("o") and line != "":
                gens.append(line)
        gens_str = " ".join(gens).strip()
        print(f"[{model_name}] Restricted Annihilator Ideal (Syndrome Ideal): {gens_str}")
    except ValueError:
        print(f"[{model_name}] Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== GENERAL RESTRICTED ANNIHILATOR EXTRACTION ===================")
    
    # 1. CSS Model A:
    # Qubits: 3 (1 vertex, 2 edges)
    # Symmetry C_v: X = [1, 0, 0], Z = [0, 0, u]
    # Gauge B_p: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # Allowed string components: X2 and X3 (indices 2 and 3)
    compute_non_css_restricted_ideal(
        "CSS Model A",
        SXsym="matrix(R, {{1, 0, 0}})",
        SZsym="matrix(R, {{0, 0, u}})",
        SXgauge="matrix(R, {{0, 0, 0}})",
        SZgauge="matrix(R, {{0, 1-y, 1-x}})",
        allowed_indices=[2, 3]
    )
    
    # 2. Non-CSS Model A (Hadamard on qubit 2: swap component 2 of X and Z)
    # Symmetry C_v': X = [1, 0, 0], Z = [0, 0, u]
    # Gauge B_p': X = [0, 1-y, 0], Z = [0, 0, 1-x]
    # Allowed string components: Z2 and X3 (indices 5 and 3)
    compute_non_css_restricted_ideal(
        "Non-CSS Model A (Hadamard on Q2)",
        SXsym="matrix(R, {{1, 0, 0}})",
        SZsym="matrix(R, {{0, 0, u}})",
        SXgauge="matrix(R, {{0, 1-y, 0}})",
        SZgauge="matrix(R, {{0, 0, 1-x}})",
        allowed_indices=[3, 5]
    )
    
    # 3. CSS Model B:
    # Qubits: 3
    # Symmetry C_v: X = [1, 0, 0], Z = [0, t+t*u^2, u^2+t*u^2]
    # Gauge B_p: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # Allowed string components: X2 and X3 (indices 2 and 3)
    compute_non_css_restricted_ideal(
        "CSS Model B",
        SXsym="matrix(R, {{1, 0, 0}})",
        SZsym="matrix(R, {{0, t+t*u^2, u^2+t*u^2}})",
        SXgauge="matrix(R, {{0, 0, 0}})",
        SZgauge="matrix(R, {{0, 1-y, 1-x}})",
        allowed_indices=[2, 3]
    )
