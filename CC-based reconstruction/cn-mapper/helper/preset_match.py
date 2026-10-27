"""
Wildcard-aware comparison between a database preset's action list and an
image's extracted action list.

A preset parameter value of "x_variable" is a placeholder meaning "this
value differs between real-world exports of the preset" -- the key must be
present on the extracted side, but its value is never compared.
"""
from __future__ import annotations

from dataclasses import dataclass

WILDCARD = "x_variable"


def actions_match(preset_action: dict, extracted_action: dict) -> bool:
    """True if extracted_action satisfies preset_action, honoring wildcards."""
    if preset_action.get("action") != extracted_action.get("action"):
        return False

    preset_params = preset_action.get("parameters", {})
    extracted_params = extracted_action.get("parameters", {})

    for key, value in preset_params.items():
        if key not in extracted_params:
            return False
        if value != WILDCARD and extracted_params[key] != value:
            return False

    return True


@dataclass
class MatchScore:
    matching_actions: int       # preset actions found in the extracted list
    total_actions: int          # size of the preset
    active_total_actions: int   # size of the extracted (active) action list
    extra_actions: int          # extracted actions not accounted for by the preset
    match_percentage: float     # matching_actions / total_actions * 100


def score_preset(preset_actions: list[dict], extracted_actions: list[dict]) -> MatchScore:
    """
    Greedy one-to-one match: each preset action consumes at most one
    extracted action. Order-independent -- mirrors compare.py's philosophy
    but tolerates preset wildcards, which exact-equality clustering can't.
    """
    used: set[int] = set()
    matched = 0

    for preset_action in preset_actions:
        for i, extracted_action in enumerate(extracted_actions):
            if i in used:
                continue
            if actions_match(preset_action, extracted_action):
                used.add(i)
                matched += 1
                break

    total = len(preset_actions)
    return MatchScore(
        matching_actions=matched,
        total_actions=total,
        active_total_actions=len(extracted_actions),
        extra_actions=len(extracted_actions) - len(used),
        match_percentage=(matched / total * 100) if total else 0.0,
    )