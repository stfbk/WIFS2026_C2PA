"""
Entrypoint: python3 -m c2pa_uniqueness [output_path] [report_path]

Task 1: for each folder flagged inconsistent by c2pa_consistency (has an
        inconsistency_report.md), report a positional action-slot summary
        (where in the sequence presets agree/split) plus a local uniqueness
        grouping among just that folder's own preset variants.
Task 2: across ALL presets found under output_path, group each preset into
        its single most-constrained equivalence class (one of 7 categories),
        or report it as unique if it matches nobody at any level.
"""
import sys
from pathlib import Path

from .info import __uniqueness_scan_logo__, __description_uniqueness__
from .constants import DEFAULT_INPUT_FOLDER, DEFAULT_OUTPUT_FOLDER
from .loader import find_inconsistent_folders, load_folder_presets, load_all_presets
from .grouping import group_presets
from .slot_summary import summarize_folder_slots, format_slot_summary, slot_summary_to_dict
from .report import print_summary, write_json_report

if __name__ == "__main__":
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_INPUT_FOLDER)
    report_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_OUTPUT_FOLDER)

    if not output_path.exists():
        sys.exit(f"ERROR: Path not found {output_path}")

    print(__uniqueness_scan_logo__)
    print(__description_uniqueness__)
    print()

    # --- Task 1: per-folder slot summary + local uniqueness ---
    inconsistent_folders = find_inconsistent_folders(output_path)
    print(f"Found {len(inconsistent_folders)} inconsistent folder(s).\n")

    for folder in inconsistent_folders:
        presets = load_folder_presets(folder)
        if len(presets) < 2:
            continue

        slots = summarize_folder_slots(presets)
        print(f"{folder}:")
        print(format_slot_summary(slots))

        grouping = group_presets(presets)
        print_summary("  Local uniqueness:", grouping)

        saving_name = str(folder).replace('/', '_')+'.json'

        write_json_report(
            {"action_slot_summary": slot_summary_to_dict(slots), "uniqueness": grouping},
            Path(DEFAULT_OUTPUT_FOLDER) / saving_name,
        )

    # --- Task 2: global uniqueness across every preset in the tree ---
    all_presets = load_all_presets(output_path)
    print(f"Loaded {len(all_presets)} preset(s) total.\n")

    global_grouping = group_presets(all_presets)
    print_summary("Global uniqueness:", global_grouping)

    report_file = report_path / "uniqueness_report.json"

    write_json_report(global_grouping, report_file)
    print(f"Wrote {report_file}")