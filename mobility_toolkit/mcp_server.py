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
    compute_translation_lattice,
    compute_gsd_and_periodicity,
    analyze_fusion_interference,
    solve_sset_fusion,
    analyze_annihilator_fusion,
    search_koszul_models
)
from mobility_toolkit.boundary_gauge.boundary.pipeline import (
    run_algorithm_1_boundary_ops_2d,
    run_algorithm_1_boundary_ops_3d,
)

mcp = FastMCP("mobility-toolkit")

@mcp.tool()
def compute_homology(
    stabilizer_matrix: List[List[str]],
    qudit_dim: int,
    p_ext: int = 0,
    prime_bypass: bool = False,
    spatial_dim: Optional[int] = None,
    validate_stabilizer: bool = True,
    saturated: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Compute the homology Ext modules, Krull dimension, and annihilator generators.
    
    Args:
        stabilizer_matrix: Pauli stabilizer matrix as a list of lists of strings.
        qudit_dim: Qudit dimension (characteristic N).
        p_ext: Ext module index (0 for point, 1 for loop excitations).
        prime_bypass: Compatibility option; composite-coefficient Ext is not implemented.
        spatial_dim: Ambient lattice dimension, including axes absent from coefficients.
        validate_stabilizer: Verify even Pauli rank and sigma^dagger lambda sigma = 0.
        saturated: Optional caller-supplied saturation hypothesis for Proposition 25.
    """
    return compute_ext_krull(
        stabilizer_matrix,
        qudit_dim,
        p_ext=p_ext,
        prime_bypass=prime_bypass,
        spatial_dim=spatial_dim,
        validate_stabilizer=validate_stabilizer,
        saturated=saturated,
    )

@mcp.tool()
def compute_mobility(generators: List[str], qudit_dim: int, variables: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Compute the exact translation lattice of a Laurent-binomial annihilator.
    
    Args:
        generators: List of generator polynomials.
        qudit_dim: Qudit dimension.
        variables: Optional variables fixing the ambient Laurent ring.  Inverse
            pairs such as x/t are treated as one spatial axis.
    """
    return compute_translation_lattice(generators, qudit_dim, variables)

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

@mcp.tool()
def compute_boundary_gauge(
    dim: int,
    Lx: int,
    Ly: int,
    q: int,
    d: int,
    wx: int,
    wy: int,
    stabilizer_generators: List[List[Any]],
    qudit_positions: List[List[float]],
    boundary: str = "bottom",
    Lz: Optional[int] = None,
    wz: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute boundary gauge operators using Algorithm 1 pipeline.
    
    Args:
        dim: Spatial dimension (2 or 3).
        Lx: System size Lx.
        Ly: System size Ly.
        q: Number of qudits per site.
        d: Qudit dimension.
        wx: Patch width wx.
        wy: Patch width wy.
        stabilizer_generators: List of lists of generator terms.
        qudit_positions: List of lists of floats representing qudit positions.
        boundary: Boundary selection ('bottom' or 'top').
        Lz: System size Lz (required for 3D).
        wz: Patch width wz (required for 3D).
    """
    if dim == 2:
        bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_2d(
            Lx=Lx,
            Ly=Ly,
            q=q,
            d=d,
            wx=wx,
            wy=wy,
            stabilizer_generators=stabilizer_generators,
            qudit_positions=qudit_positions,
            boundary=boundary,
        )
    elif dim == 3:
        if Lz is None or wz is None:
            raise ValueError("Lz and wz are required for 3D")
        bulk_stabilizers, boundary_ops, S_mat = run_algorithm_1_boundary_ops_3d(
            Lx=Lx,
            Ly=Ly,
            Lz=Lz,
            q=q,
            d=d,
            wx=wx,
            wy=wy,
            wz=wz,
            stabilizer_generators=stabilizer_generators,
            qudit_positions=qudit_positions,
            boundary=boundary,
        )
    else:
        raise ValueError("dim must be 2 or 3")
        
    return {
        "bulk_stabilizers": [{str(k): list(v) for k, v in stab.items()} for stab in bulk_stabilizers],
        "boundary_ops": boundary_ops.tolist(),
        "S_mat": S_mat.tolist()
    }

if __name__ == "__main__":
    mcp.run()
