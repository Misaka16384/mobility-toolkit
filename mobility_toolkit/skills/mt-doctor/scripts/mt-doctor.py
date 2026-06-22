import sys
import json
from mobility_toolkit.engine import describe_m2_backend, run_macaulay2

if __name__ == "__main__":
    try:
        raw = sys.stdin.read().strip()
        data = json.loads(raw) if raw else {}
        info = describe_m2_backend()
        if data.get("smoke", True) and info["available"]:
            res = run_macaulay2("2+2", timeout_seconds=20.0)
            info["smoke_test"] = {
                "ran": True,
                "ok": res["exit_code"] == 0 and "4" in res["stdout"],
                "exit_code": res["exit_code"],
                "stderr": res["stderr"].strip()[:300],
            }
        else:
            info["smoke_test"] = {"ran": False, "ok": None}
        info["status"] = "success" if info["available"] else "error"
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {str(e)}"}))
        sys.exit(1)
