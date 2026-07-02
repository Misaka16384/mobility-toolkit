"""Keep one full independent bulk-generator display set for each code family."""

from __future__ import annotations

from pathlib import Path

from common import (
    CODE_ORDER,
    FIGURE_MANIFEST_FIELDS,
    INDIVIDUAL_DIR,
    MANIFEST,
    OUTPUT_DIR,
    code_key,
    is_inside,
    read_manifest,
    write_manifest,
)


BACKUP_MANIFEST = OUTPUT_DIR / "manifest_before_bulk_generator_set_prune.csv"
DELETED_LOG = OUTPUT_DIR / "deleted_bulk_not_in_generator_set_per_code.csv"


def _is_bulk_generator(row: dict[str, str]) -> bool:
    return row["figure_title"].startswith("Bulk Stabilizer Generator #")


def _is_valid_bulk(row: dict[str, str]) -> bool:
    return row["figure_title"].startswith("Valid Bulk Stabilizer #")


def main() -> int:
    rows = read_manifest()
    BACKUP_MANIFEST.write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")

    first_case_for_code: dict[str, int] = {}
    for row in rows:
        if _is_bulk_generator(row):
            first_case_for_code.setdefault(code_key(row["case_title"]), int(row["case_index"]))

    kept_rows: list[dict[str, str]] = []
    deleted_rows: list[dict[str, str]] = []
    deleted_paths: set[Path] = set()

    for row in rows:
        delete_reason = ""
        if _is_valid_bulk(row):
            delete_reason = "valid_bulk_not_independent_generator_display"
        elif _is_bulk_generator(row):
            code = code_key(row["case_title"])
            if int(row["case_index"]) != first_case_for_code[code]:
                delete_reason = "duplicate_code_family_bulk_generator_display"

        if not delete_reason:
            kept_rows.append(row)
            continue

        path = Path(row["path"])
        if not is_inside(path, INDIVIDUAL_DIR):
            raise RuntimeError(f"refusing to remove outside individual dir: {path}")
        deleted_rows.append({**row, "delete_reason": delete_reason, "code_key": code_key(row["case_title"])})
        deleted_paths.add(path)

    for path in sorted(deleted_paths):
        if path.exists():
            path.unlink()

    write_manifest(MANIFEST, kept_rows, FIGURE_MANIFEST_FIELDS)
    write_manifest(DELETED_LOG, deleted_rows, [*FIGURE_MANIFEST_FIELDS, "delete_reason", "code_key"])

    kept_bulk = [row for row in kept_rows if _is_bulk_generator(row)]
    print(f"Kept independent bulk generator display figures: {len(kept_bulk)}")
    print(f"Deleted bulk/valid-bulk display figures: {len(deleted_paths)}")
    print(f"Remaining manifest rows: {len(kept_rows)}")
    for code, display_name in CODE_ORDER.items():
        count = sum(1 for row in kept_bulk if code_key(row["case_title"]) == code)
        print(f"{display_name}: {count}")
    print(f"Backup manifest: {BACKUP_MANIFEST}")
    print(f"Deleted log: {DELETED_LOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
