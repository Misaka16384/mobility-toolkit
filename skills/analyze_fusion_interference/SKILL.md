---
name: analyze_fusion_interference
description: "Computes point excitation annihilator ideal from Ext^1 module using M2, and checks if shift vectors cause dimension drops after quotienting and saturating."
commands:
  analyze: "Analyze fusion interference and dimension drops for a stabilizer matrix under translation shifts."
---

# Analyze Fusion Interference Skill (analyze_fusion_interference)

This skill determines whether specific translation shift vectors cause a dimension drop in the point excitation annihilated variety. A dimension drop indicates that the composite excitations at those relative shifts are more constrained (less mobile or undergo rigid-to-flexible fusion).

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
    "shifts": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "integer"
        }
      }
    }
  },
  "required": ["stabilizer_matrix", "qudit_dim", "shifts"]
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
    "annihilator_dimension": {
      "type": "integer"
    },
    "dimension_drop": {
      "type": "boolean"
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
from analyze_fusion_interference.scripts.analyze_fusion_interference import analyze_fusion_interference

result = analyze_fusion_interference(
    [["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]],
    2,
    [[1, -1, 0]]
)
# returns {"annihilator_dimension": 0, "dimension_drop": false}
```

## CLI Usage
```bash
python scripts/analyze_fusion_interference.py < input.json
```
