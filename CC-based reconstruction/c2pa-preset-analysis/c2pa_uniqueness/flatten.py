"""Shared parameter-flattening logic: generic K / K.value pairing."""
from __future__ import annotations
from .constants import VALUE_SUFFIX


def flatten_parameters(parameters: dict) -> dict[str, object]:
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