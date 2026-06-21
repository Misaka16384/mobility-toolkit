---
name: query_vector_db
description: "Manages a SQLite database (mobility_models.db) of topological mobility models, supporting seeding standard models, syncing new discoveries, and executing queries."
commands:
  query: "Query, seed, or sync the mobility models database."
---

# Query Vector Database Skill (query_vector_db)

This skill manages the SQLite database `mobility_models.db` which tracks translation-invariant stabilizer code models, their topological properties, excitation dimensions, GSD, and periodicities.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "enum": ["init", "seed", "sync", "query"]
    },
    "params": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string"
        }
      }
    }
  },
  "required": ["action"]
}
```

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error"]
    },
    "message": {
      "type": "string"
    },
    "results": {
      "type": "array",
      "items": {
        "type": "object"
      }
    },
    "error": {
      "type": "string"
    }
  },
  "required": ["status"]
}
```

## Python Usage
```python
from query_vector_db.scripts.query_vector_db import query_vector_db

# Initialize & Seed standard models
query_vector_db("init")

# Sync discoveries
query_vector_db("sync")

# Run query
res = query_vector_db("query", {"query": "SELECT name, gsd_val FROM models WHERE qudit_dim = 12"})
# returns {"status": "success", "results": [{"name": "WCF Code", "gsd_val": 144}, {"name": "DCY Code", "gsd_val": 104976}]}
```

## CLI Usage
```bash
python scripts/query_vector_db.py < input.json
```
