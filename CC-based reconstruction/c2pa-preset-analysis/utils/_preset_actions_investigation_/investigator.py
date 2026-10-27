"""
iterate over all presets in ./results/_preset_actions_ and check common actions to all presets
expectation: c2pa.coloradjustment & c2pa.filtered should be the most common actions, compute also che most common parameters

save the data as a dict: {
    'action': {
        'param_name: value
        }
}

done for each preset so it's easier to comparer

"""

import argparse
import copy     
import json
import sys
from datetime import datetime
from pathlib import Path
import pprint


def _get_raw_actions(manifest_json: dict) -> list[dict]:
    """Extract all actions from the active manifest's c2pa.actions assertions."""
    actions: list[dict] = []
    manifests    = manifest_json.get("manifests", {})
    active_label = manifest_json.get("active_manifest")
    candidates   = (
        [manifests[active_label]]
        if active_label and active_label in manifests
        else list(manifests.values())
    )
    for manifest in candidates:
        for assertion in manifest.get("assertions", []):
            if not assertion.get("label", "").startswith("c2pa.actions"):
                continue
            for entry in assertion.get("data", {}).get("actions", []):
                params = dict(entry.get("parameters", {}))
                desc   = entry.get("description", {})
                if desc:
                    params["_description"] = desc
                actions.append({"action": entry.get("action", ""), "parameters": params})
    return actions

# ---------------------------------------------------------------------------
# Preset library loading
# ---------------------------------------------------------------------------

def load_preset_library(actions_dir: Path) -> list[dict]:
    """
    Walk *actions_dir* and return one record per preset JSON file.

    Expected layout::

        <actions_dir>/<tag>/<sub_tag>/<version>/preset_*.json

    The ``Preset``-type ``c2pa.filtered`` action is stripped from every
    loaded preset before matching, so the comparison is based purely on
    the editing operations — not the preset label.
    """
    library: list[dict] = []

    for json_file in sorted(actions_dir.rglob("preset_*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  {('[WARN]')} Cannot load {json_file}: {exc}", file=sys.stderr)
            continue

        actions = payload.get("actions", [])
        if not actions:
            continue

        # Strip the preset-name action so matching works even when it is absent
        # actions = _strip_preset_action(actions)

        rel     = json_file.relative_to(actions_dir)
        parts   = rel.parts
        tag     = parts[0] if len(parts) > 0 else "unknown"
        sub_tag = parts[1] if len(parts) > 1 else "unknown"
        version = (parts[2].replace("_actions", "").replace("_action", "") if len(parts) > 2 else "unknown")
        stem    = payload.get("preset", f"{tag}_{sub_tag}_{version}")

        library.append({
            "tag":     tag,
            "sub_tag": sub_tag,
            "version": version,
            "stem":    stem,
            "path":    json_file,
            "actions": actions,
        })

    return library

def main() -> None:
    presets_dir = Path("./results/_preset_actions_")
    out_path = Path('./collapsed_lr_presets.json')
    presets_library = load_preset_library(presets_dir)
    
    print(f"Loaded {len(presets_library)} presets")
    # print(f"first_preset: {presets_library[0]}")
    # breakpoint()
    
    collapsed_presets: dict = {}

    # stem: {dict of actions}

    for preset in presets_library:
        collapsed_actions: dict = {}
        # print(f"preset: {preset}")
        # breakpoint()
        preset_name = preset['stem']
        actions = preset['actions']
        if preset_name not in collapsed_presets:
            collapsed_presets[preset_name] = {}
        for act in actions:
            action_name = act['action']
            action_param = act['parameters']

            param_key = action_param.get('com.adobe.acr')
            param_value = action_param.get('com.adobe.acr.value')

            if action_name not in collapsed_actions:
                collapsed_actions[action_name] = {}
            
            if param_key:
                collapsed_actions[action_name][param_key] = param_value

        collapsed_presets[preset_name] = collapsed_actions


    pprint.pprint(collapsed_presets)


    # save collapsed_presets into json file
    json_string = json.dumps(collapsed_presets, indent=2)
    out_path.write_text(json_string, encoding="utf-8")
    print(f"Successfully saved to {out_path.resolve()}")


if __name__ == "__main__":
    main()