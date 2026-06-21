import sys
import json
from mobility_toolkit.translate import translate_to_algebra

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.stdin.read())
        matrix_input = input_data.get("stabilizer_matrix")
        q_dim = input_data.get("qudit_dim")
        
        result = translate_to_algebra(matrix_input, q_dim)
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
