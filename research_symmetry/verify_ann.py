import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.homology import compute_ext_krull

def verify():
    # 1. Standard Toric Code
    # Qubits: 2 (edges)
    # Row 1: X = [1-t, 1-u], Z = [0, 0]
    # Row 2: X = [0, 0], Z = [1-y, 1-x]
    toric = [
        ["1 - t", "1 - u", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    
    print("=== Toric Code Homology ===")
    res_toric = compute_ext_krull(toric, qudit_dim=2, p_ext=0)
    print("Krull Dimension:", res_toric["krull_dimension"])
    print("Annihilator Generators:", res_toric["annihilator_generators"])
    print()
    
    # 2. SSET Model A (including C_v as stabilizer)
    # Qubits: 3 (1 vertex, 2 edges)
    # Row 1 (A_v): X = [0, 1-t, 1-u], Z = [1+y, 0, 0]
    # Row 2 (B_p): X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # Row 3 (C_v): X = [1, 0, 0], Z = [0, 0, u]  (where u is y^-1)
    model_a = [
        ["0", "1 - t", "1 - u", "1 + y", "0", "0"],
        ["0", "0", "0", "0", "1 - y", "1 - x"],
        ["1", "0", "0", "0", "0", "u"]
    ]
    
    print("=== SSET Model A (with C_v) Homology ===")
    res_model_a = compute_ext_krull(model_a, qudit_dim=2, p_ext=0)
    print("Krull Dimension:", res_model_a["krull_dimension"])
    print("Annihilator Generators:", res_model_a["annihilator_generators"])
    print()

if __name__ == "__main__":
    verify()
