"""
CN_MAPPER: compare an image's extracted actions against the preset database
for its identified tool, and classify the result.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Category, ClassificationRecord
from helper.preset_match import score_preset

TOOL_FOLDERS = {
    "lightroom": "Lightroom",
    "adobe photoshop": "Adobe Photoshop",
}

SHORTLIST_SIZE = 5

def _iter_presets(tool_dir: Path):
    """
    (identifier, actions) for every preset under tool_dir
    """
    for file in sorted(tool_dir.rglob("*.json")):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        relative = file.relative_to(tool_dir).with_suffix("")
        multiple = len(data) > 1
        for key, preset_actions in data.items():
            identifier = f"{relative}::{key}" if multiple else str(relative)
            yield identifier, preset_actions


def cn_mapper(image_name: str, actions: list[dict], tool: str, database_path: Path) -> ClassificationRecord:
    folder_name = TOOL_FOLDERS.get(tool)
    if folder_name is None:
        return ClassificationRecord(
            image=image_name,
            category=Category.UNSUPPORTED_TOOL,
            message=f"unsupported tool: no preset folder mapped for {tool!r}",
            tool=tool,
        )

    tool_dir = database_path / folder_name
    if not tool_dir.is_dir():
        return ClassificationRecord(
            image=image_name,
            category=Category.NONE_IN_DB,
            message=f"no preset database found for {tool} at {tool_dir}",
            tool=tool,
        )

    exact_matches: list[str] = []
    shortlist: list[dict] = []
    best_partial = None  # MatchScore of the best non-exact hit, for top-level fields

    # Deliberately do not stop at the first hit: identical presets can be
    # duplicated under different names in the database.
    for identifier, preset_actions in _iter_presets(tool_dir):
        score = score_preset(preset_actions, actions)
        if score.total_actions == 0:
            continue

        if score.matching_actions == score.total_actions and score.extra_actions == 0:
            exact_matches.append(identifier)
        elif score.matching_actions > 0:
            shortlist.append({"preset": identifier, **asdict(score)})
            if best_partial is None or score.match_percentage > best_partial.match_percentage:
                best_partial = score

    if exact_matches:
        return ClassificationRecord(
            image=image_name,
            category=Category.SAME,
            message=f"{image_name} matched: {tool} in {', '.join(exact_matches)}",
            tool=tool,
            preset_names=exact_matches,
            matching_actions=len(actions),
            total_actions=len(actions),
            active_total_actions=len(actions),
            extra_actions=0,
            match_percentage=100.0,
        )

    if shortlist:
        shortlist.sort(key=lambda row: row["match_percentage"], reverse=True)
        shortlist = shortlist[:SHORTLIST_SIZE]
        top = shortlist[0]
        return ClassificationRecord(
            image=image_name,
            category=Category.SIMILAR,
            message=f"{image_name} similar to: {tool} preset {top['preset']} "
                    f"({top['match_percentage']:.1f}% match)",
            tool=tool,
            preset_names=[top["preset"]],
            matching_actions=top["matching_actions"],
            total_actions=top["total_actions"],
            active_total_actions=top["active_total_actions"],
            extra_actions=top["extra_actions"],
            match_percentage=top["match_percentage"],
            shortlist=shortlist,
        )

    return ClassificationRecord(
        image=image_name,
        category=Category.NONE_IN_DB,
        message=f"{image_name}: no matching {tool} preset found in database",
        tool=tool,
        active_total_actions=len(actions),
    )