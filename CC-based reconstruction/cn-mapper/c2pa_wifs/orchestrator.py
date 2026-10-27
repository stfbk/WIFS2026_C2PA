from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from helper.manifest import get_active_manifest, get_claim_generator_info_name, read_manifest_store, get_raw_actions
from helper.manifest_clean import filter_actions

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}
)

@dataclass
class ImageAnalysis:
    image: str
    tool: Optional[str]      # e.g. "lightroom", "adobe photoshop", or None if unknown
    actions: list[dict]

def analyse_image(image_path: Path) -> Optional[ImageAnalysis]:
    """
    Extract and normalize the action list for a single image.
    Returns None if the file isn't a supported image, has no manifest,
    or has no active manifest.
    """
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        return None

    store = read_manifest_store(image_path)
    if not store:
        return None

    manifest = get_active_manifest(store)
    if manifest is None:
        return None

    tool_name = get_claim_generator_info_name(store)
    is_lightroom = bool(tool_name) and tool_name.lower() == "lightroom"

    actions = filter_actions(get_raw_actions(manifest), is_lightroom=is_lightroom)
    return ImageAnalysis(image=image_path.name, tool=tool_name, actions=actions)