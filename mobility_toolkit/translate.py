import re
from typing import List, Dict, Any
from mobility_toolkit.utils import verify_qudit_dim

def map_variables_to_unified(elem: str) -> str:
    # 1. Normalize power operator
    elem = elem.replace('**', '^')
    
    # 2. Map legacy negative powers (e.g. x^-2 -> t^2)
    elem = re.sub(r'\bx\s*\^\s*-\s*(\d+)\b', lambda m: 't' if int(m.group(1)) == 1 else f't^{m.group(1)}', elem)
    elem = re.sub(r'\by\s*\^\s*-\s*(\d+)\b', lambda m: 'u' if int(m.group(1)) == 1 else f'u^{m.group(1)}', elem)
    elem = re.sub(r'\bz\s*\^\s*-\s*(\d+)\b', lambda m: 'w' if int(m.group(1)) == 1 else f'w^{m.group(1)}', elem)
    
    # 3. Map unified negative powers (e.g. x1^-2 -> t1^2)
    elem = re.sub(r'\bx(\d+)\s*\^\s*-\s*(\d+)\b', lambda m: f't{m.group(1)}' if int(m.group(2)) == 1 else f't{m.group(1)}^{m.group(2)}', elem)
    
    # 4. Map legacy variables to unified variables at word boundaries
    elem = re.sub(r'\bx\b', 'x1', elem)
    elem = re.sub(r'\bt\b', 't1', elem)
    elem = re.sub(r'\by\b', 'x2', elem)
    elem = re.sub(r'\bu\b', 't2', elem)
    elem = re.sub(r'\bz\b', 'x3', elem)
    elem = re.sub(r'\bw\b', 't3', elem)
    
    return elem

def generate_ring_definition(d: int, qudit_dim: int) -> tuple[List[str], str]:
    variables_list = []
    relations = []
    for i in range(1, d + 1):
        variables_list.extend([f"x{i}", f"t{i}"])
        relations.append(f"x{i}*t{i} - 1")
    ring_definition = f"R = ZZ/{qudit_dim}[{', '.join(variables_list)}] / ideal({', '.join(relations)})"
    return variables_list, ring_definition

def translate_stabilizers(stabilizer_matrix: List[List[str]], qudit_dim: int, prime_bypass: bool = False, spatial_dim: int = None) -> Dict[str, Any]:
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
                    is_legacy = word in {'x', 'y', 'z', 't', 'u', 'w'}
                    is_unified = bool(re.match(r'^(x|t)[1-9]\d*$', word))
                    if not (is_legacy or is_unified):
                        raise ValueError(f"Invalid variable: {word}")

    # 5. Translate negative variables and map legacy to unified
    translated_matrix = []
    for row in stabilizer_matrix:
        translated_row = []
        for elem in row:
            elem_trans = map_variables_to_unified(elem)
            translated_row.append(elem_trans)
        translated_matrix.append(translated_row)

    # 6. Find highest variable index
    d_model = 0
    for row in translated_matrix:
        for elem in row:
            for m in re.finditer(r'\b[xt](\d+)\b', elem):
                d_model = max(d_model, int(m.group(1)))

    # 7. Dynamically promote spatial dimension d
    d = max(d_model, spatial_dim or 0, 1)

    # 8. Generate variables list and relations
    variables_list, ring_definition = generate_ring_definition(d, qudit_dim)

    # Transpose matrix for M2 representation
    num_rows = len(translated_matrix)
    num_cols = len(translated_matrix[0])
    transposed = [[translated_matrix[r][c] for r in range(num_rows)] for c in range(num_cols)]

    m2_matrix_rows = []
    for r in transposed:
        m2_matrix_rows.append("{" + ", ".join(r) + "}")
    matrix_definition = "{" + ", ".join(m2_matrix_rows) + "}"

    # Check if input has unified variables
    has_unified_input = False
    for row in stabilizer_matrix:
        for elem in row:
            if re.search(r'\b[xt][1-9]\d*\b', elem):
                has_unified_input = True
                break

    if not has_unified_input:
        # Map variables list
        legacy_vars = []
        for v in variables_list:
            if v == "x1": legacy_vars.append("x")
            elif v == "t1": legacy_vars.append("t")
            elif v == "x2": legacy_vars.append("y")
            elif v == "t2": legacy_vars.append("u")
            elif v == "x3": legacy_vars.append("z")
            elif v == "t3": legacy_vars.append("w")
            else: legacy_vars.append(v)
        variables_list = legacy_vars

        # Map ring_definition
        ring_definition = re.sub(r'\bx1\b', 'x', ring_definition)
        ring_definition = re.sub(r'\bt1\b', 't', ring_definition)
        ring_definition = re.sub(r'\bx2\b', 'y', ring_definition)
        ring_definition = re.sub(r'\bt2\b', 'u', ring_definition)
        ring_definition = re.sub(r'\bx3\b', 'z', ring_definition)
        ring_definition = re.sub(r'\bt3\b', 'w', ring_definition)

        # Map matrix_definition
        matrix_definition = re.sub(r'\bx1\b', 'x', matrix_definition)
        matrix_definition = re.sub(r'\bt1\b', 't', matrix_definition)
        matrix_definition = re.sub(r'\bx2\b', 'y', matrix_definition)
        matrix_definition = re.sub(r'\bt2\b', 'u', matrix_definition)
        matrix_definition = re.sub(r'\bx3\b', 'z', matrix_definition)
        matrix_definition = re.sub(r'\bt3\b', 'w', matrix_definition)

    return {
        "variables": variables_list,
        "ring_definition": ring_definition,
        "matrix_definition": matrix_definition
    }

def translate_to_algebra(stabilizer_matrix: List[List[str]], qudit_dim: int, spatial_dim: int = None, prime_bypass: bool = False) -> Dict[str, Any]:
    return translate_stabilizers(stabilizer_matrix, qudit_dim, prime_bypass=prime_bypass, spatial_dim=spatial_dim)

