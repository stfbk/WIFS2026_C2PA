"""
preset_identifier.py
====================
Identify which Lightroom preset was applied to an image by matching its
C2PA manifest actions against the preset action library stored under
``_preset_actions_/``.

Use-case
--------
When Lightroom exports an image the ``c2pa.filtered`` action sometimes does
not carry the preset name in its parameters.  This script recovers the preset
identity by comparing the full action list (minus ``c2pa.opened`` and the
``Preset`` type ``c2pa.filtered``) against every saved preset signature using
a match-and-remove deepcopy strategy with a 5% numeric tolerance.

Matching strategy
-----------------
For each preset in the library:
  1. Deep-copy the image action list into ``remaining``.
  2. For each action in the preset reference list, search ``remaining`` for
     an entry with the same action name and parameters within 5% tolerance.
  3. When found, remove it from ``remaining`` and continue.
  4. A **full match** requires ``remaining`` to be empty AND every preset
     action to have been found.

Partial matching (similarity score) is also computed for every preset so
you can see the closest candidate even when no exact match exists.

Usage
-----
    python preset_identifier.py <folder> [--actions-dir _preset_actions_]
                                          [--tool c2patool]
                                          [--output results/match.json]

    python preset_identifier.py --manifest <manifest.json>
                                [--actions-dir _preset_actions_]
                                [--output results/match.json]
"""

import argparse
import copy     
import json
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
# CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _g(s):  return f"{GREEN}{s}{RESET}"
def _r(s):  return f"{RED}{s}{RESET}"
def _y(s):  return f"{YELLOW}{s}{RESET}"
# def _c(s):  return f"{CYAN}{s}{RESET}"
def _b(s):  return f"{BOLD}{s}{RESET}"
def _gb(s): return f"{BOLD}{GREEN}{s}{RESET}"
def _rb(s): return f"{BOLD}{RED}{s}{RESET}"
def _yb(s): return f"{BOLD}{YELLOW}{s}{RESET}"

SEP  = "=" * 72
SSEP = "─" * 72

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}
)

_TOLERANCE = 0.05   # 5% relative tolerance for numeric parameter values

# Confidence thresholds for classifying a non-exact best match.
# Score = consumed_count / max(len_image, len_preset).
CONFIDENCE_LIKELY    = 0.85   # score >= this  → "likely_match"
CONFIDENCE_UNCERTAIN = 0.983 # 0.50   # score >= this  → "uncertain"; below → "unknown_preset"
# suggested rejection threshold: 0.983

# ---------------------------------------------------------------------------
# Manifest / action extraction
# ---------------------------------------------------------------------------

def _run_c2patool(image_path: Path) -> dict | None:
    """Invoke c2patool and return the parsed JSON manifest, or None."""
    import subprocess
    try:
        result = subprocess.run(
            ["c2patool", str(image_path)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)
    except FileNotFoundError:
        print(
            f"{_rb('[ERROR]')} c2patool not found at '{"c2patool"}'.\n"
            "  Install from https://github.com/contentauth/c2patool/releases",
            file=sys.stderr,
        )
        sys.exit(1)
    except json.JSONDecodeError:
        return None
    except subprocess.TimeoutExpired:
        print(f"{_y('[WARN]')} c2patool timed out.", file=sys.stderr)
        return None


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


def _strip_opened(actions: list[dict]) -> list[dict]:
    """Remove c2pa.opened — it carries image-specific hashes, not preset logic."""
    return [a for a in actions if a["action"] != "c2pa.opened"]


def _has_opened_first(actions: list[dict]) -> bool:
    """True iff the very first action is c2pa.opened."""
    return bool(actions) and actions[0]["action"] == "c2pa.opened"


def _strip_preset_action(actions: list[dict]) -> list[dict]:
    """
    Remove the c2pa.filtered entry that carries the preset name
    (com.adobe.acr == "Preset").  This entry is excluded from matching
    because it may be missing from images exported without preset metadata.
    """
    out = []
    for act in actions:
        acr_type = str(act["parameters"].get("com.adobe.acr", "")).strip().lower()
        if act["action"] == "c2pa.filtered" and acr_type == "preset":
            continue
        out.append(act)
    return out


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
            print(f"  {_y('[WARN]')} Cannot load {json_file}: {exc}", file=sys.stderr)
            continue

        actions = payload.get("actions", [])
        if not actions:
            continue

        # Strip the preset-name action so matching works even when it is absent
        actions = _strip_preset_action(actions)

        rel     = json_file.relative_to(actions_dir)
        parts   = rel.parts
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
            "actions": actions,
        })

    return library


# ---------------------------------------------------------------------------
# Tolerance-aware parameter comparison
# ---------------------------------------------------------------------------

def _numeric(v) -> float | None:
    """Parse *v* as float; return None if not numeric."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _params_match(img_params: dict, ref_params: dict) -> bool:
    """
    True when every key in *ref_params* is present in *img_params* with a
    value within ``_TOLERANCE`` (5%) for numerics, or exactly equal otherwise.

    Extra keys in *img_params* not present in *ref_params* are ignored.
    """
    for key, ref_val in ref_params.items():
        if key not in img_params:
            return False
        img_val = img_params[key]

        ref_num = _numeric(ref_val)
        img_num = _numeric(img_val)

        if ref_num is not None and img_num is not None:
            # Numeric comparison with relative tolerance
            if ref_num == 0:
                if img_num != 0:
                    return False
            # check tolerance on action parameters tolerance (fraction increase wrt ref_num)
            elif abs(img_num - ref_num) / abs(ref_num) > _TOLERANCE: 
                return False
        else:
            # Non-numeric: require exact equality
            if img_val != ref_val:
                return False

    return True


# ---------------------------------------------------------------------------
# Deepcopy actions matching
# ---------------------------------------------------------------------------

def _deep_actions_equal(actList: list[dict], refList: list[dict], verbose: bool = False) -> tuple[bool, list[dict], list[dict], int]:
    """
    Match *actList* (image actions) against *refList* (preset reference)
    using a deepcopy match-and-remove strategy with 5% numeric tolerance.

    Algorithm
    ---------
    1. Deep-copy *actList* into ``remaining``.
    2. For each action in *refList*:
       a. Search ``remaining`` for the first entry with the same action name
          and parameters within ``_TOLERANCE``.
       b. Found  → remove it from ``remaining``, increment ``matched_count``.
       c. Not found → append to ``unmatched_ref``.
    3. Full match: ``remaining == []`` and ``unmatched_ref == []``.

    Parameters
    ----------
    actList:  image actions (c2pa.opened and preset-name action already stripped)
    refList:  preset reference actions (preset-name action already stripped)
    verbose:  when True, print leftover and unmatched actions to stdout

    Returns
    -------
    ``(full_match, leftover_image, unmatched_ref, matched_count)``

    leftover_image   image actions not consumed by the preset
    unmatched_ref    preset actions not found in the image
    matched_count    actions actually consumed (always >= 0; this is the
                      ground-truth count — never derive it by subtraction,
                      since ``max(n_image, n_preset) - leftover - unmatched``
                      can go negative whenever ``n_image != n_preset``)
    """
    remaining:     list[dict] = copy.deepcopy(actList)
    unmatched_ref: list[dict] = []
    matched_count: int        = 0
    matching_actions: list[dict] = []

    for ref_act in refList:
        matched = None
        for act in remaining:
            if (act["action"] == ref_act["action"] and _params_match(act["parameters"], ref_act["parameters"])):
                matched = act
                break 
                
        if matched is not None:
            # print(f"Found mathing action: {matched['action']} with params: {matched['parameters']}")
            remaining.remove(matched)
            matched_count += 1
            matching_actions.append(matched)
        else:
            unmatched_ref.append(ref_act)

    full_match = (len(remaining) == 0 and len(unmatched_ref) == 0)

    if verbose and not full_match:
        if remaining:
            print(f"    {_y(str(len(remaining)))} current image action(s) not matched by reference preset:")
            for act in remaining:
                print(f"      {_r('→')} {act['action']}")
                for k, v in act["parameters"].items():
                    print(f"           {k}: {v}")
        if unmatched_ref:
            print(f"    {_y(str(len(unmatched_ref)))} preset action(s) not found in current image:")
            for act in unmatched_ref:
                print(f"      {_r('→')} {act['action']}")
                for k, v in act["parameters"].items():
                    print(f"           {k}: {v}")


    # print(f"Found the following matching actions: {matching_actions}")
    # breakpoint()

    return full_match, remaining, unmatched_ref, matched_count


def _similarity(image_actions: list[dict], preset_actions: list[dict]) -> float | None:
    """
    Similarity score in [0.0, 1.0] using match-and-remove with tolerance.

    Score = matched_count / max(len_image, len_preset).
    Returns None when both lists are empty.
    """
    if not image_actions and not preset_actions:
        return None
    denom = max(len(image_actions), len(preset_actions))
    if denom == 0:
        return 0.0

    remaining = copy.deepcopy(image_actions)
    matched   = 0
    for ref_act in preset_actions:
        for act in remaining:
            if (act["action"] == ref_act["action"] and _params_match(act["parameters"], ref_act["parameters"])):
                remaining.remove(act)
                matched += 1
                break

    return round(matched / denom, 4)


# ---------------------------------------------------------------------------
# Main matching function
# ---------------------------------------------------------------------------

def _classify_confidence(score: float | None) -> str:
    """
    Map a similarity score to a confidence verdict.

    "likely_match"    score >= CONFIDENCE_LIKELY     — probably this preset
    "uncertain"       score >= CONFIDENCE_UNCERTAIN  — possible, low confidence
    "unknown_preset"  score <  CONFIDENCE_UNCERTAIN  — likely not in the library
    """
    if score is None:
        return "unknown_preset"
    if score >= CONFIDENCE_LIKELY:
        return "likely_match"
    if score >= CONFIDENCE_UNCERTAIN:
        return "uncertain"
    return "unknown_preset"


def match_preset(image_actions: list[dict], library: list[dict]) -> dict:
    """
    Compare *image_actions* against every preset in *library*.

    Ranking strategy
    ----------------
    Candidates are primarily ranked by **total unmatched action count**
    (``len(leftover_image) + len(unmatched_ref)``), ascending — the preset
    leaving the fewest actions unexplained wins.  The similarity score is
    used only as a tie-breaker when two presets have the same unmatched
    count, since the raw count is a more direct measure of "how many
    actions are wrong" than a normalised score (a 2-action miss out of 4
    actions is treated the same as a 2-action miss out of 20 by score
    alone, which the unmatched-count primary key avoids).

    Confidence
    ----------
    When no full match exists, the best candidate is classified into one
    of three verdicts based on its score (see ``_classify_confidence``):
    "likely_match", "uncertain", or "unknown_preset" — the last meaning
    the image was probably edited with a preset not present in the library.

    Returns
    -------
    ::

        {
            "exact_matches":  list[dict],   # presets with full_match == True
            "best_match":     dict | None,
            "best_score":     float,
            "verdict":        str,          # see _classify_confidence
            "ambiguous":      bool,         # True if 2nd-best is very close
            "candidates":     list[dict],   # sorted by unmatched count, then score
        }

    Each candidate::

        {
            "stem", "tag", "sub_tag", "version",
            "score":            float,
            "exact":            bool,
            "n_image_act":      int,
            "n_preset_act":     int,
            "match_act":        int,        # number of actions consumed
            "n_unmatched":      int,        # leftover_image + unmatched_ref count
            "leftover_image":   list[dict],
            "unmatched_ref":    list[dict],
            "path":             str,
        }
    """
    candidates: list[dict] = []

    for preset in library:
        score                                          = _similarity(image_actions, preset["actions"])
        full_match, leftover, unmatched, matched_count = _deep_actions_equal(image_actions, preset["actions"], verbose=False)
        n_image     = len(image_actions)
        n_preset    = len(preset["actions"])
        n_unmatched = len(leftover) + len(unmatched)
        # matched_count comes straight from the match-and-remove loop —
        # never derive it by subtraction, since max(n_image, n_preset) -
        # leftover - unmatched can go negative whenever n_image != n_preset.

        candidates.append({
            "stem":           preset["stem"],
            "tag":            preset["tag"],
            "sub_tag":        preset["sub_tag"],
            "version":        preset["version"],
            "score":          score,
            "exact":          full_match,
            "n_image_act":    n_image,
            "n_preset_act":   n_preset,
            "match_act":      matched_count,
            "n_unmatched":    n_unmatched,
            "leftover_image": leftover,
            "unmatched_ref":  unmatched,
            "path":           str(preset["path"]),
        })

    # Point 1: primary key = total unmatched count (ascending) — the preset
    # leaving the fewest actions unexplained wins.  Score is the tie-breaker.
    #
    # Guard: a preset with ZERO matched actions must never outrank a preset
    # with at least one match, no matter how small its own action list is
    # (a tiny unrelated preset can otherwise "win" purely by having few
    # actions to be unmatched against). We therefore sort first on whether
    # any actions matched at all, then on unmatched count, then on score.
    candidates.sort(
        key=lambda c: (
            c["match_act"] == 0,        # False (has matches) sorts before True (no matches)
            c["n_unmatched"],           # sort on n_unmatched to weight more match on small presets (i.e. 2/4 actions) compared to few matched on big presets (i.e. 15/20)
            -(c["score"] or 0.0),       # sort on score
            c["stem"],
        )
    )

    exact_matches = [c for c in candidates if c["exact"]]
    best          = candidates[0] if candidates else None

    # Point 2: confidence verdict for the best candidate
    if exact_matches:
        verdict = "exact_match"
    else:
        verdict = _classify_confidence(best["score"] if best else None)

    # Flag ambiguity: second-best is within 1 unmatched action AND
    # score difference under 5% — the result should not be trusted blindly.
    ambiguous = False
    if not exact_matches and len(candidates) >= 2:
        first, second = candidates[0], candidates[1]
        unmatched_close = abs(first["n_unmatched"] - second["n_unmatched"]) <= 1
        score_close = (
            first["score"] is not None and second["score"] is not None
            and abs(first["score"] - second["score"]) < 0.05
        )
        ambiguous = unmatched_close and score_close

    return {
        "exact_matches": exact_matches,
        "best_match":    exact_matches[0] if exact_matches else best,
        "best_score":    best["score"] if best else 0.0,
        "verdict":       verdict,
        "ambiguous":     ambiguous,
        "candidates":    candidates,
    }

# ---------------------------------------------------------------------------
# Inter class distance computation
# ---------------------------------------------------------------------------

# Step 1: compute the "nearest other class" distance for every preset
# against every OTHER preset in your 110-preset library (leave-one-out).
# This tells you the natural separation between known classes.

def compute_inter_class_distances(library: list[dict]) -> list[float]:
    """
    For each preset, compute its similarity score against every other
    preset in the library, and return the maximum (closest neighbor).
    This calibrates what 'close to a different class' looks like.
    """
    closest_neighbor_scores = []
    for i, preset_i in enumerate(library):
        best_other_score = 0.0
        for j, preset_j in enumerate(library):
            if i == j:
                continue
            score = _similarity(preset_i["actions"], preset_j["actions"])
            best_other_score = max(best_other_score, score or 0.0)
        closest_neighbor_scores.append(best_other_score)
    return closest_neighbor_scores




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
        print(f"  {'Image              :'} {image_path}")
    print(f"  {'Timestamp          :'} {timestamp}")
    print(f"  {'Actions found      :'} {len(image_actions)}  "
          f"(c2pa.opened and Preset action excluded)")
    print(f"  {'c2pa.opened first  :'} "
          f"{_g(str(opened_first)) if opened_first else _y(str(opened_first))}")
    print(f"  {'Presets in lib     :'} {len(result['candidates'])}")
    print(f"  {'Tolerance          :'} {int(_TOLERANCE * 100)}%  "
          f"(numeric parameter values)")
    print()

    exact = result["exact_matches"]
    best  = result["best_match"]

    if exact:
        print(_gb(f"  ✓ FULL MATCH{'ES' if len(exact) > 1 else ''} FOUND  ({len(exact)})"))
        print()
        for m in exact:
            print(f"    {_gb('●')}  {_b(m['stem'])}")
            print(f"       tag       : {m['tag']}")
            print(f"       sub_tag   : {m['sub_tag']}")
            print(f"       version   : {m['version']}")
            print(f"       matched   : {_gb(str(m['match_act']))} / {m['n_preset_act']} actions")
            print(f"       score     : {_gb('1.0  (full match)')}")
            print()
    else:
        verdict   = result["verdict"]
        ambiguous = result["ambiguous"]

        if verdict == "likely_match":
            print(_yb("  ~ LIKELY MATCH (not exact, high confidence)"))
        elif verdict == "uncertain":
            print(_yb("  ? UNCERTAIN MATCH (low confidence)"))
        else:
            print(_rb("  ✗ UNKNOWN PRESET — likely not in the library"))
        print()

        if best:
            n_max       = max(best["n_image_act"], best["n_preset_act"])
            score_str   = f"{best['score']:.4f}" if best["score"] is not None else "—"
            n_unmatched = best["n_unmatched"]

            # Point 5: headline states absolute counts, not just the score
            if n_unmatched == 0:
                headline = "all actions accounted for"
            elif n_unmatched == 1:
                headline = "1 action unmatched"
            else:
                headline = f"{n_unmatched} actions unmatched"

            print(f"  {_y('Closest candidate:')}  {_b(best['stem'])}  "
                  f"— {_y(headline)}")
            print(f"    score      : {_y(score_str)}  "
                  f"({best['match_act']}/{n_max} actions within {int(_TOLERANCE*100)}%)")

            if ambiguous:
                second = result["candidates"][1]
                print(f"    {_yb('⚠ ambiguous:')} "
                      f"'{second['stem']}' is nearly as close "
                      f"({second['n_unmatched']} unmatched, score {second['score']:.4f}) "
                      f"— do not trust this match blindly.")

            if best["leftover_image"]:
                print(f"\n    {_y('Image actions not consumed by preset')} "
                      f"({len(best['leftover_image'])}):")
                for act in best["leftover_image"]:
                    print(f"      {_r('→')} {act['action']}")
                    for k, v in act["parameters"].items():
                        print(f"           {k}: {v}")

            if best["unmatched_ref"]:
                print(f"\n    {_y('Preset actions not found in image')} "
                      f"({len(best['unmatched_ref'])}):")
                for act in best["unmatched_ref"]:
                    print(f"      {_r('→')} {act['action']}")
                    for k, v in act["parameters"].items():
                        print(f"           {k}: {v}")
        print()

    # Top-5 ranking, now sorted by unmatched count (point 1)
    top = result["candidates"][:5]
    if top:
        print(f"  {'Top ranking (by fewest unmatched actions):'}")
        print(f"  {'Rank':<5} {'Unmatched':<10} {'Score':<8} {'Matched':<10} {'Stem'}")
        print(f"  {SSEP[:72]}")
        for rank, c in enumerate(top, 1):
            score_str   = _gb(f"{c['score']:.4f}") if c["exact"] else (
                f"{c['score']:.4f}" if c["score"] is not None else "—"
            )
            n_max        = max(c["n_image_act"], c["n_preset_act"])
            matched_str  = f"{c['match_act']}/{n_max}"
            unmatched_str = _gb(str(c["n_unmatched"])) if c["n_unmatched"] == 0 \
                else _y(str(c["n_unmatched"]))
            flag         = _gb(" ← full match") if c["exact"] else ""
            print(f"  {rank:<5} {unmatched_str:<10} {score_str:<8} {matched_str:<10} "
                  f"{c['stem']}{flag}")
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
            "timestamp":        timestamp,
            "image_path":       str(image_path) if image_path else None,
            "has_opened_first": opened_first,
            "actions_dir":      str(actions_dir),
            "n_image_actions":  len(image_actions),
            "n_presets_in_lib": len(result["candidates"]),
            "tolerance_pct":    int(_TOLERANCE * 100),
            "confidence_thresholds": {
                "likely_match_min":    CONFIDENCE_LIKELY,
                "uncertain_min":       CONFIDENCE_UNCERTAIN,
            },
        },
        "result": {
            "match_found":     bool(result["exact_matches"]),
            "n_exact_matches": len(result["exact_matches"]),
            "verdict":         result["verdict"],     # exact_match | likely_match | uncertain | unknown_preset
            "ambiguous":       result["ambiguous"],    # True if 2nd-best is nearly as close
            "identified_preset": (
                {
                    "stem":           best["stem"],
                    "tag":            best["tag"],
                    "sub_tag":        best["sub_tag"],
                    "version":        best["version"],
                    "score":          best["score"],
                    "exact":          best["exact"],
                    "match_act":      best["match_act"],
                    "n_unmatched":    best["n_unmatched"],
                    "leftover_image": best["leftover_image"],
                    "unmatched_ref":  best["unmatched_ref"],
                }
                if best else None
            ),
            "all_exact_matches": result["exact_matches"],
        },
        "image_actions":      image_actions,
        "similarity_ranking": result["candidates"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="preset_identifier.py",
        description="Identify the Lightroom preset applied to images via C2PA actions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--folder",
        nargs="?",
        type=Path,
        help="Folder of images to analyse.",
    )
    src.add_argument(
        "--image",
        nargs="?",
        type=Path,
        help="Folder of images to analyse.",
    )
    src.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        help="Pre-extracted manifest JSON (skips c2patool).",
    )
    p.add_argument(
        "--actions-dir",
        type=Path,
        default=Path("./results/_preset_actions_"),
        metavar="DIR",
        help="Preset action library folder (default: ./results/_preset_actions_/).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="FILE",
        help="JSON output file (default: results/preset_match_<timestamp>.json).",
    )
    return p


def main() -> None:
    args      = _parser().parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── load preset library (done once for all images) ────────────────────
    actions_dir: Path = args.actions_dir
    if not actions_dir.is_dir():
        print(
            f"{_rb('[ERROR]')} Preset actions folder not found: '{actions_dir}'.\n"
            "  Run preset_comparison.py first, or pass --actions-dir <path>.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n  Loading preset library from: {_b(str(actions_dir))} …")
    library = load_preset_library(actions_dir)
    if not library:
        print(_rb("  No preset files found in the library. Exiting."), file=sys.stderr)
        sys.exit(1)
    print(f"  {_g(str(len(library)))} preset(s) loaded.\n")

    # ── computing rejection threshold ──────────────────────────────────────
    # Step 2: your rejection threshold should sit ABOVE the highest inter-class
    # similarity you observe — otherwise two genuinely different presets in
    # your own library would already confuse each other.
    # print("Computing rejection threshold...")
    # inter_class_scores = compute_inter_class_distances(library)
    # suggested_threshold = max(inter_class_scores) + 0.02   # small safety margin

    # print(f"Done! Suggested rejection threshold: {suggested_threshold}") # suggested rejection threshold: 0.983
    
    # breakpoint()

    # ── collect images ────────────────────────────────────────────────────
    # if args.manifest:
    #     images_to_process = [None]   # sentinel — manifest path used below
    # else:

    images_to_process: list[Path] = []
    source_label = ""

    if args.image:
        if not args.image.is_file():
            print(f"{_rb('[ERROR]')} Image file not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        images_to_process = [args.image]
        source_label = f"image {args.image}"
    elif args.folder:
        if not args.folder.is_dir():
            print(f"{_rb('[ERROR]')} Folder not found: {args.folder}", file=sys.stderr)
            sys.exit(1)
        folder = args.folder
        images_to_process = sorted(
            f for f in folder.iterdir()
            if f.suffix.lower() in IMAGE_EXTENSIONS
        )
        source_label = f"folder {folder}"

    if not images_to_process:
        print(f"{_rb('[ERROR]')} No supported images found in {source_label}.", file=sys.stderr)
        sys.exit(1)

    if args.image:
        print(f"  Found {_g(str(len(images_to_process)))} image: {source_label}\n")
    else:
        print(f"  Found {_g(str(len(images_to_process)))} image(s) in {source_label}\n")



    # ── process each image ────────────────────────────────────────────────
    all_results: list[dict] = []

    for img in images_to_process:
        if args.manifest:
            if not args.manifest.is_file():
                print(f"{_rb('[ERROR]')} Manifest not found: {args.manifest}", file=sys.stderr)
                sys.exit(1)
            manifest_json = json.loads(args.manifest.read_text(encoding="utf-8"))
            image_path    = None
        else:
            image_path = img
            print(f"  {'Extracting:'} {image_path.name}")
            manifest_json = _run_c2patool(image_path)
            if manifest_json is None:
                print(f"  {_y('[SKIP]')} No C2PA manifest found in {image_path.name}\n")
                continue

        raw_actions   = _get_raw_actions(manifest_json)
        opened_first  = _has_opened_first(raw_actions)
        # Strip c2pa.opened, then also strip the Preset-type c2pa.filtered
        image_actions = _strip_preset_action(_strip_opened(raw_actions))

        if not image_actions:
            print(f"  {_y('[SKIP]')} No matchable actions after stripping.\n")
            continue

        result = match_preset(image_actions, library)
        print_result(image_path, image_actions, opened_first, result, timestamp)

        # # Save per-image JSON
        # img_stem    = image_path.stem if image_path else "manifest"
        # output_path = args.output or (
        #     Path("results") / f"preset_match_{img_stem}_{timestamp}.json"
        # )
        # output_path.parent.mkdir(parents=True, exist_ok=True)
        # payload = build_json_output(
        #     image_path, image_actions, opened_first, result, actions_dir, timestamp
        # )
        # output_path.write_text(
        #     json.dumps(payload, indent=2, default=str), encoding="utf-8"
        # )
        # print(f"  Results saved to: {str(output_path))}\n")
        # all_results.append(payload)


if __name__ == "__main__":
    main()