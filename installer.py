import os
import sys
import subprocess
import shutil
import json

def run_cmd(args: list, msg: str) -> bool:
    print(f"\n[Running] {msg}...")
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True)
        print(f"[Success] {msg}")
        if res.stdout.strip():
            print(res.stdout.strip())
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[Warning/Error] Failed: {msg}")
        if hasattr(e, 'stderr') and e.stderr:
            print(e.stderr.strip())
        return False

def register_antigravity_skills(is_local: bool):
    print("\n[Registering] Antigravity/Gemini custom skills...")
    
    if is_local:
        target_dir = os.path.abspath(os.path.join(".", ".agents", "skills"))
    else:
        home = os.path.expanduser("~")
        target_dir = os.path.join(home, ".gemini", "config", "skills")
        
    # Locate skills inside the package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    skills_path = os.path.join(package_dir, "skills")
    
    if not os.path.isdir(skills_path):
        print(f"[Error] Skills source folder not found at: {skills_path}")
        return False

    os.makedirs(target_dir, exist_ok=True)
    
    skills_to_copy = [
        "translate_to_algebra", 
        "compute_homology_and_mobility", 
        "analyze_fusion_interference", 
        "query_vector_db"
    ]
    
    for skill in skills_to_copy:
        src = os.path.join(skills_path, skill)
        dst = os.path.join(target_dir, skill)
        if os.path.isdir(src):
            try:
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"[Success] Copied skill '{skill}' to: {dst}")
            except Exception as e:
                print(f"[Warning] Failed to copy skill '{skill}': {e}")
        else:
            print(f"[Warning] Skill '{skill}' source not found at: {src}")
            
    return True

def register_claude_mcp():
    print("\n[Registering] Claude Code MCP server...")
    claude_bin = shutil.which("claude")
    if not claude_bin:
        print("[Info] 'claude' CLI not found on system. Skipping automatic MCP registration.")
        return False
        
    cmd = [
        "claude", "mcp", "add", "--transport", "stdio", 
        "mobility_toolkit", "--", 
        sys.executable, "-m", "mobility_toolkit.mcp_server"
    ]
    return run_cmd(cmd, "Registering mobility_toolkit MCP server in Claude Code")

def install_skills(is_local: bool):
    print("====================================================")
    print(f"  Mobility Toolkit - {'Local (Project)' if is_local else 'Global'} Agent Skills Installer")
    print("====================================================")
    
    # 1. Register Antigravity skills
    register_antigravity_skills(is_local)
    
    # 2. Register Claude Code MCP
    register_claude_mcp()
    
    print("\n====================================================")
    print("  Installation Completed!")
    print("====================================================")
    print("Verify by running:")
    print("  mobility-toolkit --help")
    print("====================================================")
