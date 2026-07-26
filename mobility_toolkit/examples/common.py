"""Shared helpers for example and figure-export scripts."""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

os.environ.setdefault("MPMATH_NOGMPY", "1")
os.environ.setdefault("SYMPY_GROUND_TYPES", "python")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

NOTEBOOK_NAME = "integrated_all_boundary_gauge_operator_generators_snf_weight_sorted_physbulk3d.ipynb"
OUTPUT_DIR = PROJECT_ROOT / "output" / "figures"
INDIVIDUAL_DIR = OUTPUT_DIR / "individual"
SHEET_DIR = OUTPUT_DIR / "sheets"
MANIFEST = OUTPUT_DIR / "manifest.csv"
FIGURE_MANIFEST_FIELDS = [
    "case_index",
    "cell_index",
    "case_title",
    "figure_index",
    "figure_title",
    "path",
]

CODE_ORDER = OrderedDict(
    [
        ("2d_toric_code", "2D Toric Code"),
        ("fish_toric_code", "Fish Toric Code"),
        ("z4_toric_code", "Z4 Toric Code"),
        ("z4_double_semion", "Z4 Double Semion"),
        ("3d_toric_code", "3D Toric Code"),
        ("xcube", "X-cube"),
        ("haah_cubic_code", "Haah cubic code"),
    ]
)

from mobility_toolkit.boundary_gauge.algebra.support import get_support_weight
from mobility_toolkit.boundary_gauge.boundary.pipeline import (
    run_algorithm_1_boundary_ops_2d,
    run_algorithm_1_boundary_ops_3d,
)
from mobility_toolkit.boundary_gauge.models.models_2d import (
    POSITIONS_2D_EDGE_NEGATIVE,
    POSITIONS_2D_EDGE_POSITIVE,
    get_Z4_double_semion_params,
    get_Z4_double_semion_smooth_top_params,
    get_Z4_toric_code_params,
    get_Z4_toric_code_smooth_top_params,
    get_fish_toric_code_params,
    get_fish_toric_code_smooth_top_params,
    get_toric_code_params,
    get_toric_code_smooth_top_params,
)
from mobility_toolkit.boundary_gauge.models.models_3d import (
    POSITIONS_3D_EDGE_NEGATIVE,
    POSITIONS_3D_EDGE_POSITIVE,
    POSITIONS_HAAH_VERTEX_EXACT,
    POSITIONS_HAAH_VERTEX_SPLIT_X,
    get_3d_toric_code_params,
    get_3d_toric_code_smooth_top_params,
    get_haah_cubic_code_params,
    get_xcube_code_params,
    get_xcube_code_smooth_top_params,
)


@dataclass(frozen=True)
class Case:
    index: int
    cell_index: int
    title: str
    dimension: int
    params: dict
    model_factory: Callable
    positions: object
    first_n_bulk: int = 0


def iter_cases(*, haah_visual_split: bool = False) -> list[Case]:
    """Return the 20 notebook examples with either exact or split Haah positions."""
    common_2d = {"Lx": 5, "Ly": 5, "q": 2, "wx": 3, "wy": 3}
    common_3dtc = {"Lx": 3, "Ly": 3, "Lz": 4, "q": 3, "d": 2, "wx": 2, "wy": 2, "wz": 2}
    common_xcube = {"Lx": 4, "Ly": 4, "Lz": 4, "q": 3, "d": 2, "wx": 2, "wy": 2, "wz": 2}
    common_haah = {"Lx": 5, "Ly": 5, "Lz": 5, "q": 2, "d": 2, "wx": 2, "wy": 2, "wz": 2}
    haah_positions = POSITIONS_HAAH_VERTEX_SPLIT_X if haah_visual_split else POSITIONS_HAAH_VERTEX_EXACT

    return [
        Case(1, 5, "2D Toric Code smooth bottom", 2, {**common_2d, "d": 2, "boundary": "bottom"}, get_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(2, 7, "2D Toric Code rough top", 2, {**common_2d, "d": 2, "boundary": "top"}, get_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(3, 9, "2D Toric Code smooth top", 2, {**common_2d, "d": 2, "boundary": "top"}, get_toric_code_smooth_top_params, POSITIONS_2D_EDGE_NEGATIVE),
        Case(4, 11, "Fish Toric Code smooth bottom", 2, {**common_2d, "d": 2, "boundary": "bottom"}, get_fish_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(5, 13, "Fish Toric Code rough top", 2, {**common_2d, "d": 2, "boundary": "top"}, get_fish_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(6, 15, "Fish Toric Code smooth top", 2, {**common_2d, "d": 2, "boundary": "top"}, get_fish_toric_code_smooth_top_params, POSITIONS_2D_EDGE_NEGATIVE),
        Case(7, 17, "Z4 Toric Code smooth bottom", 2, {**common_2d, "d": 4, "boundary": "bottom"}, get_Z4_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(8, 19, "Z4 Toric Code rough top", 2, {**common_2d, "d": 4, "boundary": "top"}, get_Z4_toric_code_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(9, 21, "Z4 Toric Code smooth top", 2, {**common_2d, "d": 4, "boundary": "top"}, get_Z4_toric_code_smooth_top_params, POSITIONS_2D_EDGE_NEGATIVE),
        Case(10, 23, "Z4 Double Semion smooth bottom", 2, {**common_2d, "d": 4, "boundary": "bottom"}, get_Z4_double_semion_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(11, 25, "Z4 Double Semion rough top", 2, {**common_2d, "d": 4, "boundary": "top"}, get_Z4_double_semion_params, POSITIONS_2D_EDGE_POSITIVE),
        Case(12, 27, "Z4 Double Semion smooth top", 2, {**common_2d, "d": 4, "boundary": "top"}, get_Z4_double_semion_smooth_top_params, POSITIONS_2D_EDGE_NEGATIVE),
        Case(13, 29, "3D Toric Code smooth bottom", 3, {**common_3dtc, "boundary": "bottom"}, get_3d_toric_code_params, POSITIONS_3D_EDGE_POSITIVE, 4),
        Case(14, 31, "3D Toric Code rough top", 3, {**common_3dtc, "boundary": "top"}, get_3d_toric_code_params, POSITIONS_3D_EDGE_POSITIVE, 4),
        Case(15, 33, "3D Toric Code smooth top", 3, {**common_3dtc, "boundary": "top"}, get_3d_toric_code_smooth_top_params, POSITIONS_3D_EDGE_NEGATIVE, 4),
        Case(16, 35, "X-cube smooth bottom", 3, {**common_xcube, "boundary": "bottom"}, get_xcube_code_params, POSITIONS_3D_EDGE_POSITIVE, 3),
        Case(17, 37, "X-cube rough top", 3, {**common_xcube, "boundary": "top"}, get_xcube_code_params, POSITIONS_3D_EDGE_POSITIVE, 3),
        Case(18, 39, "X-cube smooth top", 3, {**common_xcube, "boundary": "top"}, get_xcube_code_smooth_top_params, POSITIONS_3D_EDGE_NEGATIVE, 3),
        Case(19, 41, "Haah cubic code bottom", 3, {**common_haah, "boundary": "bottom"}, get_haah_cubic_code_params, haah_positions),
        Case(20, 43, "Haah cubic code top", 3, {**common_haah, "boundary": "top"}, get_haah_cubic_code_params, haah_positions),
    ]


def case_kwargs(case: Case, *, visualize: bool) -> dict:
    return {
        **case.params,
        "stabilizer_generators": case.model_factory(),
        "qudit_positions": case.positions,
        "visualize_stabilizer_generators_flag": visualize,
        "visualize_first_n_bulk_stabilizers": case.first_n_bulk if visualize else 0,
        "visualize_local_boundary_gauge_ops": visualize,
    }


def run_case(case: Case, *, visualize: bool = False):
    kwargs = case_kwargs(case, visualize=visualize)
    if case.dimension == 2:
        return run_algorithm_1_boundary_ops_2d(**kwargs)
    return run_algorithm_1_boundary_ops_3d(**kwargs)


def summarize_result(bulk, ops, s_mat) -> dict[str, object]:
    return {
        "bulk_count": len(bulk),
        "s_mat_shape": tuple(s_mat.shape),
        "final_generator_count": int(ops.shape[0]),
        "weights": [get_support_weight(op) for op in ops],
    }


def extract_saved_output_by_cell() -> dict[int, str]:
    nb = json.loads((PROJECT_ROOT / NOTEBOOK_NAME).read_text(encoding="utf-8"))
    outputs: dict[int, str] = {}
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        text_parts: list[str] = []
        for output in cell.get("outputs", []):
            if "text" in output:
                text_parts.append("".join(output["text"]))
            data = output.get("data", {})
            if "text/plain" in data:
                text_parts.append("".join(data["text/plain"]))
        outputs[idx] = "\n".join(text_parts)
    return outputs


def parse_summary(text: str) -> dict[str, object]:
    summary: dict[str, object] = {}
    patterns = {
        "bulk_count": r"retained fully-supported bulk stabilizers = (\d+)",
        "s_mat_shape": r"S_mat shape = \((\d+),\s*(\d+)\)",
        "zero_syndrome_count": r"Raw zero-syndrome operators in boundary patch = (\d+)",
        "raw_generator_count": r"Independent raw boundary gauge operators = (\d+)",
        "final_generator_count": r"Final exact boundary gauge operator generators = (\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if not match:
            continue
        summary[key] = (int(match.group(1)), int(match.group(2))) if key == "s_mat_shape" else int(match.group(1))

    weights = [int(w) for w in re.findall(r"^G\[\d+\] weight=(\d+):", text, re.MULTILINE)]
    if weights:
        summary["weights"] = weights
    return summary


def code_key(case_title: str) -> str:
    if case_title.startswith("2D Toric Code"):
        return "2d_toric_code"
    if case_title.startswith("Fish Toric Code"):
        return "fish_toric_code"
    if case_title.startswith("Z4 Toric Code"):
        return "z4_toric_code"
    if case_title.startswith("Z4 Double Semion"):
        return "z4_double_semion"
    if case_title.startswith("3D Toric Code"):
        return "3d_toric_code"
    if case_title.startswith("X-cube"):
        return "xcube"
    if case_title.startswith("Haah"):
        return "haah_cubic_code"
    raise ValueError(f"unknown code family for case title: {case_title}")


def is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def slugify(text: str, max_len: int = 90) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    text = re.sub(r"_+", "_", text).strip("_")
    return (text or "figure")[:max_len]


def figure_title(fig) -> str:
    if getattr(fig, "_suptitle", None) is not None:
        title = fig._suptitle.get_text().strip()
        if title:
            return title
    for ax in fig.axes:
        title = ax.get_title().strip()
        if title:
            return title
    return "Untitled figure"


def write_manifest(
    path: Path,
    rows: Iterable[dict[str, str]],
    fieldnames: Optional[list[str]] = None,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames or FIGURE_MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def read_manifest(path: Path = MANIFEST) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def grid_layout(n: int) -> tuple[int, int]:
    if n <= 4:
        return 2, 2
    if n <= 6:
        return 2, 3
    if n <= 9:
        return 3, 3
    if n <= 12:
        return 3, 4
    return math.ceil(n / 4), 4

