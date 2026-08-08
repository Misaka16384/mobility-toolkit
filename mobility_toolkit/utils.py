import os
import json
from datetime import datetime
from typing import Any

# Determine the project root directory dynamically relative to this file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def setup_output_dirs() -> None:
    """Ensures output/ and its subdirectories exist."""
    output_dir = os.path.join(PROJECT_ROOT, "output")
    dirs = [
        output_dir,
        os.path.join(output_dir, "logs"),
        os.path.join(output_dir, "discoveries"),
        os.path.join(output_dir, "tmp")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def log_m2_execution(script_content: str, exit_code: int, stdout: str, stderr: str) -> None:
    """Formats and logs Macaulay2 execution details.

    Args:
        script_content (str): The Macaulay2 script content that was run.
        exit_code (int): The process exit code.
        stdout (str): The process stdout output.
        stderr (str): The process stderr output.
    """
    setup_output_dirs()
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "m2_execution.log")
    timestamp = datetime.now().isoformat()
    
    log_entry = (
        f"================================================================================\n"
        f"Timestamp: {timestamp}\n"
        f"Exit Code: {exit_code}\n"
        f"-------------------------------- Script Content --------------------------------\n"
        f"{script_content}\n"
        f"------------------------------------ Stdout ------------------------------------\n"
        f"{stdout}\n"
        f"------------------------------------ Stderr ------------------------------------\n"
        f"{stderr}\n"
        f"================================================================================\n\n"
    )
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def log_python_run(module_name: str, function_name: str, args: tuple, kwargs: dict, result: Any) -> None:
    """Logs the execution details of a solver's python call.

    Args:
        module_name (str): The name of the Python module.
        function_name (str): The name of the Python function.
        args (tuple): Positional arguments passed to the function.
        kwargs (dict): Keyword arguments passed to the function.
        result (Any): The return value of the function (can be None/pending/exceptions).
    """
    setup_output_dirs()
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "python_execution.log")
    timestamp = datetime.now().isoformat()
    
    # Format arguments and result safely for logging
    try:
        args_str = str(args)
    except Exception as e:
        args_str = f"<Unserializable args: {e}>"
        
    try:
        kwargs_str = str(kwargs)
    except Exception as e:
        kwargs_str = f"<Unserializable kwargs: {e}>"
        
    try:
        result_str = str(result)
    except Exception as e:
        result_str = f"<Unserializable result: {e}>"

    log_entry = (
        f"--------------------------------------------------------------------------------\n"
        f"Timestamp: {timestamp}\n"
        f"Module: {module_name}\n"
        f"Function: {function_name}\n"
        f"Args: {args_str}\n"
        f"Kwargs: {kwargs_str}\n"
        f"Result: {result_str}\n"
        f"--------------------------------------------------------------------------------\n\n"
    )
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

def save_discovery(discovery_name: str, properties: dict) -> None:
    """Writes mathematical properties discovered during the solver runs.

    Args:
        discovery_name (str): Name of the discovery (e.g., "toric_code_ext").
        properties (dict): Dictionary containing the discovered properties.
    """
    setup_output_dirs()
    safe_name = os.path.basename(discovery_name)
    
    if safe_name.endswith(".md"):
        file_path = os.path.join(PROJECT_ROOT, "output", "discoveries", safe_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Discovery: {safe_name[:-3]}\n\n")
            for k, v in properties.items():
                f.write(f"## {k}\n{v}\n\n")
    else:
        if not safe_name.endswith(".json"):
            safe_name += ".json"
        file_path = os.path.join(PROJECT_ROOT, "output", "discoveries", safe_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(properties, f, indent=4, ensure_ascii=False)

def save_troubleshooting_dump(filename: str, content: str) -> None:
    """Saves raw intermediate M2 script code or matrix dumps.

    Args:
        filename (str): Filename to save under output/tmp/ (e.g. "m2_script_xyz.m2").
        content (str): The script or dump content.
    """
    setup_output_dirs()
    safe_name = os.path.basename(filename)
    file_path = os.path.join(PROJECT_ROOT, "output", "tmp", safe_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def is_prime(n: int) -> bool:
    """Helper function to check if a number is prime."""
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    # ⚡ Bolt: Fast prime check skipping multiples of 2 and 3
    for i in range(5, int(n ** 0.5) + 1, 6):
        if n % i == 0 or n % (i + 2) == 0:
            return False
    return True

def verify_modulus(modulus: int) -> None:
    """Validate an arbitrary finite cyclic modulus."""

    if not isinstance(modulus, int) or isinstance(modulus, bool):
        raise TypeError("modulus must be an integer")
    if modulus < 2:
        raise ValueError("modulus must be >= 2")


def verify_qudit_dim(qudit_dim: int) -> None:
    """Validate the uniform-prime coefficient domain used by Ext routines."""

    verify_modulus(qudit_dim)
    if not is_prime(qudit_dim):
        raise ValueError("qudit_dim must be prime")
