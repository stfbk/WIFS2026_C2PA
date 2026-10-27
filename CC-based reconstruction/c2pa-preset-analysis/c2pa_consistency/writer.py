"""Write one JSON file per action-list cluster, mirroring the input tree."""
from __future__ import annotations
import json
from pathlib import Path
from .naming import relative_parts, preset_key_for

def write_clusters(clusters: list[dict], *, folder: Path, input_root: Path, output_root: Path, software: str) -> Path:
    out_dir = output_root / software
    out_dir = out_dir.joinpath(*relative_parts(folder, input_root))
    out_dir.mkdir(parents=True, exist_ok=True)

    key = preset_key_for(folder, input_root)

    for index, cluster in enumerate(clusters, start=1):
        suffix = "" if index == 1 else f"_variant{index}"
        out_path = out_dir / f"{key}{suffix}.json"
        out_path.write_text(
            json.dumps({key: cluster["actions"]}, indent=2), encoding="utf-8"
        )
        # print(f"  wrote {out_path} ({len(cluster['images'])} image(s): {', '.join(cluster['images'])})")

    return out_dir