import sys
import json
from mobility_toolkit.fusion import analyze_fusion_interference

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.stdin.read())
        matrix_input = input_data.get("stabilizer_matrix")
        q_dim = input_data.get("qudit_dim")
        shifts_input = input_data.get("shifts")
        
        result = analyze_fusion_interference(matrix_input, q_dim, shifts_input)
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
