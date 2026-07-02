"""Create one contact sheet per code family from the current figure manifest."""

from __future__ import annotations

import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

from common import CODE_ORDER, SHEET_DIR, code_key, grid_layout, is_inside, read_manifest


def _sort_key(row: dict[str, str]) -> tuple[int, int]:
    return int(row["case_index"]), int(row["figure_index"])


def _make_sheet(code: str, display_name: str, rows: list[dict[str, str]]):
    rows = sorted(rows, key=_sort_key)
    row_count, col_count = grid_layout(len(rows))
    fig, axes = plt.subplots(row_count, col_count, figsize=(col_count * 5.2, row_count * 4.25))
    flat_axes = list(getattr(axes, "flat", [axes]))

    for ax in flat_axes:
        ax.axis("off")

    for ax, row in zip(flat_axes, rows):
        image = mpimg.imread(row["path"])
        ax.imshow(image)
        ax.axis("off")
        label = (
            f'cell {row["cell_index"]} | fig {row["figure_index"]}\n'
            f'{row["case_title"]}\n'
            f'{row["figure_title"]}'
        )
        ax.set_title(label, fontsize=7, pad=4)

    fig.suptitle(f"{display_name} overview", fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    path = SHEET_DIR / f"{list(CODE_ORDER).index(code) + 1:02d}_{code}_generator_set.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> int:
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    for old_sheet in SHEET_DIR.glob("*.png"):
        if not is_inside(old_sheet, SHEET_DIR):
            raise RuntimeError(f"refusing to remove outside sheet dir: {old_sheet}")
        old_sheet.unlink()

    grouped: dict[str, list[dict[str, str]]] = {key: [] for key in CODE_ORDER}
    for row in read_manifest():
        grouped[code_key(row["case_title"])].append(row)

    index_rows = []
    for code, display_name in CODE_ORDER.items():
        path = _make_sheet(code, display_name, grouped[code])
        index_rows.append(
            {
                "code_key": code,
                "display_name": display_name,
                "figure_count": str(len(grouped[code])),
                "path": str(path),
            }
        )
        print(f"{display_name}: {len(grouped[code])} figures -> {path}")

    index_path = SHEET_DIR / "code_contact_sheets.csv"
    with index_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["code_key", "display_name", "figure_count", "path"])
        writer.writeheader()
        writer.writerows(index_rows)

    print(f"Index: {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
