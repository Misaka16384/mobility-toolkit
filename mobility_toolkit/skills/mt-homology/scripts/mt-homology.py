import sys
import json
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.physics import classify_mobility


if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        matrix = data.get("stabilizer_matrix")
        assumptions = dict(data.get("assumptions") or {})
        if data.get("saturated") is not None:
            if (
                "saturated" in assumptions
                and assumptions["saturated"] != data["saturated"]
            ):
                raise ValueError(
                    "top-level saturated and assumptions.saturated disagree"
                )
            assumptions.setdefault("saturated", data["saturated"])
        result = compute_ext_krull(
            matrix,
            data.get("qudit_dim"),
            data.get("p_ext", 0),
            prime_bypass=data.get("prime_bypass", False),
            spatial_dim=data.get("spatial_dim"),
            validate_stabilizer=data.get("validate_stabilizer", True),
            saturated=data.get("saturated"),
        )
        # Attach only the theorem-safe Layer 3 reading.  The resolved spatial
        # dimension comes from the actual Laurent ring used by homology.
        result.update(classify_mobility(
            result["krull_dimension"],
            result["spatial_dim"],
            p_ext=data.get("p_ext", 0),
            assumptions=assumptions,
        ))
        result["status"] = "success"
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
