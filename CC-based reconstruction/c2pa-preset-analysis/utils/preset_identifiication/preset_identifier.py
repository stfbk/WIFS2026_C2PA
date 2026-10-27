"""
Identify which Lightroom preset was applied to an image by matching its
C2PA manifest actions against the preset action library stored under
``_preset_actions_/``.

Use-case
--------
When Lightroom exports an image the ``c2pa.filtered`` action sometimes does
not carry the preset name in its parameters.  This script recovers the preset
identity by comparing the full action list (minus ``c2pa.opened``) against
every saved preset signature.  The first exact match is returned.

Matching strategy
-----------------
Two action lists are considered a match when:
  • They have the same number of actions.
  • Every action at every position has the same name AND the same parameters.

This is the same strict equality used in ``preset_comparison.py``.

Partial matching (similarity score) is also computed for every preset so
you can see the closest candidate even when no exact match exists.

Usage
-----
    # Identify preset from a single image
    python preset_identifier.py <image_path> [--actions-dir _preset_actions_]
                                              [--tool c2patool]
                                              [--output results/match.json]

    # Identify preset from a pre-extracted manifest JSON (skip c2patool)
    python preset_identifier.py --manifest <manifest.json>
                                [--actions-dir _preset_actions_]
                                [--output results/match.json]

Output
------
  - Coloured terminal summary.
  - JSON file with match details, similarity scores, and the full action list.
"""

import os
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from preset_comparator.display import _g, _r, _y, _b, _gb, _rb, SEP, SSEP
from preset_comparator.action_comparator import actions_equal
from c2pa_prescan.action_extractor import read_manifest_store, get_raw_actions, strip_opened, has_opened_first
from c2pa_prescan.analyzer import count_matching_actions
import copy


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# supported image file extensions 
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}
)

TOLERANCE = 0.05 # 5% tolerance on the actions parameters for a match

# ---------------------------------------------------------------------------
# Manifest / action extraction 
# ---------------------------------------------------------------------------

# def _run_c2patool(image_path: Path) -> dict | None:
    
#     """
#     Run c2patool on image_path and return the parsed JSON manifest store.
#     """
#     result = subprocess.run(
#         ["c2patool", str(image_path)],
#         capture_output=True,
#         text=True,
#     )
#     output = result.stdout.strip()
#     if not output:
#         return None
#     try:
#         return json.loads(output)
#     except json.JSONDecodeError:
#         return None


# def _extract_actions(manifest_json: dict) -> list[dict]:
#     """Extract all actions from the active manifest's c2pa.actions assertions."""
#     actions: list[dict] = []
#     manifests   = manifest_json.get("manifests", {})
#     active_label = manifest_json.get("active_manifest")

#     candidates = (
#         [manifests[active_label]]
#         if active_label and active_label in manifests
#         else list(manifests.values())
#     )
#     for manifest in candidates:
#         for assertion in manifest.get("assertions", []):
#             if not assertion.get("label", "").startswith("c2pa.actions"):
#                 continue
#             for entry in assertion.get("data", {}).get("actions", []):
#                 params = dict(entry.get("parameters", {}))
#                 desc   = entry.get("description", {})
#                 if desc:
#                     params["_description"] = desc
#                 actions.append({"action": entry.get("action", ""), "parameters": params})
#     return actions


# def _strip_opened(actions: list[dict]) -> list[dict]:
#     """Remove c2pa.opened — it carries image-specific hashes, not preset logic."""
#     return [a for a in actions if a["action"] != "c2pa.opened"]

def _strip_preset(actions: list[dict]) -> list[dict]:
    
    a = []
    # return [a for a in actions if a["action"] != "c2pa.opened"]
    for act in actions:
        # if act["action"] != "c2pa.filtered":
        #     continue
        acr_type = str(act["parameters"].get("com.adobe.acr", "")).strip().lower()
        if acr_type == "preset":
            continue
        a.append(act)
    return a


# ---------------------------------------------------------------------------
# Preset library loading
# ---------------------------------------------------------------------------

def load_preset_library(actions_dir: Path) -> list[dict]:
    """
    Walk *actions_dir* and load every preset JSON file.

    Expected layout::

        <actions_dir>/<tag>/<sub_tag>/<version>/preset_*.json

    Returns a list of records::

        {
            "tag":     str,
            "sub_tag": str,
            "version": str,
            "stem":    str,
            "path":    Path,
            "actions": list[dict],   # already stripped of c2pa.opened
        }
    """
    library: list[dict] = []

    # subdirs = [item for item in os.listdir(actions_dir) if item in ['seasons', 'style']] # add PRESETS const
    # # print(subdirs)
    # # breakpoint()
    # for subdir in subdirs:
    #     for json_file in sorted(Path(subdir).rglob("preset_*.json")): 
    #         print(f"{json_file}")

    # breakpoint()

    for json_file in sorted(actions_dir.rglob("preset_*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  {_y('[WARN]')} Cannot load {json_file}: {exc}", file=sys.stderr)
            continue

        actions = payload.get("actions", [])
        if not actions:
            continue
            
        actions = _strip_preset(actions) # remove the preset info to find best match

        rel   = json_file.relative_to(actions_dir)
        parts = rel.parts

        tag     = parts[0] if len(parts) > 0 else "unknown"
        sub_tag = parts[1] if len(parts) > 1 else "unknown"
        version = (parts[2].replace("_actions", "").replace("_action", "")
                   if len(parts) > 2 else "unknown")
        stem    = payload.get("preset", f"{tag}_{sub_tag}_{version}")

        library.append({
            "tag":     tag,
            "sub_tag": sub_tag,
            "version": version,
            "stem":    stem,
            "path":    json_file,
            "actions": actions,    # saved presets never include c2pa.opened
        })

    return library


# ---------------------------------------------------------------------------
# Tolerance-aware parameter comparison
# ---------------------------------------------------------------------------

def _deep_actions_equal(actList: list[dict], refList: list[dict]) -> bool:
    """Strict positional equality: same length, names, and all parameters."""
    # if len(a) != len(b):
    #     return False
    # return all(
    #     x["action"] == y["action"] and x["parameters"] == y["parameters"]
    #     for x, y in zip(a, b)
    # )

    # def actions_equal(actList: list[dict], refList: list[dict]) -> bool:
    
    """
        Compare two action lists (after removing c2pa.opened).
        - act_list
        - ref_list
        
        ----

        Create a deep copy of the current action list to avoid modifying the original.
        For each action in the reference list, find a matching action in the deep copied list.
        A matching action has the same 'action' name and identical 'parameters'.
        If a matching action is found, remove it from the deep copied list.
        After processing all reference actions, if there are any remaining actions in the deep copied list,
        it means they do not have a match in the reference list, and the function returns False
        If the deep copied list is empty, it means all actions have a match in the reference list, and the function returns True.
    """

    # print("list a", a)
    # print("list b", b)
    # breakpoint()

    deep_act_list = copy.deepcopy(actList)
    for ref_act in refList:
        # Find a matching action in the deep copied list
        matching_act = next((act for act in deep_act_list if act["action"] == ref_act["action"] and act["parameters"] == ref_act["parameters"]), None)
        if matching_act:
            # remove matching actions from deep list
            deep_act_list.remove(matching_act)
    
    if deep_act_list:
        print(f"{len(deep_act_list)} unmatched actions in current list: {deep_act_list}")
        print()
        return False
    return True

def _numeric(value) -> float | None:
    """Try to convert a value to float, return None if not possible."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def _deep_action_match_tolerance(actList: list[dict], refList: list[dict]) -> bool:
    
    """
        Compare two action lists (after removing c2pa.opened) with a tolerance on the parameters values.
        - act_list
        - ref_list
        
        -> dict of action and parameters + param values
        es: [{'action': 'c2pa.color_adjustments', 'parameters': {'com.adobe.acr': 'Blacks2012', 'com.adobe.acr.value': '20'}}, 
        {'action': 'c2pa.color_adjustments', 'parameters': {'com.adobe.acr': 'Clarity2012', 'com.adobe.acr.value': '30'}},
        ...]

        match on 2 levels:
        1. action name
        2. parameters 
            - same keys (name)
            - numeric values with a tolerance (e.g. 5% difference allowed)

        ----

        Create a deep copy of the current action list to avoid modifying the original.
        For each action in the reference list, find a matching action in the deep copied list.
        A matching action has the same 'action' name and parameters that are within a certain tolerance.
        If a matching action is found, remove it from the deep copied list.
        After processing all reference actions, if there are any remaining actions in the deep copied list,
        it means they do not have a match in the reference list, and the function returns False
        If the deep copied list is empty, it means all actions have a match in the reference list, and the function returns True.
    """

    # print("list a", a)
    # print("list b", b)
    # breakpoint()

    deep_act_list = copy.deepcopy(actList)
    # for ref_act in refList:
    #     # Find a matching action in the deep copied list
    #     matching_act = next((act for act in deep_act_list if act["action"] == ref_act["action"] and all(abs(float(act["parameters"].get(param, 0)) - float(ref_act["parameters"].get(param, 0))) <= TOLERANCE for param in ref_act["parameters"])), None)
    #     if matching_act:
    #         # remove matching actions from deep list
    #         deep_act_list.remove(matching_act)

    for ref_act in refList:
        for img_act in deep_act_list:
            if ref_act["action"] != img_act["action"]:
                continue
            # check parameters keys
            if set(ref_act["parameters"].keys()) != set(img_act["parameters"].keys()):
                continue
            # check parameters values with tolerance
            all_params_match = True
            for param in ref_act["parameters"]:
                # try to convert param values to numeric value and compare them with a tolerance
                ref_val = _numeric(ref_act["parameters"].get(param))
                img_val = _numeric(img_act["parameters"].get(param))
                if ref_val is not None and img_val is not None:
                    # 5% tolerance check on action parameters values (bigger or smaller values accepted withtin tolerance)
                    if abs(ref_val - img_val) > TOLERANCE * max(abs(ref_val), abs(img_val), 1): 
                        all_params_match = False
                        break
                else:
                    # if not numeric, check for exact match as strings
                    if ref_act["parameters"].get(param) != img_act["parameters"].get(param):
                        all_params_match = False
                        break
            if all_params_match:
                # remove matching actions from deep list
                deep_act_list.remove(img_act)
                break

    if deep_act_list:
        print(f"{len(deep_act_list)} unmatched actions in current list: {deep_act_list}")
        print()
        return False, len(deep_act_list)
    
    return True, len(deep_act_list)

def _similarity(image_actions: list[dict], preset_actions: list[dict]) -> float:
    """
    Return a similarity score in [0.0, 1.0].

    Score = matching_positions / max(len_a, len_b)

    A score of 1.0 means a full exact match.
    A score of 0.0 means nothing matches.
    """
    if not image_actions and not preset_actions:
        return None
    denom = max(len(image_actions), len(preset_actions))
    if denom == 0:
        return 0.0
    matches = sum(
        1 for a, b in zip(image_actions, preset_actions)
        if a["action"] == b["action"] and a["parameters"] == b["parameters"]
    )
    return round(matches / denom, 4)


def match_preset(
    image_actions: list[dict],
    library: list[dict],
) -> dict:
    """
    Compare *image_actions* (c2pa.opened already stripped) against every
    preset in *library*.

    Returns a result dict::

        {
            "exact_matches":   list[dict],   # all presets with score == 1.0
            "best_match":      dict | None,  # highest-scoring preset
            "best_score":      float,
            "candidates":      list[dict],   # all presets sorted by score desc
        }

    Each candidate::

        {
            "stem":      str,
            "tag":       str,
            "sub_tag":   str,
            "version":   str,
            "score":     float,    # 0.0 – 1.0
            "exact":     bool,
            "n_image":   int,      # number of image actions
            "n_preset":  int,      # number of preset actions
        }
    """
    candidates: list[dict] = []

    for preset in library:
        print(f"Checking img against {preset["stem"]}_{preset['tag']}_{preset['sub_tag']} actions")
        score = _similarity(image_actions, preset["actions"])
        exact, non_match_actions = _deep_action_match_tolerance(image_actions, preset["actions"])
        print(f"exact: {exact}, non_match_act: {non_match_actions}")
        # exact = _deep_actions_equal(image_actions, preset["actions"]) # actList vs refList
        count_match_act = count_matching_actions(image_actions, preset["actions"])
        candidates.append({
            "stem":     preset["stem"],
            "tag":      preset["tag"],
            "sub_tag":  preset["sub_tag"],
            "version":  preset["version"],
            "score":    score,
            "exact":    exact,
            "n_image_act":  len(image_actions),
            "n_preset_act": len(preset["actions"]),
            "match_act": count_match_act,
            # "non_matching_act": non_match_actions,
            "path":     str(preset["path"]),
        })

    # Sort by score descending, then by stem for deterministic ordering
    candidates.sort(key=lambda c: (-c["score"], c["stem"]))
    # candidates_non_match = candidates.sort(key=lambda c: (-c["non_matching_act"], c["stem"]))
    # if candidates_non_match:
    #     print("found some possibile candidated based on lowest number of non-matching actions")
    # else:
    #     print("no stored preset matched the image under analysis")
    # print(f"cadidated_non_match: {candidates_non_match}")

    exact_matches = [c for c in candidates if c["exact"]]
    best          = candidates[0] if candidates else None
    # best_non_match = candidates_non_match[0] if candidates_non_match else None
    best_score    = best["score"] if best else 0.0 # best_non_match['non_matching_act']

    print(f" BEST SCORE {best_score}")
    # breakpoint()

    return {
        "exact_matches": exact_matches,
        "best_match":    exact_matches[0] if exact_matches else best,
        "best_score":    best_score,
        "candidates":    candidates,
    }


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_result(
    image_path: Path | None,
    image_actions: list[dict],
    opened_first: bool,
    result: dict,
    timestamp: str,
) -> None:
    print(f"\n{_b(SEP)}")
    print(_b("  C2PA-PRESCAN — PRESET IDENTIFIER"))
    print(_b(SEP))

    if image_path:
        print(f"{('Image          :')} {image_path}")
    print(f"  {('Timestamp          :')} {timestamp}")
    print(f"  {('Actions found      :')} {len(image_actions)}  (c2pa.opened excluded)")
    print(f"  {('c2pa.opened first  :')} {opened_first}")
    print(f"  {('Presets in lib     :')} {len(result['candidates'])}")
    print()

    exact = result["exact_matches"]
    best  = result["best_match"]

    if exact:
        print(_gb(f"  ✓ EXACT MATCH{'ES' if len(exact) > 1 else ''} FOUND ({len(exact)})"))
        print()
        for m in exact:
            print(f"    {_gb('●')}  {_b(m['stem'])}")
            print(f"       tag     : {m['tag']}")
            print(f"       sub_tag : {m['sub_tag']}")
            print(f"       version : {m['version']}")
            print(f"       score   : {_gb('1.0  (exact)')}")
            print()
    else:
        print(_rb("  ✗ No exact match found."))
        if best:
            print(f"  {_y('Closest candidate:')}")
            print(f"    {_b(best['stem'])}")
            print(f"    score   : {_y(str(best['score']))}  "
                  f"({int(best['score'] * max(best['n_image_act'], best['n_preset_act']))}"
                  f"/{max(best['n_image_act'], best['n_preset_act'])} actions match)")
        print()

    # Top-5 similarity ranking
    top = result["candidates"][:5]
    if top:
        print(f"  {'Top similarity ranking:'}")
        print(f"  {'Rank':<5} {'Score':<8} {'Stem'}")
        print(f"  {SSEP[:50]}")
        for rank, c in enumerate(top, 1):
            score_str = _gb(f"{c['score']:.4f}") if c["exact"] else f"{c['score']:.4f}"
            flag      = _gb(" ← exact") if c["exact"] else ""
            print(f"  {rank:<5} {score_str:<8} {c['stem']}{flag}")
        print()

    print(_b(SEP))


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json_output(
    image_path: Path | None,
    image_actions: list[dict],
    opened_first: bool,
    result: dict,
    actions_dir: Path,
    timestamp: str,
) -> dict:
    best = result["best_match"]
    return {
        "meta": {
            "timestamp":       timestamp,
            "image_path":      str(image_path) if image_path else None,
            "has_opened_first": opened_first,
            "actions_dir":     str(actions_dir),
            "n_image_actions": len(image_actions),
            "n_presets_in_lib": len(result["candidates"]),
        },
        "result": {
            "match_found":   bool(result["exact_matches"]),
            "n_exact_matches": len(result["exact_matches"]),
            # First exact match (the one returned as the answer)
            "identified_preset": (
                {
                    "stem":    best["stem"],
                    "tag":     best["tag"],
                    "sub_tag": best["sub_tag"],
                    "version": best["version"],
                    "score":   best["score"],
                    "exact":   best["exact"],
                }
                if best else None
            ),
            "all_exact_matches": result["exact_matches"],
        },
        "image_actions": image_actions,
        "similarity_ranking": result["candidates"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="preset_identifier.py",
        description=(
            "Identify which Lightroom preset was applied to an image "
            "by matching its C2PA actions against the preset library."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = p.add_mutually_exclusive_group(required=True) # mutually exclusive: either image or manifest
    src.add_argument(
        "--image",
        nargs="?",
        type=Path,
        help="Image file to analyse.",
    )
    src.add_argument(
        "--folder",
        nargs="?",
        type=Path,
        help="folder to analyse.",
    )
    src.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        help="Pre-extracted manifest JSON (skips c2patool invocation).",
    )
    p.add_argument(
        "--actions-dir",
        type=Path,
        default=Path("./results/_preset_actions_"),
        metavar="DIR",
        help="Preset action library folder (default: ./_preset_actions_/).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help=(
            "JSON output file "
            "(default: results/test_preset_match/preset_match_<timestamp>.json)."
        ),
    )
    return p

    # example run
    # python preset_identifier.py ./results/test_images/ --actions-dir ./results/_preset_actions_ --output ./results/test_preset_match/preset_match.json




def main() -> None:
    args    = _parser().parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.folder and not args.folder.is_dir():
        print(f"{_rb('[ERROR]')} Folder not found: {args.folder}",
            file=sys.stderr)
        sys.exit(1)

    if args.image and not args.image.is_file():
        print(f"{_rb('[ERROR]')} Image file not found: {args.image}",
            file=sys.stderr)
        sys.exit(1)

    if args.image:
        image_files = [args.image]
    elif args.folder:
        image_files: list[Path] = sorted(f for f in args.folder.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS)
    print(image_files)
    # breakpoint()
    # load manifest
    image_path: Path | None = None

    for img in image_files:
        print(f"  Extracting: {img.name}")

        if args.manifest:
            # Pre-extracted manifest JSON
            if not args.manifest.is_file():
                print(f"{_rb('[ERROR]')} Manifest file not found: {args.manifest}",
                    file=sys.stderr)
                sys.exit(1)
            try:
                manifest_json = json.loads(args.manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"{_rb('[ERROR]')} Cannot parse manifest JSON: {exc}", file=sys.stderr)
                sys.exit(1)
            print(f"\n  Using pre-extracted manifest: {_b(str(args.manifest))}")

        else:
            # Image path — invoke c2patool
            image_path = img    
            if not image_path or not image_path.is_file():
                print(f"{_rb('[ERROR]')} Image file not found: {image_path}",
                    file=sys.stderr)
                sys.exit(1)
            print(f"\n  Extracting manifest from: {_b(str(image_path))} …")
            manifest_json = read_manifest_store(image_path)
            #_run_c2patool(image_path, args.tool)
            if manifest_json is None:
                print(_rb("  No C2PA manifest found in this image. Exiting."),
                    file=sys.stderr)
                sys.exit(1)

        # extract and strip actions
        raw_actions   = get_raw_actions(manifest_json)

        opened_first = has_opened_first(raw_actions)

        #_extract_actions(manifest_json)
        image_actions = strip_opened(raw_actions) 
        #_strip_opened(raw_actions)

        # breakpoint()

        if not image_actions:
            print(_y("  No actions found in manifest (after stripping c2pa.opened)."),
                file=sys.stderr)

        # load preset library
        actions_dir: Path = args.actions_dir
        if not actions_dir.is_dir():
            print(
                f"{_rb('[ERROR]')} Preset actions folder not found: '{actions_dir}'.\n"
                "  Run preset_comparison.py first, or pass --actions-dir <path>.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"  Loading preset library from: {_b(str(actions_dir))} …")
        library = load_preset_library(actions_dir)

        if not library:
            print(_rb("  No preset files found in the library. Exiting."), file=sys.stderr)
            sys.exit(1)

        print(f"  {_g(str(len(library)))} preset(s) loaded.\n")

        # compute match
        result = match_preset(image_actions, library)

        # print results
        print_result(image_path, image_actions, opened_first, result, timestamp)
        
        # # save json
        # output_path = args.output or (
        #     Path("results") / f"test_preset_match/preset_match_{}_{}{timestamp}.json"
        # )
        # output_path.parent.mkdir(parents=True, exist_ok=True)
        # payload = build_json_output(
        #     image_path, image_actions, opened_first, result, actions_dir, timestamp
        # )
        # output_path.write_text(
        #     json.dumps(payload, indent=2, default=str), encoding="utf-8"
        # )
        # print(f"  Results saved to: {str(output_path)}\n")


if __name__ == "__main__":
    main()