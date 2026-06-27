import sys
import os

# Add workspace to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research_symmetry.general_restricted_annihilator import extract_restricted_annihilator

if __name__ == "__main__":
    print("=================== STUDYING C_v EXCITATIONS (GAUGE = C_v) ===================")
    
    # In SSET Model A, what if we study the excitations of the subsystem stabilizer C_v itself?
    # Here, C_v acts as the gauge stabilizer (we want to study its violations).
    # Symmetries (constraints): A_v and B_p (which we enforce to not be violated).
    #
    # SSET Model A generators:
    # A_v: X = [0, 1+t, 1+u], Z = [1+y, 0, 0]
    # B_p: X = [0, 0, 0], Z = [0, 1-y, 1-x]
    # C_v: X = [1, 0, 0], Z = [0, 0, u]
    #
    # Under this partition:
    # SXgauge = C_v's X = [[1, 0, 0]]
    # SZgauge = C_v's Z = [[0, 0, u]]
    # Allowed indices detected: Z_1 (index 4) and X_3 (index 3)
    #
    # SXsym = {A_v, B_p}'s X = [[0, 1+t, 1+u], [0, 0, 0]]
    # SZsym = {A_v, B_p}'s Z = [[1+y, 0, 0], [0, 1-y, 1-x]]
    
    extract_restricted_annihilator(
        "SSET Model A (C_v excitations)",
        dimensions=2,
        SXsym=[["0", "1+t", "1+u"], ["0", "0", "0"]],
        SZsym=[["1+y", "0", "0"], ["0", "1-y", "1-x"]],
        SXgauge=[["1", "0", "0"]],
        SZgauge=[["0", "0", "u"]]
    )
