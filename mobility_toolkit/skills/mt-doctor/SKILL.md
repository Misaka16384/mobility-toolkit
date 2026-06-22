---
name: mt-doctor
description: "Infrastructure check. Diagnose the Macaulay2 backend: report how M2 will be invoked on this platform (native / WSL / Docker / override) and run a live 2+2 smoke test. Run this FIRST whenever a computation skill (mt-homology / mt-mobility / mt-gsd / mt-fusion) errors with a backend failure."
---

# mt-doctor — Macaulay2 backend diagnostic

Reports how Macaulay2 is resolved on this machine and runs a live smoke test. The compute
skills (mt-homology, mt-mobility, mt-gsd, mt-fusion) all need a working M2 backend — when
one of them errors, run this first to see whether the backend is the problem.

Resolution order: `MOBILITY_M2_CMD` → `MOBILITY_M2_DOCKER_IMAGE` → native `M2` on PATH →
WSL (`MOBILITY_M2_WSL_DISTRO`, default `Ubuntu`).

## Input
```json
{ "smoke": true }
```
Optional — `smoke` (default `true`) runs a live `2+2` check. Empty input (`{}`) is fine.

## Output
```json
{ "status": "success",
  "platform": "win32", "strategy": "wsl", "command": ["wsl", "-d", "Ubuntu", "M2", "..."],
  "available": true,
  "smoke_test": { "ran": true, "ok": true, "exit_code": 0, "stderr": "" } }
```

## Example
```bash
echo '{}' | python scripts/mt-doctor.py
```
If `available` is false or `smoke_test.ok` is false, install/repair Macaulay2 (see the
README "Macaulay2 backend" section) or set `MOBILITY_M2_CMD`.
