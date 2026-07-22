import sys
import json
from mobility_toolkit.physics import classify_mobility

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        result = classify_mobility(
            data.get("krull_dimension"),
            data.get("spatial_dim", 3),
            p_ext=data.get("p_ext", 0),
            assumptions=data.get("assumptions"),
        )
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
