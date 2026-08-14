import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def compute_sset_torus_homology(Lx: int, Ly: int):
    """
    Computes the homology module H = Ker(MsymT) / Im(MstabT)
    for SSET Model A on a torus of size Lx x Ly.
    """
    m2_script = f"""R = ZZ/2[x, y, t, u] / ideal(x*t - 1, y*u - 1, x^{Lx} - 1, y^{Ly} - 1)

-- SSET Model A stabilizers
SX = matrix(R, {{
    {{0, 1+t, 1+u}},
    {{0, 0, 0}},
    {{1, 0, 0}}
}})
SZ = matrix(R, {{
    {{1+y, 0, 0}},
    {{0, 1-y, 1-x}},
    {{0, 0, u}}
}})

-- Define antipode map
conjugateMatrix = M -> (
    sub(M, {{x => t, y => u, t => x, u => y}})
)

-- Commutation map MsymT
SZconj = conjugateMatrix(SZ)
SXconj = conjugateMatrix(SX)
Msym = (transpose(SZconj)) || (transpose(SXconj))
MsymT = transpose(Msym)

-- Stabilizer map MstabT
Mstab = SX | SZ
MstabT = transpose(Mstab)

-- Homology on Torus
K = kernel MsymT
I = image MstabT

Q = 3
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
        print(f"Macaulay2 failed: {stderr or stdout}")
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
        
        print(f"SSET Model A on {Lx}x{Ly} Torus:")
        print(f"  Homology: {hom_str}")
        print(f"  Krull Dimension: {dim_str}")
        print("  Generators of Symmetries:")
        print(f"    {gen_str}")
    except ValueError:
        print(f"Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== SSET TORUS HOMOLOGY (LOGICALS) ===================")
    compute_sset_torus_homology(3, 3)
