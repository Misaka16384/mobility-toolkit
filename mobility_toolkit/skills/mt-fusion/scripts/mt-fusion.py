import sys
import json
from mobility_toolkit.fusion import analyze_fusion_interference, analyze_annihilator_fusion, solve_sset_fusion

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        if "shifts" in data and "stabilizer_matrix" in data:
            result = analyze_fusion_interference(
                data.get("stabilizer_matrix"), data.get("qudit_dim"), data.get("shifts")
            )
        elif "generators" in data:
            result = analyze_annihilator_fusion(
                data.get("generators"), data.get("qudit_dim"), data.get("variables"), data.get("prime_bypass", False)
            )
        elif "poly_f" in data and "poly_g" in data:
            result = solve_sset_fusion(
                data.get("poly_f"), data.get("poly_g"), data.get("qudit_dim", 2), data.get("variables"), data.get("prime_bypass", False)
            )
        else:
            raise ValueError("Invalid input schema: must provide ('stabilizer_matrix' and 'shifts'), 'generators', or ('poly_f' and 'poly_g').")
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
