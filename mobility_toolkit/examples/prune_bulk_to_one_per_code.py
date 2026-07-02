"""Keep only one bulk-stabilizer display figure for each code family."""

from __future__ import annotations

import csv
import math
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
BACKUP_MANIFEST = OUTPUT_DIR / "manifest_before_one_bulk_per_code.csv"
DELETED_LOG = OUTPUT_DIR / "deleted_extra_bulk_figures_one_per_code.csv"


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_bulk_figure(row: dict[str, str]) -> bool:
    return "Bulk Stabilizer" in row["figure_title"]


def _code_key(case_title: str) -> str:
    if case_title.startswith("2D Toric Code"):
        return "2D Toric Code"
    if case_title.startswith("Fish Toric Code"):
        return "Fish Toric Code"
    if case_title.startswith("Z4 Toric Code"):
        return "Z4 Toric Code"
    if case_title.startswith("Z4 Double Semion"):
        return "Z4 Double Semion"
    if case_title.startswith("3D Toric Code"):
        return "3D Toric Code"
    if case_title.startswith("X-cube"):
        return "X-cube"
    if case_title.startswith("Haah"):
        return "Haah cubic code"
    return case_title


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

    kept_bulk_codes: set[str] = set()
    kept_rows: list[dict[str, str]] = []
    deleted_rows: list[dict[str, str]] = []
    deleted_paths: set[Path] = set()

    for row in rows:
        if not _is_bulk_figure(row):
            kept_rows.append(row)
            continue

        code = _code_key(row["case_title"])
        if code not in kept_bulk_codes:
            kept_bulk_codes.add(code)
            kept_rows.append(row)
            continue

        path = Path(row["path"])
        if not _is_inside(path, INDIVIDUAL_DIR):
            raise RuntimeError(f"refusing to remove outside individual dir: {path}")
        deleted_rows.append({**row, "code_key": code})
        deleted_paths.add(path)

    for path in sorted(deleted_paths):
        if path.exists():
            path.unlink()

    fieldnames = [
        "case_index",
        "cell_index",
        "case_title",
        "figure_index",
        "figure_title",
        "path",
    ]
    with MANIFEST.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)

    with DELETED_LOG.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[*fieldnames, "code_key"])
        writer.writeheader()
        writer.writerows(deleted_rows)

    _save_contact_sheets(kept_rows)

    print(f"Kept bulk code families: {len(kept_bulk_codes)}")
    print(f"Deleted extra bulk figures: {len(deleted_paths)}")
    print(f"Remaining manifest rows: {len(kept_rows)}")
    print(f"Backup manifest: {BACKUP_MANIFEST}")
    print(f"Deleted log: {DELETED_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

