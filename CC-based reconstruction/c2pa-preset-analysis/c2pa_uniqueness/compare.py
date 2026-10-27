"""
Staged comparison between two presets' action lists, cheapest/coarsest checks first. Stops at the first stage where the two presets diverge; only
when every earlier stage matches do we fall through to comparing exact values (the worst case, and the only one requiring a full check).
"""
from __future__ import annotations
from dataclasses import dataclass

from .constants import (STAGE_ACTION_COUNT, STAGE_ACTION_TYPES, STAGE_ACTION_ORDER, STAGE_PARAMETER_NAMES,STAGE_PARAMETER_ORDER, STAGE_VALUES, VALUE_SUFFIX)


@dataclass(frozen=True)
class ComparisonResult:
    level: int | None   # stage index of first divergence; None = identical
    detail: str = ""

def _action_names(actions: list[dict]) -> list[str]:
    return [a.get("action", "") for a in actions]

def _flatten_parameter_names(parameters: dict) -> list[str]:
    """
    Generic name/value pairing: any key K with a sibling "K.value" means the real setting name is parameters[K] (covers Lightroom's com.adobe.acr /
    com.adobe.acr.value). Any other key is its own name (covers Photoshop's flat parameters). Order preserved as found.
    """
    names: list[str] = []
    consumed: set[str] = set()

    for key in parameters:
        value_key = f"{key}{VALUE_SUFFIX}"
        if value_key in parameters:
            names.append(str(parameters[key]))
            consumed.add(key)
            consumed.add(value_key)

    for key in parameters:
        if key in consumed:
            continue
        names.append(key)

    return names

def _flatten_parameters(parameters: dict) -> dict[str, object]:
    """Same pairing logic as _flatten_parameter_names, keeping values too."""
    flat: dict[str, object] = {}
    consumed: set[str] = set()

    for key, value in parameters.items():
        value_key = f"{key}{VALUE_SUFFIX}"
        if value_key in parameters:
            flat[str(value)] = parameters[value_key]
            consumed.add(key)
            consumed.add(value_key)

    for key, value in parameters.items():
        if key in consumed:
            continue
        flat[key] = value

    return flat

def compare_presets(actions_a: list[dict], actions_b: list[dict]) -> ComparisonResult:
    # Stage 0: action count
    if len(actions_a) != len(actions_b):
        return ComparisonResult(STAGE_ACTION_COUNT, f"{len(actions_a)} vs {len(actions_b)} actions")

    names_a = _action_names(actions_a)
    names_b = _action_names(actions_b)

    # Stage 1: action types (order-independent)
    if sorted(names_a) != sorted(names_b):
        return ComparisonResult(STAGE_ACTION_TYPES, "different action types present")

    # Stage 2: action order
    if names_a != names_b:
        return ComparisonResult(STAGE_ACTION_ORDER, "same action types, different order")

    # From here, actions are pairable by position (same type, same order).
    # Stage 3: parameter names (order-independent, per action)
    for index, (a, b) in enumerate(zip(actions_a, actions_b)):
        names_a3 = _flatten_parameter_names(a.get("parameters", {}) or {})
        names_b3 = _flatten_parameter_names(b.get("parameters", {}) or {})
        if sorted(names_a3) != sorted(names_b3):
            return ComparisonResult(
                STAGE_PARAMETER_NAMES,
                f"action #{index} ({names_a[index]}): different parameter names",
            )

    # Stage 4: parameter order, per action
    for index, (a, b) in enumerate(zip(actions_a, actions_b)):
        names_a4 = _flatten_parameter_names(a.get("parameters", {}) or {})
        names_b4 = _flatten_parameter_names(b.get("parameters", {}) or {})
        if names_a4 != names_b4:
            return ComparisonResult(
                STAGE_PARAMETER_ORDER,
                f"action #{index} ({names_a[index]}): same parameter names, different order",
            )

    # Stage 5: values - worst case, only reached if everything else matched
    for index, (a, b) in enumerate(zip(actions_a, actions_b)):
        flat_a = _flatten_parameters(a.get("parameters", {}) or {})
        flat_b = _flatten_parameters(b.get("parameters", {}) or {})
        if flat_a != flat_b:
            diffs = [k for k in flat_a if flat_a.get(k) != flat_b.get(k)]
            return ComparisonResult(
                STAGE_VALUES,
                f"action #{index} ({names_a[index]}): different value(s) for {', '.join(diffs)}",
            )

    return ComparisonResult(None, "identical")