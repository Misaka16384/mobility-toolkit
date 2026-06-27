import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mobility_toolkit.homology import compute_ext_krull

if __name__ == "__main__":
    print("=================== XCUBE NATIVE HOMOLOGY ===================")
    
    # True 3D X-cube stabilizer matrix (3 qubits, 3 generators)
    # Generator 1 (Cube): X = [1+t+u+t*u, 1+u+w+u*w, 1+t+w+t*w], Z = [0, 0, 0]
    # Generator 2 (Star 1): X = [0, 0, 0], Z = [1-z, 1-x, 0]
    # Generator 3 (Star 2): X = [0, 0, 0], Z = [0, 1-x, 1-y]
    xcube_matrix = [
        ["1 + t + u + t*u", "1 + u + w + u*w", "1 + t + w + t*w", "0", "0", "0"],
        ["0", "0", "0", "1 - z", "1 - x", "0"],
        ["0", "0", "0", "0", "1 - x", "1 - y"]
    ]
    
    # Compute Ext^1 (point charges, p_ext=0)
    print("Computing homology for point charges (p_ext=0)...")
    res_p0 = compute_ext_krull(xcube_matrix, qudit_dim=2, p_ext=0)
    print("Point Charges:")
    print("  Krull Dimension:", res_p0["krull_dimension"])
    print("  Annihilator Generators:", res_p0["annihilator_generators"])
    print()
    
    # Compute Ext^2 (lineons/fluxes, p_ext=1)
    print("Computing homology for lineons/fluxes (p_ext=1)...")
    res_p1 = compute_ext_krull(xcube_matrix, qudit_dim=2, p_ext=1)
    print("Lineons/Fluxes:")
    print("  Krull Dimension:", res_p1["krull_dimension"])
    print("  Annihilator Generators:", res_p1["annihilator_generators"])
