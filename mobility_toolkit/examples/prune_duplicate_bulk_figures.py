"""Prune duplicate bulk-stabilizer figures from exported static figures."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "figures"
INDIVIDUAL_DIR = OUTPUT_DIR / "individual"
SHEET_DIR = OUTPUT_DIR / "sheets"
MANIFEST = OUTPUT_DIR / "manifest.csv"
BACKUP_MANIFEST = OUTPUT_DIR / "manifest_before_bulk_prune.csv"
DELETED_LOG = OUTPUT_DIR / "deleted_duplicate_bulk_figures.csv"


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_bulk_figure(row: dict[str, str]) -> bool:
    return "Bulk Stabilizer" in row["figure_title"]


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_contact_sheets(rows: list[dict[str, str]], chunk_size: int = 20) -> None:
    for old_sheet in SHEET_DIR.glob("contact_sheet_*.png"):
        if not _is_inside(old_sheet, SHEET_DIR):
            raise RuntimeError(f"refusing to remove sheet outside output dir: {old_sheet}")
        old_sheet.unlink()

    for page, start in enumerate(range(0, len(rows), chunk_size), start=1):
        chunk = rows[start : start + chunk_size]
        cols = 4
        row_count = math.ceil(len(chunk) / cols)
        fig, axes = plt.subplots(row_count, cols, figsize=(cols * 4.8, row_count * 4.0))
        flat_axes = list(getattr(axes, "flat", [axes]))
        for ax in flat_axes:
            ax.axis("off")

        for ax, row in zip(flat_axes, chunk):
            image = mpimg.imread(row["path"])
            ax.imshow(image)
            ax.axis("off")
            label = f'{row["case_index"]}.{row["figure_index"]} {row["case_title"]}\n{row["figure_title"]}'
            ax.set_title(label, fontsize=7, pad=4)

        fig.tight_layout()
        fig.savefig(SHEET_DIR / f"contact_sheet_{page:02d}.png", dpi=160, bbox_inches="tight")
        plt.close(fig)


def main() -> int:
    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    if not BACKUP_MANIFEST.exists():
        BACKUP_MANIFEST.write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        path = Path(row["path"])
        if _is_bulk_figure(row) and path.exists():
            groups[_hash_file(path)].append(row)

    delete_rows: list[dict[str, str]] = []
    delete_paths: set[Path] = set()
    for group in groups.values():
        if len(group) <= 1:
            continue
        for row in group[1:]:
            path = Path(row["path"])
            if not _is_inside(path, INDIVIDUAL_DIR):
                raise RuntimeError(f"refusing to remove outside individual dir: {path}")
            delete_rows.append(row)
            delete_paths.add(path)

    for path in sorted(delete_paths):
        if path.exists():
            path.unlink()

    kept_rows = [row for row in rows if Path(row["path"]) not in delete_paths]

    fieldnames = [
        "case_index",
        "cell_index",
        "case_title",
        "figure_index",
        "figure_title",
        "path",
    ]
    with DELETED_LOG.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(delete_rows)

    with MANIFEST.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    _save_contact_sheets(kept_rows)

    print(f"Deleted duplicate bulk figures: {len(delete_paths)}")
    print(f"Remaining manifest rows: {len(kept_rows)}")
    print(f"Backup manifest: {BACKUP_MANIFEST}")
    print(f"Deleted log: {DELETED_LOG}")
    print(f"Regenerated contact sheets in: {SHEET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

