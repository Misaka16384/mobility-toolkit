import sys
import json
from mobility_toolkit.homology import compute_homology_and_mobility
from mobility_toolkit.physics import classify_mobility

# spatial axes: a dimension is "present" if its forward OR inverse variable appears.
_AXES = (("x", "t"), ("y", "u"), ("z", "w"))


def _infer_spatial_dim(matrix):
    present = 0
    for pos, inv in _AXES:
        if any(pos in entry or inv in entry for row in matrix for entry in row):
            present += 1
    return max(present, 1)


if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        matrix = data.get("stabilizer_matrix")
        result = compute_homology_and_mobility(
            matrix,
            data.get("qudit_dim"),
            data.get("p_ext", 0),
            prime_bypass=data.get("prime_bypass", False)
        )
        spatial_dim = data.get("spatial_dim") or _infer_spatial_dim(matrix)
        # attach the Layer 3 reading (mobility_class, order, is_fracton, ...)
        result.update(classify_mobility(result["krull_dimension"], spatial_dim))
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
