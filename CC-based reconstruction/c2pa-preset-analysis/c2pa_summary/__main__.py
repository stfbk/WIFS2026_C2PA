"""
Entrypoint: python3 -m c2pa_summary [consistency_output_path] [report_file]

Reads the folder index written by c2pa_consistency plus the preset files in
the consistency output, and writes the per-folder summary table (markdown).
"""
import sys
from pathlib import Path

from .table import load_index, build_rows, write_report, write_grouped_report, write_csv
from c2pa_common.info import __description_summary__, __summary_logo__
from c2pa_common.paths import CONSISTENCY_OUTPUT, SUMMARY_TABLE, SUMMARY_GROUPED, SUMMARY_CSV

if __name__ == "__main__":
    args = sys.argv[1:]
    index_path = Path(args[0]) if len(args) > 0 else Path(CONSISTENCY_OUTPUT)
    report_file = Path(args[1]) if len(args) > 1 else Path(SUMMARY_TABLE)
    grouped_file = Path(args[2]) if len(args) > 2 else Path(SUMMARY_GROUPED)
    csv_file = Path(args[3]) if len(args) > 3 else Path(SUMMARY_CSV)

    print(__summary_logo__)
    print(__description_summary__)
    print()

    try:
        index, root = load_index(index_path)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"ERROR: {e}")

    rows, missing = build_rows(index, root)
    write_report(rows, report_file)
    write_grouped_report(rows, grouped_file)
    write_csv(rows, csv_file)
    if missing:
        print(f"WARNING: no preset file found for {len(missing)} folder(s), reported as Full Uniqueness:")
        for m in missing:
            print(f"  - {m}")

    print(f"Summary table: {len(rows)} folder(s)")
    print(f"  consistency: {sum(r.full_consistency for r in rows)} full, {sum(r.partial_consistency for r in rows)} partial")
    print(f"  uniqueness:  {sum(r.full_uniqueness for r in rows)} full, {sum(r.partial_uniqueness for r in rows)} partial")
    print(f"Wrote {report_file}")
    print(f"Wrote {grouped_file}")
    print(f"Wrote {csv_file}")
