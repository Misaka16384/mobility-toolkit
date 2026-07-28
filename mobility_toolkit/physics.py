"""Theorem-safe interpretation of charge-module Krull dimensions.

Ruba--Yang prove a mobility criterion for the *whole local point-charge
module* ``Q^0``: it has Krull dimension zero if and only if every local point
charge is mobile in all non-compact lattice directions.  This result does not
identify planons, lineons, or individual fractons from a positive Krull
dimension, and the analogous interpretation for ``Q^p`` with ``p > 0`` is
conjectural in the paper.

This module deliberately reports only those conclusions.  In particular,
Krull dimension alone neither proves topological order nor determines a number
of free directions.
"""
from typing import Any, Dict, Mapping, Optional


_TOPOLOGICAL_ASSUMPTIONS = ("lagrangian", "saturated", "no_ssb")


def _normalize_assumptions(
    assumptions: Optional[Mapping[str, bool]],
) -> Dict[str, Optional[bool]]:
    if assumptions is None:
        assumptions = {}
    if not isinstance(assumptions, Mapping):
        raise TypeError("assumptions must be a mapping or None")

    normalized: Dict[str, Optional[bool]] = {}
    for name in _TOPOLOGICAL_ASSUMPTIONS:
        value = assumptions.get(name)
        if value is not None and not isinstance(value, bool):
            raise TypeError(f"assumptions['{name}'] must be a bool when provided")
        normalized[name] = value
    return normalized


def classify_mobility(
    krull_dim: int,
    spatial_dim: int = 3,
    charge_degree: int = 0,
    assumptions: Optional[Mapping[str, bool]] = None,
    *,
    p_ext: Optional[int] = None,
) -> Dict[str, Any]:
    """Interpret a charge-module Krull dimension without exceeding the theorem.

    Args:
        krull_dim: Krull dimension of ``Q^charge_degree``.  A negative value
            denotes the zero module under the toolkit's convention.
        spatial_dim: Number of non-compact lattice directions.  Retained for
            context; it is not subtracted from ``krull_dim``.
        charge_degree: Charge-module degree ``p``.  The proven mobility theorem
            applies only to ``p=0``.
        assumptions: Optional explicit physical assumptions.  Only when
            ``lagrangian``, ``saturated``, and ``no_ssb`` are all true may the
            result expose an assumption-qualified topological-order label.
        p_ext: Keyword alias for ``charge_degree``.

    Returns:
        A theorem-scoped conclusion together with its evidence and assumptions.
        Compatibility fields which previously over-classified mobility are kept
        but are ``None`` whenever the theorem does not determine them.
    """
    if isinstance(krull_dim, bool) or not isinstance(krull_dim, int):
        raise TypeError("krull_dim must be an integer")
    if isinstance(spatial_dim, bool) or not isinstance(spatial_dim, int) or spatial_dim < 1:
        raise ValueError("spatial_dim must be a positive integer")
    if isinstance(charge_degree, bool) or not isinstance(charge_degree, int) or charge_degree < 0:
        raise ValueError("charge_degree must be a non-negative integer")
    if p_ext is not None:
        if isinstance(p_ext, bool) or not isinstance(p_ext, int) or p_ext < 0:
            raise ValueError("p_ext must be a non-negative integer")
        if charge_degree != 0 and charge_degree != p_ext:
            raise ValueError("charge_degree and p_ext disagree")
        charge_degree = p_ext

    normalized_assumptions = _normalize_assumptions(assumptions)
    topology_assumptions_met = all(
        normalized_assumptions[name] is True for name in _TOPOLOGICAL_ASSUMPTIONS
    )

    common: Dict[str, Any] = {
        "krull_dimension": krull_dim,
        "spatial_dim": spatial_dim,
        "charge_degree": charge_degree,
        "assumptions": normalized_assumptions,
        "generic_mobility_dimension": None,
        "is_fracton": None,
        "deprecated_fields": {
            "generic_mobility_dimension": (
                "Krull dimension does not determine a number of free directions."
            ),
            "is_fracton": (
                "A positive module dimension does not classify every charge as a fracton."
            ),
        },
    }

    if krull_dim < 0:
        return {
            **common,
            "charge_module_status": "zero",
            "theorem_status": "not_applicable",
            "mobility_conclusion": "no_charge_in_this_degree",
            "mobility_class": "no-charge-module",
            "topological_order": None,
            "order": None,
            "is_topological": None,
            "evidence": {
                "kind": "algebraic_convention",
                "statement": (
                    "A negative Krull dimension denotes the zero charge module; "
                    "it does not imply that the whole stabilizer code is trivial."
                ),
            },
            "note": (
                f"Q^{charge_degree} is zero.  There is no charge of this degree to "
                "classify, and no phase-level conclusion follows."
            ),
        }

    if charge_degree > 0:
        return {
            **common,
            "charge_module_status": "nonzero",
            "theorem_status": "conjectural",
            "mobility_conclusion": "undetermined_for_higher_charge_degree",
            "mobility_class": "undetermined",
            "topological_order": None,
            "order": None,
            "is_topological": None,
            "evidence": {
                "kind": "scope_limit",
                "statement": (
                    "Ruba--Yang's direct Krull-dimension mobility criterion is proven "
                    "for Q^0; the analogous interpretation for Q^p, p>0, is conjectural."
                ),
            },
            "note": (
                f"Krull dimension {krull_dim} of Q^{charge_degree} does not have a "
                "theorem-proven direct mobility classification."
            ),
        }

    if krull_dim == 0:
        topological_order = True if topology_assumptions_met else None
        return {
            **common,
            "charge_module_status": "nonzero",
            "theorem_status": "proven",
            "mobility_conclusion": "all_local_point_charges_fully_mobile",
            "mobility_class": "fully-mobile-local-point-charges",
            "topological_order": topological_order,
            "order": "topological" if topological_order else None,
            "is_topological": topological_order,
            "evidence": {
                "kind": "theorem",
                "reference": "Ruba--Yang, Corollary 37",
                "statement": (
                    "dim(Q^0)=0 if and only if every local point charge is mobile "
                    "in all non-compact directions."
                ),
            },
            "note": (
                "All local point charges are fully mobile.  Krull dimension alone "
                + (
                    "is accompanied by explicit Lagrangian, saturation, and no-SSB "
                    "assumptions in this call."
                    if topology_assumptions_met
                    else "does not establish topological order; additional Lagrangian, "
                    "saturation, and no-SSB assumptions were not all supplied."
                )
            ),
        }

    return {
        **common,
        "charge_module_status": "nonzero",
        "theorem_status": "proven",
        "mobility_conclusion": "not_all_local_point_charges_fully_mobile",
        "mobility_class": "not-fully-mobile-as-a-whole",
        "topological_order": None,
        "order": None,
        "is_topological": None,
        "evidence": {
            "kind": "theorem_contrapositive",
            "reference": "Ruba--Yang, Corollary 37",
            "statement": (
                "dim(Q^0)>0 means that not every local point charge is mobile in "
                "all non-compact directions."
            ),
        },
        "note": (
            f"Q^0 has Krull dimension {krull_dim}, so not all local point charges "
            "are fully mobile.  The dimension does not determine which charges are "
            "planons, lineons, or fractons, nor a number of free directions."
        ),
    }
