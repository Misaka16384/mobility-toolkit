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

def map_variables_to_legacy(elem: str) -> str:
    elem = re.sub(r'\bx1\b', 'x', elem)
    elem = re.sub(r'\bt1\b', 't', elem)
    elem = re.sub(r'\bx2\b', 'y', elem)
    elem = re.sub(r'\bt2\b', 'u', elem)
    elem = re.sub(r'\bx3\b', 'z', elem)
    elem = re.sub(r'\bt3\b', 'w', elem)
    return elem

def parse_monomial(term_str: str) -> tuple[int, Dict[int, int]]:
    term_str = term_str.strip().replace(" ", "").replace("**", "^")
    if not term_str:
        return 0, {}
    
    coef_match = re.match(r'^([+-]?\d+)(?:\*(.*))?$', term_str)
    if coef_match:
        coef = int(coef_match.group(1))
        rest = coef_match.group(2) or ""
    else:
        sign = 1
        if term_str.startswith("-"):
            sign = -1
            term_str = term_str[1:]
        elif term_str.startswith("+"):
            term_str = term_str[1:]
        coef = sign
        rest = term_str

    net_exps = {}
    if rest:
        factors = rest.split("*")
        for factor in factors:
            factor = factor.strip()
            if not factor:
                continue
            m = re.match(r'^([xt])(\d+)(?:\^([+-]?\d+))?$', factor)
            if not m:
                if factor.isdigit():
                    coef *= int(factor)
                    continue
                raise ValueError(f"Invalid factor: {factor}")
            var_type = m.group(1)
            var_idx = int(m.group(2))
            exp = int(m.group(3)) if m.group(3) else 1
            if var_type == 'x':
                net_exps[var_idx] = net_exps.get(var_idx, 0) + exp
            else:
                net_exps[var_idx] = net_exps.get(var_idx, 0) - exp
    return coef, net_exps

def normalize_laurent_poly(poly_str: str) -> str:
    """
    Clears denominators and common monomial factors from a Laurent polynomial string.
    e.g. "x1^2*t2 - x2 + 1" -> "x1^2 - x2^2 + x2" (using t2 = x2^-1)
    """
    is_legacy = bool(re.search(r'\b[xyztuw]\b', poly_str))
    poly_trans = map_variables_to_unified(poly_str)
    
    # Split by + and - keeping signs
    terms = re.findall(r'[+-]?[^+-]+', poly_trans)
    
    terms_data = []
    max_idx = 0
    for t in terms:
        coef, net_exps = parse_monomial(t)
        if coef != 0:
            terms_data.append((coef, net_exps))
            if net_exps:
                max_idx = max(max_idx, max(net_exps.keys()))
                
    if not terms_data:
        return "0"
        
    # Find minimum net exponent for each variable
    min_exps = {}
    for i in range(1, max_idx + 1):
        min_exps[i] = min(net_exps.get(i, 0) for _, net_exps in terms_data)
        
    # Adjust exponents
    new_terms = []
    for idx, (coef, net_exps) in enumerate(terms_data):
        term_parts = []
        abs_coef = abs(coef)
        has_vars = False
        for i in range(1, max_idx + 1):
            new_exp = net_exps.get(i, 0) - min_exps[i]
            if new_exp > 0:
                has_vars = True
                term_parts.append(f"x{i}^{new_exp}" if new_exp > 1 else f"x{i}")
                
        if abs_coef != 1 or not has_vars:
            term_parts.insert(0, str(abs_coef))
            
        term_str = "*".join(term_parts)
        if coef < 0:
            new_terms.append(f"- {term_str}")
        else:
            if idx == 0:
                new_terms.append(term_str)
            else:
                new_terms.append(f"+ {term_str}")
                
    res = " ".join(new_terms)
    res = re.sub(r'\s+', ' ', res).strip()
    
    if is_legacy:
        res = map_variables_to_legacy(res)
    return res


