import sys
import json
from mobility_toolkit.registry import query_vector_db

if __name__ == "__main__":
    try:
        input_data = json.loads(sys.stdin.read())
        action_val = input_data.get("action")
        params_val = input_data.get("params", {})
        
        result = query_vector_db(action_val, params_val)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
