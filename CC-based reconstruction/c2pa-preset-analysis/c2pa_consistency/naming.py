"""Derive a stable key for a fingerprint from its folder path."""
from __future__ import annotations
from pathlib import Path

def relative_parts(folder: Path, input_root: Path) -> tuple[str, ...]:
    parts = folder.relative_to(input_root).parts
    return parts[1:] if len(parts) > 1 else parts


def preset_key_for(folder: Path, input_root: Path) -> str:
    return "_".join(relative_parts(folder, input_root))