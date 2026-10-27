"""
Cross-preset action-slot summary for one folder.

Aligns every preset's action list positionally (action #1, #2, ...) and classifies each slot as: 
fully matched across all presets, same action but split on value(s), different action type present, or missing in some presets (list longer in some than others).
Consecutive slots sharing a status are grouped into ranges (e.g. "actions 1-3 fully matched").
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .flatten import flatten_parameters
from .loader import Preset
from .constants import STATUS_FULL_MATCH, STATUS_LABELS, STATUS_PARTIAL_PRESENCE, STATUS_TYPE_MISMATCH, STATUS_VALUE_MISMATCH


@dataclass
class SlotResult:
    index: int
    status: str
    action_names: dict[str, str | None]
    detail: str = ""

def _slot_action(actions: list[dict], index: int) -> dict | None:
    return actions[index] if index < len(actions) else None

def summarize_folder_slots(presets: list[Preset]) -> list[SlotResult]:
    """presets: every preset variant found in one folder."""
    preset_ids = [p.id for p in presets]
    actions_by_id = {p.id: p.actions for p in presets}
    max_len = max((len(a) for a in actions_by_id.values()), default=0)

    slots: list[SlotResult] = []
    for index in range(max_len):
        per_preset = {pid: _slot_action(actions_by_id[pid], index) for pid in preset_ids}
        present = {pid: a for pid, a in per_preset.items() if a is not None}
        action_names = {pid: (a.get("action") if a else None) for pid, a in per_preset.items()}

        if len(present) < len(preset_ids):
            missing = [pid for pid in preset_ids if per_preset[pid] is None]
            slots.append(SlotResult(
                index, STATUS_PARTIAL_PRESENCE, action_names,
                detail=f"missing/new for {len(missing)}/{len(preset_ids)} preset(s): {', '.join(missing)}",
            ))
            continue

        names_present = {a.get("action") for a in present.values()}
        if len(names_present) > 1:
            slots.append(SlotResult(index, STATUS_TYPE_MISMATCH, action_names, detail=f"types seen: {', '.join(sorted(names_present))}"))
            continue

        flattened = {pid: flatten_parameters(a.get("parameters", {}) or {}) for pid, a in present.items()}
        all_params = sorted({p for f in flattened.values() for p in f})

        mismatched_params = []
        for param in all_params:
            values = {flattened[pid].get(param) for pid in preset_ids}
            if len(values) > 1:
                groups: dict[Any, list[str]] = {}
                for pid in preset_ids:
                    groups.setdefault(flattened[pid].get(param), []).append(pid)
                breakdown = "; ".join(f"{len(ids)}={val!r}" for val, ids in groups.items())
                mismatched_params.append(f"{param} ({breakdown})")

        if mismatched_params:
            slots.append(SlotResult(index, STATUS_VALUE_MISMATCH, action_names,
                                     detail="; ".join(mismatched_params)))
        else:
            slots.append(SlotResult(index, STATUS_FULL_MATCH, action_names))

    return slots

def _slot_label(slot: SlotResult) -> str:
    names = {n for n in slot.action_names.values() if n}
    return next(iter(names)) if len(names) == 1 else "varies"

def group_consecutive(slots: list[SlotResult]) -> list[tuple[int, int, str, list[SlotResult]]]:
    groups: list[tuple[int, int, str, list[SlotResult]]] = []
    for slot in slots:
        if groups and groups[-1][2] == slot.status:
            start, _, status, members = groups[-1]
            groups[-1] = (start, slot.index, status, members + [slot])
        else:
            groups.append((slot.index, slot.index, slot.status, [slot]))
    return groups

def format_slot_summary(slots: list[SlotResult]) -> str:
    if not slots:
        return "No actions to summarize.\n"

    lines = []
    for start, end, status, members in group_consecutive(slots):
        label = f"Action {start + 1}" if start == end else f"Actions {start + 1}-{end + 1}"
        status_label = STATUS_LABELS[status]

        if status == STATUS_FULL_MATCH:
            names = sorted({_slot_label(m) for m in members})
            names_str = f" ({', '.join(names)})" if len(names) <= 3 else ""
            lines.append(f"  {label}: {status_label}{names_str}")
        else:
            lines.append(f"  {label}: {status_label}")
            for m in members:
                lines.append(f"    - action #{m.index + 1} ({_slot_label(m)}): {m.detail}")

    return "\n".join(lines) + "\n"

def slot_summary_to_dict(slots: list[SlotResult]) -> list[dict]:
    """JSON-serializable form of the grouped slot summary."""
    entries = []
    for start, end, status, members in group_consecutive(slots):
        entries.append({
            "actions": [start + 1, end + 1] if start != end else [start + 1],
            "status": status,
            "details": [m.detail for m in members if m.detail] or None,
        })
    return entries