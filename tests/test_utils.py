import os
import json
import pytest
from mobility_toolkit.utils import (
    PROJECT_ROOT,
    setup_output_dirs,
    log_m2_execution,
    log_python_run,
    save_discovery,
    save_troubleshooting_dump
)
from mobility_toolkit.bridge import run_m2_script
from mobility_toolkit.homology import compute_ext_krull
from mobility_toolkit.grobner import compute_gsd_and_periodicity
from mobility_toolkit.fusion import solve_sset_fusion
from mobility_toolkit.reference_models import TORIC_CODE_2D

@pytest.fixture(autouse=True)
def ensure_dirs():
    """Fixture to ensure the output directories exist before each test."""
    setup_output_dirs()

def test_setup_output_dirs():
    """Verify that setup_output_dirs creates all required folders."""
    output_dir = os.path.join(PROJECT_ROOT, "output")
    dirs = [
        output_dir,
        os.path.join(output_dir, "logs"),
        os.path.join(output_dir, "discoveries"),
        os.path.join(output_dir, "tmp")
    ]
    for d in dirs:
        assert os.path.exists(d)
        assert os.path.isdir(d)

def test_log_m2_execution():
    """Verify that log_m2_execution correctly writes execution details to the log file."""
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "m2_execution.log")
    
    # Delete the log file if it exists to make assertions clean
    if os.path.exists(log_file):
        os.remove(log_file)
        
    script = "test_script_code_123"
    stdout = "test_stdout_output_456"
    stderr = "test_stderr_error_789"
    exit_code = 42
    
    log_m2_execution(script, exit_code, stdout, stderr)
    
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "test_script_code_123" in content
    assert "test_stdout_output_456" in content
    assert "test_stderr_error_789" in content
    assert "Exit Code: 42" in content
    assert "Timestamp:" in content

def test_log_python_run():
    """Verify that log_python_run correctly writes Python function calls to the log file."""
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "python_execution.log")
    
    # Delete the log file if it exists to make assertions clean
    if os.path.exists(log_file):
        os.remove(log_file)
        
    log_python_run("test_module", "test_func", (1, 2), {"a": 3}, "test_result")
    
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "test_module" in content
    assert "test_func" in content
    assert "(1, 2)" in content
    assert "{'a': 3}" in content
    assert "test_result" in content
    assert "Timestamp:" in content

def test_save_discovery_json():
    """Verify that save_discovery saves mathematical discoveries as JSON files."""
    disc_name = "test_discovery_json"
    props = {"metric": "Krull dimension", "value": 3, "valid": True}
    
    # Ensure file does not exist
    dest_file = os.path.join(PROJECT_ROOT, "output", "discoveries", f"{disc_name}.json")
    if os.path.exists(dest_file):
        os.remove(dest_file)
        
    save_discovery(disc_name, props)
    
    assert os.path.exists(dest_file)
    with open(dest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data == props

def test_save_discovery_md():
    """Verify that save_discovery saves mathematical discoveries as markdown files."""
    disc_name = "test_discovery_md.md"
    props = {"MetricName": "Krull dimension", "ValueVal": "3"}
    
    # Ensure file does not exist
    dest_file = os.path.join(PROJECT_ROOT, "output", "discoveries", disc_name)
    if os.path.exists(dest_file):
        os.remove(dest_file)
        
    save_discovery(disc_name, props)
    
    assert os.path.exists(dest_file)
    with open(dest_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "# Discovery: test_discovery_md" in content
    assert "MetricName" in content
    assert "Krull dimension" in content
    assert "ValueVal" in content
    assert "3" in content

def test_save_troubleshooting_dump():
    """Verify that save_troubleshooting_dump saves intermediate scripts to the tmp folder."""
    filename = "test_dump_file.m2"
    content = "R = ZZ/2[x]; x^2 - 1"
    
    dest_file = os.path.join(PROJECT_ROOT, "output", "tmp", filename)
    if os.path.exists(dest_file):
        os.remove(dest_file)
        
    save_troubleshooting_dump(filename, content)
    
    assert os.path.exists(dest_file)
    with open(dest_file, "r", encoding="utf-8") as f:
        read_content = f.read()
        
    assert read_content == content

def test_bridge_integration():
    """Verify that running a script via run_m2_script triggers log and dump creation."""
    # Ensure log file exists or clean it
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "m2_execution.log")
    if os.path.exists(log_file):
        os.remove(log_file)
        
    tmp_dir = os.path.join(PROJECT_ROOT, "output", "tmp")
    # Clean tmp files starting with m2_script
    for filename in os.listdir(tmp_dir):
        if filename.startswith("m2_script"):
            try:
                os.remove(os.path.join(tmp_dir, filename))
            except OSError:
                pass
                
    exit_code, stdout, stderr = run_m2_script("3 + 3")
    
    # Check that it executed successfully
    assert exit_code == 0
    assert "6" in stdout
    
    # Check that the log entry is present
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "3 + 3" in log_content
    
    # Check that a troubleshooting dump file was saved in tmp/
    tmp_files = [f for f in os.listdir(tmp_dir) if f.startswith("m2_script") and f.endswith("_dump.m2")]
    assert len(tmp_files) >= 1
    
    # Check content of the dump file containing the run script
    found_dump = False
    for filename in tmp_files:
        dump_path = os.path.join(tmp_dir, filename)
        try:
            with open(dump_path, "r", encoding="utf-8") as f:
                dump_content = f.read()
            if "3 + 3" in dump_content:
                found_dump = True
                break
        except OSError:
            pass
    assert found_dump, "A troubleshooting dump file containing '3 + 3' should be saved."

def test_homological_integration():
    """Verify that compute_ext_krull triggers Python log and discovery saving."""
    # Clear computations table to prevent cache hits
    from mobility_toolkit.registry import ModelRegistry
    import sqlite3
    registry = ModelRegistry()
    conn = sqlite3.connect(registry.db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM computations")
        conn.commit()
    finally:
        conn.close()

    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "python_execution.log")
    discovery_file = os.path.join(PROJECT_ROOT, "output", "discoveries", "homological_discovery.json")
    
    if os.path.exists(log_file):
        os.remove(log_file)
    if os.path.exists(discovery_file):
        os.remove(discovery_file)
        
    # Toric code stabilizer matrix representation
    # Z1*Z2, X1*X3, etc. represented simple generators
    res = compute_ext_krull(TORIC_CODE_2D, 2)
    
    # Verify results
    assert "krull_dimension" in res
    assert "ext_modules" in res
    
    # Verify discovery was saved
    assert os.path.exists(discovery_file)
    with open(discovery_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["krull_dimension"] == res["krull_dimension"]
    
    # Verify python execution log has PENDING and finished records
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "compute_ext_krull" in log_content
    assert "PENDING" in log_content
    assert str(res["krull_dimension"]) in log_content

def test_grobner_integration():
    """Verify that compute_gsd_and_periodicity triggers Python log and discovery saving."""
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "python_execution.log")
    discovery_file = os.path.join(PROJECT_ROOT, "output", "discoveries", "grobner_discovery.json")
    
    if os.path.exists(log_file):
        os.remove(log_file)
    if os.path.exists(discovery_file):
        os.remove(discovery_file)
        
    # Simple stabilizer matrix for a toric code generator
    stabilizer = [
        ["1 - x", "1 - y", "0", "0"],
        ["0", "0", "1 - y", "1 - x"]
    ]
    
    res = compute_gsd_and_periodicity(stabilizer, Lx=2, Ly=2, qudit_dim=2)
    
    # Verify results
    assert "gsd" in res
    assert "periodicities" in res
    
    # Verify discovery was saved
    assert os.path.exists(discovery_file)
    with open(discovery_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["gsd"] == res["gsd"]
    
    # Verify python execution log
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "compute_gsd_and_periodicity" in log_content
    assert "PENDING" in log_content
    assert str(res["gsd"]) in log_content

def test_hoca_integration():
    """Verify that solve_sset_fusion triggers Python log and discovery saving."""
    log_file = os.path.join(PROJECT_ROOT, "output", "logs", "python_execution.log")
    discovery_file = os.path.join(PROJECT_ROOT, "output", "discoveries", "hoca_discovery.json")
    
    if os.path.exists(log_file):
        os.remove(log_file)
    if os.path.exists(discovery_file):
        os.remove(discovery_file)
        
    # Standard polynomial values
    poly_f = "x + y + 1"
    poly_g = "x + 1"
    
    res = solve_sset_fusion(poly_f, poly_g)
    
    # Verify results
    assert "characteristic_polynomial" in res
    
    # Verify discovery was saved
    assert os.path.exists(discovery_file)
    with open(discovery_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["characteristic_polynomial"] == res["characteristic_polynomial"]
    
    # Verify python execution log
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "solve_sset_fusion" in log_content
    assert "PENDING" in log_content
    assert res["characteristic_polynomial"] in log_content
