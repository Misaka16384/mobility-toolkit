---
name: compute_homology_and_mobility
description: "Computes the Ext^{p_ext+1}(PL, R^1) module and its Krull dimension using Macaulay2 to determine excitation mobility properties."
commands:
  compute: "Compute homology and mobility properties for a stabilizer matrix."
---

# Compute Homology and Mobility Skill (compute_homology_and_mobility)

This skill calculates the Ext modules and their corresponding Krull dimensions to identify the mobility classification of excitation types in translation-invariant stabilizer codes.

## Input Schema
```json
{
  "type": "object",
  "properties": {
    "stabilizer_matrix": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "string"
        }
      }
    },
    "qudit_dim": {
      "type": "integer"
    },
    "p_ext": {
      "type": "integer",
      "minimum": 0
    }
  },
  "required": ["stabilizer_matrix", "qudit_dim", "p_ext"]
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
    "krull_dimension": {
      "type": "integer"
    },
    "ext_modules": {
      "type": "array",
      "items": {
        "type": "string"
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
from compute_homology_and_mobility.scripts.compute_homology_and_mobility import compute_homology_and_mobility

result = compute_homology_and_mobility([["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]], 2, 0)
# returns {"krull_dimension": 0, "ext_modules": ["cokernel | t+1 x+1 |"]}
```

## CLI Usage
```bash
python scripts/compute_homology_and_mobility.py < input.json
```
