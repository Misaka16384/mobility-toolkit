import re
from typing import List, Dict, Any
from mobility_toolkit.utils import verify_qudit_dim

def translate_stabilizers(stabilizer_matrix: List[List[str]], qudit_dim: int, prime_bypass: bool = False) -> Dict[str, Any]:
    # 1. Validate stabilizer_matrix
    if not isinstance(stabilizer_matrix, list) or not stabilizer_matrix:
        raise ValueError("stabilizer_matrix must be a non-empty list of lists of strings")
    
    row_len = None
    for row in stabilizer_matrix:
        if not isinstance(row, list) or not row:
            raise ValueError("stabilizer_matrix rows must be non-empty lists")
        if row_len is None:
            row_len = len(row)
        elif len(row) != row_len:
            raise ValueError("All rows of stabilizer_matrix must have the same length")
        for elem in row:
            if not isinstance(elem, str):
                raise ValueError("All elements of stabilizer_matrix must be strings")

    # 2. Validate qudit_dim using verify_qudit_dim
    # This checks that qudit_dim is an integer >= 2, and prime unless prime_bypass is True.
    # It raises TypeError for non-int, ValueError for non-prime or < 2.
    verify_qudit_dim(qudit_dim, prime_bypass=prime_bypass)
    
    # Check max limit 100000
    if qudit_dim > 100000:
        raise ValueError("qudit_dim must be <= 100000")

    # 3. Regex validation on every element to prevent command injection
    pattern = r"^[a-zA-Z0-9_\-\+\*\/\^\(\)\s\.]+$"
    for row in stabilizer_matrix:
        for elem in row:
            if not re.match(pattern, elem):
                raise ValueError(f"Invalid character or potential command injection in: {elem}")

    # 4. Scan elements for variables and validate them
    for row in stabilizer_matrix:
        for elem in row:
            words = re.findall(r'\w+', elem)
            for word in words:
                if any(c.isalpha() for c in word):
                    if any(c.isupper() for c in word):
                        raise ValueError(f"Uppercase variables are not allowed: {word}")
                    if len(word) > 1 or '_' in word or any(c.isdigit() for c in word):
                        raise ValueError(f"Multi-character, subscripted, or invalid variables are not allowed: {word}")
                    if word not in {'x', 'y', 'z', 't', 'u', 'w'}:
                        raise ValueError(f"Only single-character lowercase variables x, y, z, t, u, w are allowed: {word}")

    # 5. Translate negative variables
    def repl_x(match):
        power = int(match.group(1))
        return 't' if power == 1 else f't^{power}'

    def repl_y(match):
        power = int(match.group(1))
        return 'u' if power == 1 else f'u^{power}'

    def repl_z(match):
        power = int(match.group(1))
        return 'w' if power == 1 else f'w^{power}'

    translated_matrix = []
    active_vars = set()
    for row in stabilizer_matrix:
        translated_row = []
        for elem in row:
            elem_trans = re.sub(r'\bx\s*(?:\^|\*\*)\s*-\s*(\d+)\b', repl_x, elem)
            elem_trans = re.sub(r'\by\s*(?:\^|\*\*)\s*-\s*(\d+)\b', repl_y, elem_trans)
            elem_trans = re.sub(r'\bz\s*(?:\^|\*\*)\s*-\s*(\d+)\b', repl_z, elem_trans)
            elem_trans = elem_trans.replace('**', '^')
            translated_row.append(elem_trans)
            
            # Find any active variables in the translated element
            words = re.findall(r'\w+', elem_trans)
            for word in words:
                if word in {'x', 'y', 'z', 't', 'u', 'w'}:
                    active_vars.add(word)
        translated_matrix.append(translated_row)

    # 6. Determine variables list and relations based on active variables
    variables_list = []
    relations = []
    
    if 'z' in active_vars or 'w' in active_vars:
        variables_list = ['x', 't', 'y', 'u', 'z', 'w']
        relations = ['x*t - 1', 'y*u - 1', 'z*w - 1']
    elif 'y' in active_vars or 'u' in active_vars:
        variables_list = ['x', 't', 'y', 'u']
        relations = ['x*t - 1', 'y*u - 1']
    else:
        # Default to x, t
        variables_list = ['x', 't']
        relations = ['x*t - 1']

    # quotient ring definition
    ring_definition = f"R = ZZ/{qudit_dim}[{', '.join(variables_list)}] / ideal({', '.join(relations)})"

    # Transpose matrix for M2 representation
    num_rows = len(translated_matrix)
    num_cols = len(translated_matrix[0])
    transposed = [[translated_matrix[r][c] for r in range(num_rows)] for c in range(num_cols)]

    m2_matrix_rows = []
    for r in transposed:
        m2_matrix_rows.append("{" + ", ".join(r) + "}")
    matrix_definition = "{" + ", ".join(m2_matrix_rows) + "}"

    return {
        "variables": variables_list,
        "ring_definition": ring_definition,
        "matrix_definition": matrix_definition
    }

def translate_to_algebra(stabilizer_matrix: List[List[str]], qudit_dim: int) -> Dict[str, Any]:
    return translate_stabilizers(stabilizer_matrix, qudit_dim, prime_bypass=False)
