"""Run every notebook example through the modular package and compare summaries."""

from __future__ import annotations

import contextlib
import io

from common import (
    extract_saved_output_by_cell,
    iter_cases,
    parse_summary,
    run_case,
    summarize_result,
)


EXPECTED_FIXED_DIFFERENCES = {
    # The saved notebook used row-reduced S_mat as local reduction moves here,
    # leaving a nonlocal X-type representative of weight 7. The modular
    # pipeline now uses physical bulk stabilizer rows and reduces it to weight 3.
    5: {"weights": ([1, 7], [1, 3])},
}


def _run_case_summary(case) -> tuple[dict[str, object], str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        bulk, ops, s_mat = run_case(case, visualize=False)
    text = buffer.getvalue()
    summary = parse_summary(text)
    summary.update(summarize_result(bulk, ops, s_mat))
    return summary, text


def main() -> int:
    saved_outputs = extract_saved_output_by_cell()
    mismatch_count = 0
    no_saved_count = 0

    print("cell | status | title | modular summary")
    print("-----|--------|-------|----------------")

    for case in iter_cases(haah_visual_split=False):
        modular_summary, _ = _run_case_summary(case)
        saved_summary = parse_summary(saved_outputs.get(case.cell_index, ""))

        if not saved_summary:
            no_saved_count += 1
            status = "NO_SAVED_OUTPUT"
        else:
            comparable_keys = sorted(set(saved_summary) & set(modular_summary))
            mismatches = {
                key: (saved_summary[key], modular_summary[key])
                for key in comparable_keys
                if saved_summary[key] != modular_summary[key]
            }
            expected = EXPECTED_FIXED_DIFFERENCES.get(case.cell_index, {})
            unexpected_mismatches = {
                key: value for key, value in mismatches.items() if expected.get(key) != value
            }
            if unexpected_mismatches:
                mismatch_count += 1
                status = "DIFF " + repr(unexpected_mismatches)
            elif mismatches:
                status = "EXPECTED_FIX " + repr(mismatches)
            else:
                status = "MATCH"

        print(f"{case.cell_index:>4} | {status} | {case.title} | {modular_summary}")

    print()
    print(f"Saved-output mismatches: {mismatch_count}")
    print(f"Cases without saved notebook output: {no_saved_count}")
    return 1 if mismatch_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
