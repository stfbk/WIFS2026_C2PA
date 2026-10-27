"""
Manifest I/O, extraction, and graph walking.

This module reads and traverses manifest data structures.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def read_manifest_store(image_path: Path) -> dict | None:
    """
    Run c2patool on *image_path* and return the parsed JSON manifest store.
    Returns None if no manifest is present or the output is not valid JSON.
    """
    result = subprocess.run(
        ["c2patool", str(image_path)],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None

def load_manifest_store(path: Path) -> dict | None:
    """
    Load a manifest store from a pre-exported JSON file.
    Useful for analysing manifests without re-running c2patool.
    Returns None on missing file or invalid JSON.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def get_active_manifest(store: dict) -> dict | None:
    """
    Return the active manifest dict from a manifest store, or None if not present.
    """
    manifests = store.get("manifests", {})
    active_label = store.get("active_manifest")
    if not active_label or active_label not in manifests:
        return None
    return manifests[active_label]

def get_claim_generator_info_name(store: dict) -> str | None:
    """
    Return the claim generator name (e.g. "Lightroom") from a manifest store's
    active manifest, or None if there's no active manifest or no name present.
    """
    active_manifest = get_active_manifest(store)
    if active_manifest is None:
        return None
    info = active_manifest.get("claim_generator_info", [])
    return info[0].get("name") if info else "unknown"

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def get_raw_actions(manifest: dict) -> list[dict]:
    """
    Return raw action objects from all c2pa.actions / c2pa.actions.v2 assertions,
    preserving order and all fields (including digitalSourceType).
    """
    raw: list[dict] = []
    for assertion in manifest.get("assertions", []):
        if assertion.get("label", "") not in ("c2pa.actions", "c2pa.actions.v2"):
            continue
        raw.extend(assertion.get("data", {}).get("actions", []))
    return raw

def extract_ingredient_manifest_labels(manifest: dict) -> list[str]:
    """
    Return manifest labels referenced as ingredients (v1/v2 and v3).
    """
    labels: list[str] = []
    seen: set[str] = set()

    def add(label: str) -> None:
        if label and label not in seen:
            seen.add(label)
            labels.append(label)

    # v1/v2: references inside assertions
    for assertion in manifest.get("assertions", []):
        if not assertion.get("label", "").startswith("c2pa.ingredient"):
            continue
        data = assertion.get("data", {})
        ref  = (
            data.get("c2pa_manifest", {}).get("url", "")
            or data.get("relationship", {}).get("url", "")
        )
        if ref and "self#jumbf=/c2pa/" in ref:
            add(ref.split("self#jumbf=/c2pa/", 1)[1].split("/")[0])

    # v3: top-level ingredients array
    for ingredient in manifest.get("ingredients", []):
        add(ingredient.get("active_manifest", ""))

    return labels