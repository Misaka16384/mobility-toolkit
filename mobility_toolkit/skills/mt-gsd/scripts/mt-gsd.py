import sys
import json
from mobility_toolkit.grobner import compute_gsd_and_periodicity

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        result = compute_gsd_and_periodicity(
            data.get("stabilizer_matrix"), data.get("Lx"), data.get("Ly"), data.get("qudit_dim")
        )
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
