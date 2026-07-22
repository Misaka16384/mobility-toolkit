---
name: mt-models
description: "Use when you need to seed, query, or sync the SQLite registry of stabilizer models, literature metadata, computed invariants, GSD, and periodicities."
---

# mt-models — model and invariant registry

A SQLite registry (`mobility_models.db`) for models, literature-backed metadata,
and computed invariants. Seed values are reference metadata, not a proof that
Krull dimension alone establishes a phase label.

The X-Cube seed is the full `6 x 3` map of Ruba--Yang Eq. (98): `d0=1` and
`d1=-1` (indeed `Q^i=0` for every `i>0`). Homology cache entries are isolated by
ambient dimension, validation mode, matrix convention, and invariant version,
so legacy raw-cokernel results cannot satisfy the corrected charge-module key.

## Actions

| `action` | Effect |
|---|---|
| `init` | Create the database schema |
| `seed` | Insert the standard reference models (toric, X-Cube, Chamon, WCF, DCY, …) |
| `sync` | Persist discoveries produced by other skills/runs |
| `query` | Run a read-only SQL query (pass it in `params.query`) |

## Input
```json
{ "action": "query", "params": { "query": "SELECT name, gsd_val FROM models WHERE qudit_dim = 12" } }
```

## Output
```json
{ "status": "success",
  "results": [ {"name": "WCF Code", "gsd_val": 144}, {"name": "DCY Code", "gsd_val": 104976} ] }
```

## Examples
```bash
echo '{"action": "init"}'  | python scripts/mt-models.py
echo '{"action": "seed"}'  | python scripts/mt-models.py
echo '{"action": "query", "params": {"query": "SELECT name, gsd_val FROM models WHERE qudit_dim=12"}}' \
  | python scripts/mt-models.py
```
