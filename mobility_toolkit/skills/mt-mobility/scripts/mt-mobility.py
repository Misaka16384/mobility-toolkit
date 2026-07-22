import sys
import json
from mobility_toolkit.mobility import compute_true_mobility_dimension

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        result = compute_true_mobility_dimension(
            data.get("generators"), data.get("qudit_dim"), data.get("all_vars")
        )
        # Preserve structured inconclusive/trivial outcomes from the core.
        result.setdefault("status", "success")
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
