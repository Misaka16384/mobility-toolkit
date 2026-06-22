import sys
import json
from mobility_toolkit.fusion import analyze_fusion_interference

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        result = analyze_fusion_interference(
            data.get("stabilizer_matrix"), data.get("qudit_dim"), data.get("shifts")
        )
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
