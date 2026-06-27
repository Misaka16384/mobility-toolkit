import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def compute_code_homology(model_name: str, SX_list, SZ_list):
    """
    Computes the homology module H = Ker(Commutation) / Im(Stabilizers)
    representing the non-trivial symmetries (logical operators) on the infinite plane.
    """
    from research_symmetry.extract_general_symmetry_auto import list_to_m2_matrix
    SX = list_to_m2_matrix(SX_list)
    SZ = list_to_m2_matrix(SZ_list)
    
    m2_script = f"""R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1)

SX = {SX}
SZ = {SZ}

-- Define antipode map
conjugateMatrix = M -> (
    sub(M, {{x => t, y => u, t => x, u => y}})
)

-- MsymT represents the commutation map: Ker(MsymT) is the set of all commuting operators
SZconj = conjugateMatrix(SZ)
SXconj = conjugateMatrix(SX)
Msym = (transpose(SZconj)) || (transpose(SXconj))
MsymT = transpose(Msym)

-- MstabT represents the stabilizer image map
Mstab = SX | SZ
MstabT = transpose(Mstab)

-- H = Ker(MsymT) / Im(MstabT)
K = kernel MsymT
Q = numColumns SX
F = R^(2*Q)
Ksub = image map(F, , generators K)
Isub = image map(F, , MstabT)
H = Ksub / Isub
print "VALUE:HOMOLOGY_START"
print H
print "VALUE:DIM_START"
print (dim H)
print "VALUE:GENS_START"
print generators gb H
print "VALUE:HOMOLOGY_END"
"""

    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        print(f"[{model_name}] Macaulay2 failed: {stderr or stdout}")
        return
        
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        idx_hom = lines.index("VALUE:HOMOLOGY_START")
        idx_dim = lines.index("VALUE:DIM_START")
        idx_gen = lines.index("VALUE:GENS_START")
        idx_end = lines.index("VALUE:HOMOLOGY_END")
        
        hom_str = " ".join(lines[idx_hom+1:idx_dim]).strip()
        dim_str = " ".join(lines[idx_dim+1:idx_gen]).strip()
        gen_str = " ".join(lines[idx_gen+1:idx_end]).strip()
        
        print(f"[{model_name}] Homology (Symmetry Quotient Module): {hom_str}")
        print(f"  Krull Dimension of Symmetries: {dim_str}")
        print(f"  Generators of Symmetries: {gen_str}")
    except ValueError:
        print(f"[{model_name}] Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== STABILIZER CODE HOMOLOGY (NATIVE SYMMETRIES) ===================")
    
    # 1. Toric Code
    compute_code_homology(
        "Toric Code",
        SX_list=[["1-t", "1-u"]],
        SZ_list=[["1-y", "1-x"]]
    )
    print()
    
    # 2. SSET Model A
    # Qubits: 3 (1 matter, 2 gauge)
    # A_v: X = [0, 1+t, 1+u], Z = [1+y, 0, 0]
    # B_p: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # C_v: X = [1, 0, 0], Z = [0, 0, u]
    compute_code_homology(
        "SSET Model A",
        SX_list=[
            ["0", "1+t", "1+u"],
            ["0", "0", "0"],
            ["1", "0", "0"]
        ],
        SZ_list=[
            ["1+y", "0", "0"],
            ["0", "1-y", "1-x"],
            ["0", "0", "u"]
        ]
    )
