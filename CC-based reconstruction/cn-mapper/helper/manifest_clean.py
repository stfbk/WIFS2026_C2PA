"""
Normalize a C2PA manifest by dropping certain actions that are not relevant to the
preset DB comparison. This is done before the manifest is passed to cn_mapper.

  1. Drop actions whose "action" is in EXCLUDED_ACTIONS.
  2. Drop actions with no (or empty) "parameters".
  3. For Lightroom only: drop "label-only" entries -- actions whose *value* parameter (the key ending in ".value", e.g. "com.adobe.acr.value") is
     just a preset display-name placeholder rather than a real edit value, e.g.: {"com.adobe.acr": "Look", "com.adobe.acr.value": "None to Modern 04"}

Order and duplicate actions are preserved.
"""

EXCLUDED_ACTIONS = {"c2pa.opened"}
IGNORE_LR_NAMES = {"preset", "none to"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matches_ignore_list(text: str) -> bool:
    """True if any ignore term is contained within *text* (case-insensitive)."""
    normalized = text.strip().lower()
    return any(term in normalized for term in IGNORE_LR_NAMES)

def _is_preset_lr(parameters: dict) -> bool:
    """
    True if *parameters* is a single name/value pair where either side (case-insensitive) matches a known preset-label name or value
    (e.g. com.adobe.acr: "Preset" / com.adobe.acr.value: "None to TM01", or "None to B&W Green Filter v2").
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
    Order and duplicate actions are preserved:    
      - Drop excluded actions (c2pa.opened)
      - Drop entries with no "parameters"
      - [Lightroom only] Drop preset-label-only entries (e.g. c2pa.filtered whose only info is the preset's display name).  
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
