"""Load presets produced by c2pa_consistency, for uniqueness analysis."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

from .constants import INCONSISTENCY_REPORT_FILENAME as REPORT_FILENAME, NON_PRESET_FILENAMES


@dataclass(frozen=True)
class Preset:
    id: str
    path: Path
    actions: list[dict]

def _read_preset_actions(path: Path) -> list[dict] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not data:
        return None
    _, actions = next(iter(data.items()))
    return actions if isinstance(actions, list) else None

def find_inconsistent_folders(output_root: Path) -> list[Path]:
    return sorted({p.parent for p in output_root.rglob(REPORT_FILENAME)})
    
def load_folder_presets(folder: Path) -> list[Preset]:
    presets = []
    for path in sorted(folder.glob("*.json")):
        if path.name in NON_PRESET_FILENAMES:
            continue
        actions = _read_preset_actions(path)
        if actions is not None:
            presets.append(Preset(id=path.name, path=path, actions=actions))
    return presets

def load_all_presets(output_root: Path) -> list[Preset]:
    presets = []
    for path in sorted(output_root.rglob("*.json")):
        if path.name == REPORT_FILENAME or path.name in NON_PRESET_FILENAMES:
            continue
        actions = _read_preset_actions(path)
        if actions is not None:
            rel_id = str(path.relative_to(output_root).with_suffix(""))
            presets.append(Preset(id=rel_id, path=path, actions=actions))
    return presets