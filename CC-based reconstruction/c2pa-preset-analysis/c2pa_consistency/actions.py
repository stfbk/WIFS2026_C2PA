"""
Action filtering.
Keeps the raw action list mostly intact, dropping bookkeeping / label-only
entries so what's left reflects real edits.
"""
from __future__ import annotations

from .constants import EXCLUDED_ACTIONS, IGNORE_LR_NAMES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_lightroom(software: str) -> bool:
    return "lightroom" in software.lower()

def _matches_ignore_list(text: str) -> bool:
    """True if any ignore term is contained within *text* (case-insensitive)."""
    normalized = text.strip().lower()
    return any(term in normalized for term in IGNORE_LR_NAMES)

def _is_preset_lr(parameters: dict) -> bool:
    """
    True if *parameters* is a single name/value pair where either side (case-insensitive) matches a
    known preset-label name or value (e.g. com.adobe.acr: "Preset" /
    com.adobe.acr.value: "None to TM01", or "None to B&W Green Filter v2").
    """

    for key, value in parameters.items():

        matches = _matches_ignore_list(value)

        if matches:
            return True

    return False

# ---------------------------------------------------------------------------
# Actions filtering
# ---------------------------------------------------------------------------

def filter_actions(raw_actions: list[dict], *, is_lightroom: bool) -> list[dict]:
    """
    Keep actions as-is, except: drop excluded actions (c2pa.opened), drop
    entries with no "parameters", and -- for Lightroom only -- drop
    preset-label-only entries (e.g. c2pa.filtered whose only info is the
    preset's display name). Order and duplicate actions are preserved.
    """
    kept: list[dict] = []
    for raw in raw_actions:
        action_name = raw.get("action")
        parameters = raw.get("parameters")
        if not action_name or not parameters:
            continue
        if action_name in EXCLUDED_ACTIONS:
            continue
        if is_lightroom and _is_preset_lr(parameters):
            continue
        kept.append({"action": action_name, "parameters": parameters})
    return kept
