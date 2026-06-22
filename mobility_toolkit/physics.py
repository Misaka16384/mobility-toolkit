"""Layer 3 — physical interpretation of algebraic invariants.

Maps the Krull dimension of a charge module (Layer 2) to a mobility class
(Layer 3). The criterion is from *Homological Invariants of Pauli Stabilizer
Codes* (Comm. Math. Phys. 2024) and is validated in ``docs/VALIDATION.md``:

    Krull dimension 0   <=>  mobile excitation (topological order)
    Krull dimension > 0 <=>  restricted mobility (fracton order)

The *generic* number of free directions is ``spatial_dim - krull_dim`` (the
Type-I expectation). For Type-II fractons this overestimates mobility; use
``compute_true_mobility_dimension`` (the ``mt-mobility`` skill) for the exact
value.
"""
from typing import Any, Dict


def classify_mobility(krull_dim: int, spatial_dim: int = 3) -> Dict[str, Any]:
    """Classify an excitation's mobility from the Krull dimension of its charge module.

    Args:
        krull_dim: Krull dimension of ``Ext^{p+1}(coker M, R)`` (e.g. from
            ``compute_ext_krull``). A negative value denotes the zero module.
        spatial_dim: Number of spatial dimensions of the lattice (default 3).

    Returns:
        A dict with the physical reading: ``order`` (topological/fracton/trivial),
        ``mobility_class`` (fully-mobile / planon / lineon / fracton / trivial),
        ``is_topological`` / ``is_fracton`` flags, the generic free-direction count
        ``generic_mobility_dimension``, and an explanatory ``note``.
    """
    if isinstance(krull_dim, bool) or not isinstance(krull_dim, int):
        raise TypeError("krull_dim must be an integer")
    if isinstance(spatial_dim, bool) or not isinstance(spatial_dim, int) or spatial_dim < 1:
        raise ValueError("spatial_dim must be a positive integer")

    if krull_dim < 0:
        return {
            "krull_dimension": krull_dim,
            "spatial_dim": spatial_dim,
            "order": "trivial",
            "is_topological": False,
            "is_fracton": False,
            "mobility_class": "trivial",
            "generic_mobility_dimension": None,
            "note": (
                "Krull dimension < 0: the charge module is zero -- no excitation of "
                "this type (e.g. Ext is the zero module)."
            ),
        }

    if krull_dim == 0:
        return {
            "krull_dimension": 0,
            "spatial_dim": spatial_dim,
            "order": "topological",
            "is_topological": True,
            "is_fracton": False,
            "mobility_class": "fully-mobile (anyon)",
            "generic_mobility_dimension": spatial_dim,
            "note": (
                "Krull dimension 0: fully mobile excitation (topological order / "
                f"deconfined anyon), free in all {spatial_dim} spatial directions."
            ),
        }

    # krull_dim > 0  ->  restricted mobility (fracton order)
    m = max(spatial_dim - krull_dim, 0)
    if m <= 0:
        label = "fracton (immobile)"
    elif m == 1:
        label = "lineon"
    elif m == 2:
        label = "planon"
    else:
        label = f"mobile-{m}d"

    return {
        "krull_dimension": krull_dim,
        "spatial_dim": spatial_dim,
        "order": "fracton",
        "is_topological": False,
        "is_fracton": True,
        "mobility_class": label,
        "generic_mobility_dimension": m,
        "note": (
            f"Krull dimension {krull_dim} > 0: restricted mobility (fracton order). "
            f"The generic (Type-I) number of free directions is "
            f"spatial_dim - krull_dim = {m} (an upper bound). For Type-II fractons "
            "the true mobility is lower -- compute it exactly with the mt-mobility "
            "skill (compute_true_mobility_dimension) on the annihilator generators."
        ),
    }
