import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.bridge import run_m2_script

def compute_sset_torus_relations(Lx: int, Ly: int):
    """
    Computes the relations (syzygies) of the stabilizer generators
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

M = SX | SZ
MT = transpose(M)

-- Relations between stabilizers: v * M = 0 mod 2
-- which is the kernel of MT
K = kernel MT

print "VALUE:RELATIONS_START"
print generators gb K
print "VALUE:RELATIONS_END"
"""

    code, stdout, stderr = run_m2_script(m2_script)
    if code != 0:
        print(f"Macaulay2 failed: {stderr or stdout}")
        return
        
    lines = [line.strip() for line in stdout.splitlines()]
    try:
        start_idx = lines.index("VALUE:RELATIONS_START")
        end_idx = lines.index("VALUE:RELATIONS_END")
        gens = []
        for i in range(start_idx + 1, end_idx):
            line = lines[i].strip()
            if not line.startswith("i") and not line.startswith("o") and line != "":
                gens.append(line)
        gens_str = " ".join(gens).strip()
        print(f"SSET Model A on {Lx}x{Ly} Torus:")
        print(f"  Stabilizer Relations (Symmetries): {gens_str}")
    except ValueError:
        print(f"Failed to parse M2 output: {stdout}")

if __name__ == "__main__":
    print("=================== SSET NATIVE RELATIONS ON TORUS ===================")
    compute_sset_torus_relations(3, 3)
