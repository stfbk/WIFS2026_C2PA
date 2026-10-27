"""
Entrypoint for direct execution: python3 -m c2pa_consistency [input_path] [output_path]

Preset analysis:
   For each image, its manifest is taken (if present), and the claim_generator_info[name] and actions are extracted.
   From the set of actions, ones with "action" and "parameters" are kept, except "c2pa.opened" (if present); for Lightroom specifically, the
   preset-label-only entry (e.g. c2pa.filtered / "Preset") is also dropped.

   The resulting list is compared between images (order-independent on both actions and parameters); if one differs it is taken as a second sample to
   be compared with the remaining images.
   
   The output is one or more JSON files, at least one per preset, stored in the output folder. The output folder is structured with the name of the
   software (taken from claim_generator_info[name]) and the same structure as the input folder, with the name of the preset as the last folder.
"""

import sys
import os
from pathlib import Path

from c2pa_consistency.cluster import process_output_tree

from .constants import DEFAULT_INPUT_FOLDER, DEFAULT_OUTPUT_FOLDER, BAR_WIDTH
from .info import __consistency_scan_logo__, __description_consistency__
from .pipeline import analyse_folder
from .analyzer import analyse_inconsistency


def _print_progress(current: int, total: int, inconsistent_count: int) -> None:
    fraction = current / total if total else 1.0
    filled = int(BAR_WIDTH * fraction)
    bar = "#" * filled + "-" * (BAR_WIDTH - filled)
    pct = int(fraction * 100)
    line = f"\r  [{bar}] {pct:3d}% ({current}/{total} folders, {inconsistent_count} inconsistent)"
    sys.stdout.write(line)
    sys.stdout.flush()

if __name__ == "__main__":

    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_INPUT_FOLDER)
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(DEFAULT_OUTPUT_FOLDER)

    if not input_path.exists():
        sys.exit(f"ERROR: Path not found {input_path}")

    print(__consistency_scan_logo__)
    print(__description_consistency__)
    print()

    root_folder = input_path

    # walk the entire tree, collecting every directory at every depth
    all_folders = sorted(
        Path(dir_path)
        for dir_path, dirs, files in os.walk(root_folder)
        if files  # only keep folders that actually contain files
    )

    if not all_folders:
        sys.exit(f"ERROR: No files found under {root_folder}")

    if len(all_folders) > 1:
        print(f"Scanning preset path '{root_folder}' and its {len(all_folders) - 1} subfolder(s) at all depths...")
    else:
        print(f"Scanning preset path '{root_folder}'...")

    results = []
    total = len(all_folders)
    inconsistent_so_far = 0

    for i, folder in enumerate(all_folders, start=1):
        result = analyse_folder(folder, input_root=root_folder, output_root=output_path)

        if result is not None:
            results.append(result)
            if not result.is_consistent:
                inconsistent_so_far += 1

        _print_progress(i, total, inconsistent_so_far)

    print("\n")

    inconsistent = [r for r in results if not r.is_consistent]
    skipped = len(all_folders) - len(results)

    print(f"Summary: {len(results)} folder(s) analyzed, {len(inconsistent)} inconsistent, {skipped} skipped (no manifests)")
    if inconsistent:
        print("Inconsistent folders:")
        for r in inconsistent:
            print(f"  ! {r.output_dir} — {r.image_count} image(s), {r.preset_count} distinct presets")

        print()
        answer = input("Do you want to further analyse these inconsistencies? [Y/n] ").strip().lower()
        if answer in ("", "y", "yes"):
            print()
            for r in inconsistent:
                analyse_inconsistency(r)

            print(output_path)
            result = process_output_tree(output_path, min_cluster_size=2, dry_run="", old_files_subfolder="old_variants" or None)
            for p in result:
                print("wrote", p)
            if not result:
                print("nothing to write (no matching clusters found)")

    print()
