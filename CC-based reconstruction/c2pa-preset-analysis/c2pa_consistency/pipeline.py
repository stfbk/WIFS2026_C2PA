"""Orchestration: one preset folder in, JSON file(s) out."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

from .manifest import read_manifest_store, get_active_manifest, get_raw_actions, get_claim_generator_info_name
from .actions import filter_actions, is_lightroom
from .compare import cluster_action_lists
from .writer import write_clusters
from .constants import IMAGE_EXTENSIONS


@dataclass
class FolderResult:
    folder: Path
    output_dir: Path
    image_count: int
    preset_count: int
    # Populated only when preset_count > 1, so the analyzer can build a
    # per-image diff table without re-reading manifests from disk.
    action_lists: dict[str, list[dict]] | None = None

    @property
    def is_consistent(self) -> bool:
        return self.preset_count <= 1

def analyse_folder(folder: Path, *, input_root: Path, output_root: Path) -> None:
    action_lists: dict[str, list[dict]] = {}
    software = None

    for image_path in sorted(folder.iterdir()):
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        store = read_manifest_store(image_path)
        if not store:
            print(f"  ! no manifest for {image_path.name}, skipping")
            continue

        manifest = get_active_manifest(store)
        if manifest is None:
            print(f"  ! active manifest missing for {image_path.name}, skipping")
            continue

        if software is None:
            software = get_claim_generator_info_name(store)

        action_lists[image_path.name] = filter_actions(
            get_raw_actions(manifest), is_lightroom=is_lightroom(software)
        )

    if not action_lists:
        return

    clusters = cluster_action_lists(action_lists)
    image_count = len(action_lists)
    preset_count = len(clusters)

    out_dir = write_clusters(clusters, folder=folder, input_root=input_root, output_root=output_root, software=software)
   
    return FolderResult(folder=folder, output_dir=out_dir, image_count=image_count, preset_count=preset_count, action_lists=action_lists if preset_count > 1 else None)
