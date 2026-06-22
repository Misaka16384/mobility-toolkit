---
name: mt-models
description: "Knowledge base linking models (Layer 1) to their physical properties (Layer 3). Seed standard models, sync discoveries, and run SQL queries over a SQLite registry of translation-invariant stabilizer codes (mobility, GSD, periodicities). Use to look up known models/results or to persist what you compute. No Macaulay2 backend needed."
---

# mt-models — model ↔ physics registry (Layer 1 ↔ Layer 3 store)

A SQLite registry (`mobility_models.db`) that connects **Layer 1** models to their
**Layer 3** properties (mobility class, GSD, periodicities, `is_topological`). Use it to
seed standard models, sync new discoveries from your runs, and query results with SQL.

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
