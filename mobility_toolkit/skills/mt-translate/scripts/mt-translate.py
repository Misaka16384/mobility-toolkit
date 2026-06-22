import sys
import json
from mobility_toolkit.translate import translate_to_algebra

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        result = translate_to_algebra(data.get("stabilizer_matrix"), data.get("qudit_dim"))
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
