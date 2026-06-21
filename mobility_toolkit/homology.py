import re
import hashlib
from typing import List, Dict, Any
from mobility_toolkit.translate import translate_stabilizers
from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit.utils import log_python_run, save_discovery

def compute_ext_krull(stabilizer_matrix: List[List[str]], qudit_dim: int, p_ext: int = 0, prime_bypass: bool = False) -> Dict[str, Any]:
    # 1. Input validation on p_ext
    if not isinstance(p_ext, int) or isinstance(p_ext, bool) or p_ext < 0:
        raise ValueError("p_ext must be a non-negative integer")

    log_python_run(
        module_name="mobility_toolkit.homology",
        function_name="compute_ext_krull",
        args=(stabilizer_matrix, qudit_dim),
        kwargs={"p_ext": p_ext, "prime_bypass": prime_bypass},
        result="PENDING"
    )

    # Check cache first
    from mobility_toolkit.registry import ModelRegistry
    registry = ModelRegistry()
    cached = registry.get_cached_annihilator(stabilizer_matrix, qudit_dim, p_ext)
    if cached is not None:
        return cached

    # 2. Call translate_stabilizers to get ring and matrix definitions
    translation = translate_stabilizers(stabilizer_matrix, qudit_dim, prime_bypass=prime_bypass)
    ring_def = translation["ring_definition"]
    matrix_def = translation["matrix_definition"]

    # 3. Construct Macaulay2 script
    script_content = f"""{ring_def}
M = matrix(R, {matrix_def})
PL = coker M
E = Ext^{p_ext + 1}(PL, R^1)
I = ann E
print "VALUE:EXT_START"
print E
print "VALUE:DIM_START"
print (dim E)
print "VALUE:ANN_START"
print generators gb I
print toString(generators gb I)
"""

    # 4. Run Macaulay2 script via WSL bridge
    exit_code, stdout, stderr = run_m2_script(script_content)
    if exit_code != 0:
        raise RuntimeError(f"Macaulay2 execution failed: {stderr or stdout}")

    # 5. Parse stdout using value markers
    lines = [line.strip() for line in stdout.split('\n')]
    
    try:
        idx_ext = lines.index("VALUE:EXT_START")
        idx_dim = lines.index("VALUE:DIM_START")
        idx_ann = lines.index("VALUE:ANN_START")
    except ValueError:
        raise RuntimeError(f"Failed to find expected output markers in Macaulay2 stdout: {stdout}")

    # Parse Ext module representation
    ext_lines = []
    for i in range(idx_ext + 1, idx_dim):
        line = lines[i].strip()
        if not re.match(r'^[io]\d+\s*[:=]', line) and line != "":
            ext_lines.append(line)
    ext_str = " ".join(ext_lines).strip()
    ext_modules = [ext_str] if ext_str else ["0"]

    # Parse Krull dimension
    dim_val = None
    for i in range(idx_dim + 1, idx_ann):
        line = lines[i].strip()
        if not re.match(r'^[io]\d+\s*[:=]', line) and line != "":
            dim_val = line
            break
            
    if dim_val is None:
        raise ValueError(f"Could not parse dimension from Macaulay2 output: {stdout}")

    dim_str = dim_val.strip()
    if dim_str == "-1" or "infinity" in dim_str or "inf" in dim_str:
        krull_dim = -1
    else:
        num_match = re.search(r'-?\d+', dim_str)
        if num_match:
            krull_dim = int(num_match.group(0))
        else:
            raise ValueError(f"Could not convert dimension '{dim_str}' to integer.")

    # Parse annihilator generators
    ann_lines = []
    for i in range(idx_ann + 1, len(lines)):
        line = lines[i].strip()
        if not re.match(r'^[io]\d+\s*[:=]', line) and line != "":
            ann_lines.append(line)
            
    ann_content = " ".join(ann_lines).strip()
    
    # Extract generators list
    if "matrix {}" in ann_content or "matrix{}" in ann_content.replace(" ", ""):
        generators_list = []
    else:
        matrix_match = re.search(r'matrix\s*\{\{(.*?)\}\}', ann_content)
        if matrix_match:
            gens_str = matrix_match.group(1)
            generators_list = [g.strip() for g in gens_str.split(',') if g.strip()]
        else:
            # Fallback to double curly braces representation if any
            braces_match = re.search(r'\{\{(.*?)\}\}', ann_content)
            if braces_match:
                gens_str = braces_match.group(1)
                generators_list = [g.strip() for g in gens_str.split(',') if g.strip()]
            else:
                # Fallback to bar representation: | xy x2 |
                bar_matches = re.findall(r'\|(.*?)\|', ann_content)
                if bar_matches:
                    generators_list = []
                    for match in bar_matches:
                        for item in match.split():
                            if item.strip():
                                generators_list.append(item.strip())
                else:
                    generators_list = []

    # 6. Formulate result
    result = {
        "krull_dimension": krull_dim,
        "ext_modules": ext_modules,
        "annihilator_generators": generators_list
    }

    # Cache the result
    registry.cache_annihilator(
        stabilizer_matrix,
        qudit_dim,
        p_ext,
        result["krull_dimension"],
        result["ext_modules"],
        result["annihilator_generators"]
    )

    # 7. Log Python run details
    log_python_run(
        module_name="mobility_toolkit.homology",
        function_name="compute_ext_krull",
        args=(stabilizer_matrix, qudit_dim),
        kwargs={"p_ext": p_ext, "prime_bypass": prime_bypass},
        result=result
    )

    # 8. Save discovery details
    matrix_hash = hashlib.md5(str(stabilizer_matrix).encode('utf-8')).hexdigest()[:8]
    discovery_name = f"discovery_q{qudit_dim}_p{p_ext}_{matrix_hash}"
    save_discovery(discovery_name, result)
    save_discovery("homological_discovery", result)

    return result

def compute_homology_and_mobility(stabilizer_matrix: List[List[str]], qudit_dim: int, p_ext: int) -> Dict[str, Any]:
    return compute_ext_krull(stabilizer_matrix, qudit_dim, p_ext, prime_bypass=False)
