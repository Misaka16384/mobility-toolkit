---
name: translate_to_algebra
description: "Parses stabilizer matrix elements (including negative variables) and translates them to Laurent ring variables and Macaulay2 definitions."
commands:
  translate: "Translate a stabilizer matrix to Laurent ring variables and Macaulay2 representations."
---

# Translate to Algebra Skill (translate_to_algebra)

This skill provides functionality to parse stabilizer matrices in physical models (with potential negative power variables) and translate them into ring and matrix variables for algebraic calculations.

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
    }
  },
  "required": ["stabilizer_matrix", "qudit_dim"]
}
```

> [!IMPORTANT]
> **Parenthesis Constraint**: The stabilizer matrix elements must NOT contain parentheses `(` or `)` due to strict character validation. All input polynomials must be fully expanded (e.g. use `y + z + x*y + x*z` instead of `(1+x)*(y+z)`).

## Output Schema
```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error"]
    },
    "variables": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "ring_definition": {
      "type": "string"
    },
    "matrix_definition": {
      "type": "string"
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
from translate_to_algebra.scripts.translate_to_algebra import translate_to_algebra

result = translate_to_algebra([["1 - x", "1 - y", "0", "0"], ["0", "0", "1 - y", "1 - x"]], 2)
# returns {"variables": ["x", "t", "y", "u"], "ring_definition": "...", "matrix_definition": "..."}
```

## CLI Usage
```bash
python scripts/translate_to_algebra.py < input.json
```
