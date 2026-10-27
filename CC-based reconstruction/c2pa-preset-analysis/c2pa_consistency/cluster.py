"""
Walks an output tree produced by the style-generation pipeline. In every
folder that contains an `inconsistency_report.md`, it collects the style
JSON variants, groups the ones that share the exact same set of actions/
parameters, and writes one or more merged "UNIQUE" JSON files:

  - a parameter whose value agrees across every file in a group keeps
    that value
  - a parameter whose value disagrees is replaced with "x_variable"
  - files that don't share the same set of parameters are NOT merged
    together; each distinct set of parameters becomes its own cluster,
    written as style_<key>_UNIQUE.json, style_<key>_UNIQUE_variant2.json, ...
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from collections import defaultdict

REPORT_FILENAME = "inconsistency_report.md"
PLACEHOLDER = "x_variable"
OLD_FILES_SUBFOLDER = "old_variants"

# the two keys expected inside every action's "parameters" dict
PARAM_NAME_KEY = "com.adobe.acr"
PARAM_VALUE_KEY = "com.adobe.acr.value"

# The only variant-marker convention in use: a trailing "_variantN".
# If you ever introduce another convention, add its pattern here.
VARIANT_SUFFIX_PATTERN = re.compile(r"_variant\d+$", re.IGNORECASE)


def normalize_style_key(key: str) -> str:
    """
    Strip a trailing "_variantN" suffix from a style key (or filename
    stem) so that e.g. "seasons_autumn_variant2" and "seasons_autumn"
    both normalize to "seasons_autumn" and get grouped together, even if
    the JSON's top-level key (not just the filename) carries the suffix.
    Keys with no such suffix are returned unchanged.
    """
    return VARIANT_SUFFIX_PATTERN.sub("", key)


def find_target_folders(root: Path):
    """Yield every folder under `root` that contains inconsistency_report.md."""
    for md_path in root.rglob(REPORT_FILENAME):
        yield md_path.parent


def load_style_json(path: Path):
    """
    Load one style json file.
    Returns (style_key, actions_list), or None if the file doesn't look
    like a style file (e.g. it's already a generated _UNIQUE file, or
    doesn't match the expected {style_key: [...]} shape).
    """
    if "_UNIQUE" in path.stem:
        return None  # don't re-consume our own output on re-runs

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict) or len(data) != 1:
        return None

    (style_key, actions), = data.items()
    if not isinstance(actions, list):
        return None

    return style_key, actions


def signature_and_values(actions: list):
    """
    Turn an actions list into:
      - signature: an ordered tuple of (action, property_name), identifying
        which parameters are present, in the file's original order
      - values: dict {(action, property_name): value}
    """
    signature = []
    values = {}
    for entry in actions:
        action = entry.get("action")
        params = entry.get("parameters", {})
        prop_name = params.get(PARAM_NAME_KEY)
        prop_value = params.get(PARAM_VALUE_KEY)
        key = (action, prop_name)
        signature.append(key)
        values[key] = prop_value
    return tuple(signature), values


def cluster_by_signature(files_data: list):
    """
    files_data: list of (path, signature, values)
    Returns a list of (signature, members) sorted by cluster size,
    largest first. members is a list of (path, values).
    """
    groups = defaultdict(list)
    for path, signature, values in files_data:
        groups[signature].append((path, values))

    return sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)


def merge_cluster(signature: tuple, members: list):
    """
    Build the merged actions list for one cluster: a parameter keeps its
    value if every member agrees, otherwise it becomes "x_variable".
    """
    merged_actions = []
    for action, prop_name in signature:
        key = (action, prop_name)
        values = {m_values[key] for _path, m_values in members}
        merged_value = next(iter(values)) if len(values) == 1 else PLACEHOLDER
        merged_actions.append({
            "action": action,
            "parameters": {
                PARAM_NAME_KEY: prop_name,
                PARAM_VALUE_KEY: merged_value,
            },
        })
    return merged_actions


def output_name_for(style_key: str, cluster_index: int) -> str:
    if cluster_index == 0:
        return f"{style_key}_UNIQUE.json"
    return f"{style_key}_UNIQUE_variant{cluster_index + 1}.json"


def process_folder(folder: Path, min_cluster_size: int = 2, dry_run: bool = False,
                    old_files_subfolder: str = OLD_FILES_SUBFOLDER):
    """
    Process one folder that contains an inconsistency_report.md.

    min_cluster_size: minimum number of agreeing files needed before a
    _UNIQUE file is written for that group. Default 2, matching "only
    make a merged variant if there's something to merge against". Set to
    1 if you also want lone, non-matching files copied out as their own
    _UNIQUE file.

    old_files_subfolder: name of the subfolder (created inside `folder`)
    that the original variant files are moved into after the merged
    _UNIQUE file(s) are written, so the folder stays readable. Pass None
    to leave the originals where they are.
    """
    by_style_key = defaultdict(list)

    for json_path in sorted(folder.glob("*.json")):
        loaded = load_style_json(json_path)
        if loaded is None:
            continue
        style_key, actions = loaded
        base_key = normalize_style_key(style_key)
        signature, values = signature_and_values(actions)
        by_style_key[base_key].append((json_path, signature, values))

    written = []
    processed_originals = []

    for style_key, files_data in by_style_key.items():
        clusters = cluster_by_signature(files_data)

        cluster_index = 0
        for signature, members in clusters:
            if len(members) < min_cluster_size:
                # not merged into anything -> leave these file(s) alone so
                # they stay visible in the main folder
                continue

            merged_actions = merge_cluster(signature, members)
            out_path = folder / output_name_for(style_key, cluster_index)

            if not dry_run:
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump({style_key: merged_actions}, f, indent=2, ensure_ascii=False)

            written.append(out_path)
            cluster_index += 1

            # only the files that actually contributed to this written
            # _UNIQUE file are "old" now
            processed_originals.extend(path for path, _values in members)

    if not dry_run and old_files_subfolder and processed_originals:
        old_dir = folder / old_files_subfolder
        old_dir.mkdir(exist_ok=True)
        for path in processed_originals:
            shutil.move(str(path), str(old_dir / path.name))

    return written


def process_output_tree(root, min_cluster_size: int = 2, dry_run: bool = False,
                         old_files_subfolder: str = OLD_FILES_SUBFOLDER):
    """Entry point to call from your pipeline after generation finishes."""
    root = Path(root)
    all_written = []
    for folder in find_target_folders(root):
        all_written.extend(
            process_folder(folder, min_cluster_size=min_cluster_size, dry_run=dry_run,
                            old_files_subfolder=old_files_subfolder)
        )
    return all_written


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="root output folder to scan")
    parser.add_argument("--dry-run", action="store_true", help="print what would be written, don't write")
    parser.add_argument("--min-cluster-size", type=int, default=2)
    parser.add_argument("--old-files-subfolder", default=OLD_FILES_SUBFOLDER,
                         help="subfolder name to move original variant files into (empty string to disable)")
    args = parser.parse_args()

    result = process_output_tree(args.root, min_cluster_size=args.min_cluster_size, dry_run=args.dry_run, old_files_subfolder=args.old_files_subfolder or None)
    for p in result:
        print("wrote", p)
    if not result:
        print("nothing to write (no matching clusters found)")