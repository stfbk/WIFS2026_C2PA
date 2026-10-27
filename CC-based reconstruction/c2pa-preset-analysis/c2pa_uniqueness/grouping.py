"""
Assign each preset to exactly one group. The most constrained (finest) equivalence class it shares with at least one other
preset. Presets matching nobody at any level are reported as "unique".
"""
from __future__ import annotations

from .constants import ( CATEGORY_FULLY_IDENTICAL, CATEGORY_DIFFERS_AT_VALUES, CATEGORY_DIFFERS_AT_PARAMETER_ORDER, CATEGORY_DIFFERS_AT_PARAMETER_NAMES, CATEGORY_DIFFERS_AT_ACTION_ORDER, CATEGORY_DIFFERS_AT_ACTION_TYPES, KEY_UNIQUE)
from .flatten import flatten_parameters
from .loader import Preset


def _sig_count(actions: list[dict]) -> object:
    return len(actions)

def _sig_types_unordered(actions: list[dict]) -> object:
    return tuple(sorted(a.get("action", "") for a in actions))

def _sig_types_ordered(actions: list[dict]) -> object:
    return tuple(a.get("action", "") for a in actions)

def _sig_param_names_unordered(actions: list[dict]) -> object:
    return tuple(
        (a.get("action", ""), tuple(sorted(flatten_parameters(a.get("parameters") or {}).keys())))
        for a in actions
    )

def _sig_param_names_ordered(actions: list[dict]) -> object:
    return tuple(
        (a.get("action", ""), tuple(flatten_parameters(a.get("parameters") or {}).keys()))
        for a in actions
    )

def _sig_full_identity(actions: list[dict]) -> object:
    return tuple(
        (a.get("action", ""), tuple((k, repr(v)) for k, v in flatten_parameters(a.get("parameters") or {}).items()))
        for a in actions
    )

# Each signature strictly implies the ones below it (e.g. equal param-names-ordered implies equal action-types-ordered
# implies equal count)
_ROUNDS = [
            (CATEGORY_FULLY_IDENTICAL, _sig_full_identity), 
            (CATEGORY_DIFFERS_AT_VALUES, _sig_param_names_ordered), 
            (CATEGORY_DIFFERS_AT_PARAMETER_ORDER, _sig_param_names_unordered),
            (CATEGORY_DIFFERS_AT_PARAMETER_NAMES, _sig_types_ordered), 
            (CATEGORY_DIFFERS_AT_ACTION_ORDER, _sig_types_unordered), 
            (CATEGORY_DIFFERS_AT_ACTION_TYPES, _sig_count)
        ]

def _build_groups(buckets: dict[object, list[str]], remaining: dict[str, Preset]) -> dict[str, dict]:
    """
    Turn {signature: [ids]} buckets of size >= 2 into {"Group_1": {"action_count": N, "presets": [ids]}, ...}.
    """
    groups: dict[str, dict] = {}
    index = 1
    for ids in buckets.values():
        if len(ids) <= 1:
            continue
        action_count = len(remaining[ids[0]].actions)
        groups[f"Group_{index}"] = {"action_count": action_count, "presets": sorted(ids)}
        index += 1
    return groups

def group_presets(presets: list[Preset]) -> dict:
    """
    Returns: {category: {"Group_1": {"action_count": N, "presets": [ids]}, ...}}
    for each of the 6 categories where at least one group of 2+ presets was
    found, plus KEY_UNIQUE: [ids] for presets matching nobody at all.
    """
    remaining = {p.id: p for p in presets}
    result: dict = {}

    for category, sig_fn in _ROUNDS:
        buckets: dict[object, list[str]] = {}
        for pid, preset in remaining.items():
            key = sig_fn(preset.actions)
            buckets.setdefault(key, []).append(pid)

        groups = _build_groups(buckets, remaining)
        if groups:
            result[category] = groups
            for group in groups.values():
                for pid in group["presets"]:
                    del remaining[pid]

    if remaining:
        result[KEY_UNIQUE] = sorted(remaining.keys())

    return result