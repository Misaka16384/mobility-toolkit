import sys

try:
    from fastmcp import FastMCP
except ImportError:
    print("Error: The 'mcp' package with FastMCP is required to run the MCP server.", file=sys.stderr)
    print("Please install it using: pip install mcp[cli]", file=sys.stderr)
    sys.exit(1)

import json
from typing import List, Dict, Any, Optional

from mobility_toolkit import (
    compute_ext_krull,
    compute_true_mobility_dimension,
    compute_gsd_and_periodicity,
    analyze_fusion_interference,
    solve_sset_fusion,
    analyze_annihilator_fusion,
    search_koszul_models
)

mcp = FastMCP("mobility-toolkit")

@mcp.tool()
def compute_homology(stabilizer_matrix: List[List[str]], qudit_dim: int, p_ext: int = 0, prime_bypass: bool = False) -> Dict[str, Any]:
    """
    Compute the homology Ext modules, Krull dimension, and annihilator generators.
    
    Args:
        stabilizer_matrix: Pauli stabilizer matrix as a list of lists of strings.
        qudit_dim: Qudit dimension (characteristic N).
        p_ext: Ext module index (0 for point, 1 for loop excitations).
        prime_bypass: Set to True to bypass prime characteristic checks (e.g. for composite N=12).
    """
    return compute_ext_krull(stabilizer_matrix, qudit_dim, p_ext, prime_bypass)

@mcp.tool()
def compute_mobility(generators: List[str], qudit_dim: int, variables: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compute the physical mobility dimension of a given annihilator ideal.
    
    Args:
        generators: List of generator polynomials.
        qudit_dim: Qudit dimension.
        variables: Optional list of active variables (defaults to x, t, y, u, z, w).
    """
    return compute_true_mobility_dimension(generators, qudit_dim, variables)

@mcp.tool()
def compute_grobner(stabilizer_matrix: List[List[str]], qudit_dim: int, Lx: Optional[int] = None, Ly: Optional[int] = None, L: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Compute the Ground State Degeneracy (GSD) and anyon periodicities on a torus.
    
    Args:
        stabilizer_matrix: Pauli stabilizer matrix.
        qudit_dim: Qudit dimension.
        Lx: Torus size in the X direction (optional).
        Ly: Torus size in the Y direction (optional).
        L: Torus sizes list for arbitrary dimensions (optional).
    """
    return compute_gsd_and_periodicity(stabilizer_matrix, Lx, Ly, qudit_dim, L)

@mcp.tool()
def compute_fusion_interference(stabilizer_matrix: List[List[str]], qudit_dim: int, shifts: List[List[int]]) -> Dict[str, Any]:
    """
    Compute dimension drops of point excitations under relative shift-interferences.
    
    Args:
        stabilizer_matrix: Pauli stabilizer matrix.
        qudit_dim: Qudit dimension.
        shifts: List of relative shift vectors (each is a list of integers).
    """
    return analyze_fusion_interference(stabilizer_matrix, qudit_dim, shifts)

@mcp.tool()
def search_models(qudit_dim: int, target_dim: int, max_trials: int = 100) -> Dict[str, Any]:
    """
    Reverse-search for commuting Koszul stabilizer models matching a target excitation dimension.
    
    Args:
        qudit_dim: Qudit dimension.
        target_dim: Target Krull dimension.
        max_trials: Maximum search iterations.
    """
    return search_koszul_models(qudit_dim, target_dim, max_trials)

@mcp.tool()
def compute_annihilator_fusion(generators: List[str], qudit_dim: int, variables: Optional[List[str]] = None, prime_bypass: bool = False) -> Dict[str, Any]:
    """
    Directly compute SSET-style mobility fusion rules from an annihilator ideal's generators.
    
    Args:
        generators: List of generator polynomials.
        qudit_dim: Qudit dimension.
        variables: Optional list of active variables.
        prime_bypass: Set to True to bypass prime characteristic checks.
    """
    return analyze_annihilator_fusion(generators, qudit_dim, variables, prime_bypass)

if __name__ == "__main__":
    mcp.run()
