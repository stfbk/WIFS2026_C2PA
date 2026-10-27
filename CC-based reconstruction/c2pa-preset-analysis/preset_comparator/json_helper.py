"""
JSON files loading and serialisation helpers
"""
 
from __future__ import annotations
 
import json
import sys
from pathlib import Path
 
from .display import _y, _rb


# ---------------------------------------------------------------------------
# Loading preset_actions json
# ---------------------------------------------------------------------------

def load_preset_files(actions_dir: Path) -> list[dict]:
    """
    Walk *actions_dir* and return one record per preset JSON file found.
    Path pattern: <actions_dir>/<tag>/<sub_tag>/<version>/preset_*.json
    Each record
        {
            "tag":        str,    e.g. "seasons"
            "sub_tag":    str,    e.g. "autumn"
            "version":    str,    e.g. "TM01"
            "stem":       str,    e.g. "seasons_autumn_TM01"
            "path":       Path,
            "actions":    list[dict],
            "full_match": bool | None,
        }
    """
    presets: list[dict] = []

    for json_file in sorted(actions_dir.rglob("preset_*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  {_y('WARN')} Cannot load {json_file}: {exc}", file=sys.stderr)
            continue

        actions = payload.get("actions", [])
        if not actions:
            print(f"  {_y('WARN')} No actions in {json_file} — skipping.", file=sys.stderr)
            continue

        # parts = (tag, sub_tag, version, filename)
        rel   = json_file.relative_to(actions_dir)
        parts = rel.parts

        tag     = parts[0] if len(parts) > 0 else "unknown"
        sub_tag = parts[1] if len(parts) > 1 else "unknown"
        # strip any trailing "_actions" suffix if present (backward-compat)
        version = (parts[2].replace("_actions", "").replace("_action", "")
                   if len(parts) > 2 else "unknown")

        stem = payload.get("preset", f"{tag}_{sub_tag}_{version}")

        presets.append({
            "tag":        tag,
            "sub_tag":    sub_tag,
            "version":    version,
            "stem":       stem,
            "path":       json_file,
            "actions":    actions,
            "full_match": payload.get("full_match", None),
        })

    return presets



# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json(presets, inter, cross, actions_dir, timestamp):
    tags     = sorted({p["tag"]     for p in presets})
    sub_tags = sorted({p["sub_tag"] for p in presets})

    def _serialise_level(level_result):
        """Convert level result to JSON-safe dict (drop Path objects)."""
        out = dict(level_result)
        out["groups"] = [dict(g) for g in level_result["groups"]]
        return out

    return {
        "analysis": {
            "timestamp":     timestamp,
            "actions_dir":   str(actions_dir),
            "total_presets": len(presets),
            "tags":          tags,
            "sub_tags":      sub_tags,
        },
        "global_verdict": {
            
            "inter_sub_tag_pass": inter["overall_pass"],
            "cross_tag_pass":     cross["overall_pass"],
            "all_pass": (
                # intra["overall_pass"]
                inter["overall_pass"]
                and cross["overall_pass"]
            ),
            "interpretation": (
                "PASS = all compared pairs are DIFFERENT — "
                "each preset has a unique action signature."
            ),
        },
        "preset_index": [
            {
                "tag":        p["tag"],
                "sub_tag":    p["sub_tag"],
                "version":    p["version"],
                "stem":       p["stem"],
                "path":       str(p["path"]),
                "n_actions":  len(p["actions"]),
                "full_match": p["full_match"],
            }
            for p in presets
        ],
       
        "inter_sub_tag": {
            "description": (
                "All (sub_tag_A × sub_tag_B) version crosses within "
                "the same tag. e.g. seasons: autumn/* vs summer/*."
            ),
            **_serialise_level(inter),
        },
        "cross_tag": {
            "description": (
                "All presets in tag_A crossed against all presets in tag_B. "
                "e.g. seasons/* vs style/*."
            ),
            **_serialise_level(cross),
        },
    }