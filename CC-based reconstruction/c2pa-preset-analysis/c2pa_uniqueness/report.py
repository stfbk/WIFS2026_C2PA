"""Write grouping and slot-summary results as JSON, print terminal summaries."""
from __future__ import annotations
import json
from pathlib import Path


def print_summary(title: str, grouping: dict) -> None:
    print(title)
    for category, groups in grouping.items():
        if isinstance(groups, dict):
            total = sum(len(ids) for ids in groups.values())
            print(f"  {category}: {len(groups)} group(s), {total} preset(s)")
            for group_name, group in groups.items():
                print(f"    {group_name} ({group['action_count']} action(s)): {len(group['presets'])} preset(s)")
        else:
            print(f"  {category}: {len(groups)} preset(s)")
    print()

def write_json_report(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")