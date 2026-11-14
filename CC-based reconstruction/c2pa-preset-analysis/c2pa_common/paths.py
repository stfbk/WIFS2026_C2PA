"""
Default folders and files of the whole pipeline.

Change a default HERE and every stage (and run.sh) picks it up. Paths are
relative to the tool's root folder, which is where run.sh runs everything.
Each stage still accepts its own command-line arguments, which win over these.
"""
from pathlib import Path

INPUT_PRESETS = "./DB" #"./input_presets"            # images carrying the C2PA manifests
OUTPUT_ROOT = "./output"

CONSISTENCY_OUTPUT = f"{OUTPUT_ROOT}/consistency"
UNIQUENESS_INPUT = CONSISTENCY_OUTPUT        # uniqueness reads what consistency wrote
UNIQUENESS_OUTPUT = f"{OUTPUT_ROOT}/uniqueness"

SUMMARY_TABLE = f"{OUTPUT_ROOT}/summary_table.md"
SUMMARY_GROUPED = f"{OUTPUT_ROOT}/summary_grouped.json"
SUMMARY_CSV = f"{OUTPUT_ROOT}/summary_table.csv"


def index_path_for(output_root: Path) -> Path:
    """
    Folder index written by the consistency stage and read by c2pa_summary.
    """
    root = Path(output_root).resolve()
    return root.parent / f"{root.name}_index.json"
