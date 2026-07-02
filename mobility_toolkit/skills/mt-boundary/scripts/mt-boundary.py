import sys
import json
from mobility_toolkit.boundary_gauge.boundary.pipeline import (
    run_algorithm_1_boundary_ops_2d,
    run_algorithm_1_boundary_ops_3d,
)

if __name__ == "__main__":
    try:
        data = json.loads(sys.stdin.read())
        dim = data.get("dim")
        boundary = data.get("boundary", "bottom")
        Lx = data.get("Lx")
        Ly = data.get("Ly")
        q = data.get("q")
        d = data.get("d")
        wx = data.get("wx")
        wy = data.get("wy")
        stabilizer_generators = data.get("stabilizer_generators")
        qudit_positions = data.get("qudit_positions")
        
        if dim == 2:
            bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_2d(
                Lx=Lx,
                Ly=Ly,
                q=q,
                d=d,
                wx=wx,
                wy=wy,
                stabilizer_generators=stabilizer_generators,
                qudit_positions=qudit_positions,
                boundary=boundary,
            )
        elif dim == 3:
            Lz = data.get("Lz")
            wz = data.get("wz")
            if Lz is None or wz is None:
                raise ValueError("Lz and wz are required for 3D")
            bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_3d(
                Lx=Lx,
                Ly=Ly,
                Lz=Lz,
                q=q,
                d=d,
                wx=wx,
                wy=wy,
                wz=wz,
                stabilizer_generators=stabilizer_generators,
                qudit_positions=qudit_positions,
                boundary=boundary,
            )
        else:
            raise ValueError("dim must be 2 or 3")
            
        result = {
            "status": "success",
            "bulk_stabilizers": [{str(k): list(v) for k, v in stab.items()} for stab in bulk_stabilizers],
            "boundary_ops": boundary_ops.tolist(),
            "S_mat": S_mat.tolist()
        }
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
