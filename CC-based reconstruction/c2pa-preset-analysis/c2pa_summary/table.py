"""
Build the per-image summary table.

Columns: File | Partial Consistency | Full Consistency | Partial Uniqueness | Full Uniqueness

Consistency:
  Full     - every image in the folder produced the same preset (1 preset)
  Partial  - the folder produced more than one preset

Uniqueness:
  Partial  - the image's preset is fully identical to a preset in ANOTHER folder
  Full     - no preset in any other folder is identical to it

Note: a _UNIQUE file carries "x_variable" for values that varied; it is
compared literally, so it only matches another preset with the same marker.
"""
from __future__ import annotations
import csv
import json
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path

from c2pa_common.paths import index_path_for
from c2pa_uniqueness.constants import CATEGORY_FULLY_IDENTICAL
from c2pa_uniqueness.grouping import group_presets
from c2pa_uniqueness.loader import Preset, load_all_presets

IMAGE_INDEX_FILENAME = "image_index.json"
OLD_VARIANTS_DIR = "old_variants"
HEADERS = ["Folder", "Partial Consistency", "Full Consistency", "Partial Uniqueness", "Full Uniqueness"]
MARK = "✓"

FAMILY_DEPTH = 2  # path components that define a family, e.g. 2 -> "lr-presets/adaptive"

HEADER_LINE = "| " + " | ".join(HEADERS) + " |"
DIVIDER_LINE = "|" + "|".join(["---", ":---:", ":---:", ":---:", ":---:"]) + "|"

@dataclass(frozen=True)
class Row:
    folder: str
    partial_consistency: bool
    full_consistency: bool
    partial_uniqueness: bool
    full_uniqueness: bool

def load_index(consistency_root: Path) -> tuple[dict, Path]:
    """Returns (index, consistency_output_root)."""
    root = Path(consistency_root)
    index_file = index_path_for(root)
    if not index_file.exists():
        raise FileNotFoundError(
            f"{index_file} not found. Run the consistency stage first (run.sh option 1 or 2)."
        )
    index = json.loads(index_file.read_text(encoding="utf-8"))
    if not index.get("folders"):
        raise ValueError(f"{index_file} lists no folders; re-run the consistency stage.")
    if any("output_dir" not in f or "preset_count" not in f for f in index["folders"]):
        raise ValueError(f"{index_file} is from an older version; re-run the consistency stage.")
    return index, root

def _current_presets(root: Path) -> list[Preset]:
    """Preset files as the uniqueness stage sees them, minus old_variants/."""
    return [p for p in load_all_presets(root) if OLD_VARIANTS_DIR not in p.path.relative_to(root).parts]

def build_rows(index: dict, root: Path) -> tuple[list[Row], list[str]]:
    """Returns (rows, folders for which no preset file was found)."""
    root = Path(root)
    presets = _current_presets(root)
    by_id = {p.id: p for p in presets}
    ids_by_dir: dict[Path, list[str]] = {}
    for p in presets:
        ids_by_dir.setdefault(p.path.parent, []).append(p.id)

    # presets fully identical to a preset that lives in another folder
    matched_elsewhere: set[str] = set()
    for group in group_presets(presets).get(CATEGORY_FULLY_IDENTICAL, {}).values():
        members = [by_id[pid] for pid in group["presets"]]
        for m in members:
            if any(o.path.parent != m.path.parent for o in members):
                matched_elsewhere.add(m.id)

    rows, missing = [], []
    for f in sorted(index["folders"], key=lambda f: f["folder"]):
        ids = ids_by_dir.get(root / f["output_dir"], [])
        if not ids:
            missing.append(f["folder"])
        partial_u = any(pid in matched_elsewhere for pid in ids)
        rows.append(Row(
            folder=f["folder"],
            partial_consistency=f["preset_count"] > 1,
            full_consistency=f["preset_count"] <= 1,
            partial_uniqueness=partial_u,
            full_uniqueness=not partial_u,
        ))
    return rows, missing

def family_of(folder: str) -> str:
    """First FAMILY_DEPTH path components"""
    # print(f"folder: {folder}") # folder: video/creative/VCR12
    # print(folder.split("/")[:FAMILY_DEPTH]) #  ['video', 'creative']
    return "/".join(folder.split("/")[:FAMILY_DEPTH])

def format_markdown(rows: list[Row]) -> str:
    """One Markdown table per preset family"""
    def cell(flag: bool) -> str:
        return MARK if flag else ""

    def row_line(r: Row) -> str:
        name = r.folder.replace("|", "\\|")
        return (
            f"| {name} | {cell(r.partial_consistency)} | {cell(r.full_consistency)} "
            f"| {cell(r.partial_uniqueness)} | {cell(r.full_uniqueness)} |"
        )

    if not rows:
        return "\n".join([HEADER_LINE, DIVIDER_LINE]) + "\n"

    blocks = []
    for _, group in groupby(rows, key=lambda r: family_of(r.folder)):
        blocks.append("\n".join([HEADER_LINE, DIVIDER_LINE, *(row_line(r) for r in group)]))
    return "\n\n".join(blocks) + "\n"

def format_csv_rows(rows: list[Row]) -> list[list[str]]:
    """Header + one list per row, with the same ✓ marks as the .md file."""
    def cell(flag: bool) -> str:
        return MARK if flag else ""

    return [HEADERS] + [
        [r.folder, cell(r.partial_consistency), cell(r.full_consistency),
         cell(r.partial_uniqueness), cell(r.full_uniqueness)]
        for r in rows
    ]

GROUPS = [
    ("partial_consistency_partial_uniqueness", "Partial Consistency - Partial Uniqueness", lambda r: r.partial_consistency and r.partial_uniqueness),
    ("partial_consistency_full_uniqueness", "Partial Consistency - Full Uniqueness", lambda r: r.partial_consistency and r.full_uniqueness),
    ("full_consistency_partial_uniqueness", "Full Consistency - Partial Uniqueness", lambda r: r.full_consistency and r.partial_uniqueness),
    ("full_consistency_full_uniqueness", "Full Consistency - Full Uniqueness", lambda r: r.full_consistency and r.full_uniqueness),
]

def build_grouped(rows: list[Row]) -> dict:
    """Folders grouped by (consistency, uniqueness) category."""
    categories = {}
    for key, label, pred in GROUPS:
        members = [r for r in rows if pred(r)]
        categories[key] = {
            "label": label,
            "count": len(members),
            "folders": [r.folder for r in members],
        }
    return {"total_folders": len(rows), "categories": categories}

def write_grouped_report(rows: list[Row], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_grouped(rows), indent=2, ensure_ascii=False), encoding="utf-8")

def write_report(rows: list[Row], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_markdown(rows), encoding="utf-8")

def write_csv(rows: list[Row], path: Path) -> None:
    """save .md table as .csv file: single header row, no repeated headers"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(format_csv_rows(rows))