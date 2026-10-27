"""
presets comparison functions and aggregation logic for printing/saving results
"""
 
from __future__ import annotations
import copy 

# ---------------------------------------------------------------------------
# Action comparison
# ---------------------------------------------------------------------------

def actions_equal(a: list[dict], b: list[dict]) -> bool:
    """Full equality: same length, same names, same parameters."""
    if len(a) != len(b):
        return False
    return all(
        x["action"] == y["action"] and x["parameters"] == y["parameters"]
        for x, y in zip(a, b)
    )


def names_equal(a: list[dict], b: list[dict]) -> bool:
    """Same action names in the same order; parameters may differ."""
    if len(a) != len(b):
        return False
    return all(x["action"] == y["action"] for x, y in zip(a, b))


def count_matching(a: list[dict], b: list[dict]) -> int:
    """Positions where both action name AND parameters are identical."""
    return sum(
        1 for x, y in zip(a, b)
        if x["action"] == y["action"] and x["parameters"] == y["parameters"]
    )


def compare_pair(p: dict, q: dict) -> dict:
    """Return a compact comparison record for a single preset pair."""
    acts_a = p["actions"]
    acts_b = q["actions"]
    eq     = actions_equal(acts_a, acts_b)
    return {
        "stem_a":          p["stem"],
        "stem_b":          q["stem"],
        "tag_a":           p["tag"],
        "sub_tag_a":       p["sub_tag"],
        "version_a":       p["version"],
        "tag_b":           q["tag"],
        "sub_tag_b":       q["sub_tag"],
        "version_b":       q["version"],
        "actions_equal":   eq,
        "names_equal":     names_equal(acts_a, acts_b),
        "matching_count":  count_matching(acts_a, acts_b),
        "total_actions_a": len(acts_a),
        "total_actions_b": len(acts_b),
    }


# ---------------------------------------------------------------------------
# Grouping helpers
# ---------------------------------------------------------------------------

def _group(presets: list[dict], *keys: str) -> dict:
    """Nest presets into a dict keyed by the given fields in order."""
    root: dict = {}
    for p in presets:
        node = root
        for k in keys[:-1]:
            node = node.setdefault(p[k], {})
        node.setdefault(p[keys[-1]], []).append(p)
    return root


def _all_pairs(items: list) -> list[tuple]:
    return [(items[i], items[j])
            for i in range(len(items))
            for j in range(i + 1, len(items))]


def _cross(list_a: list, list_b: list) -> list[tuple]:
    return [(a, b) for a in list_a for b in list_b]


def _pair_stats(pairs_data: list[dict]) -> dict:
    n_total  = len(pairs_data)
    n_equal  = sum(1 for p in pairs_data if p["actions_equal"])
    n_diff   = n_total - n_equal
    return {
        "n_pairs":       n_total,
        "n_equal_pairs": n_equal,
        "n_diff_pairs":  n_diff,
        "all_different": True if n_equal == 0 else False,
    }


# ---------------------------------------------------------------------------
# Inter sub_tag (within same tag)
# ---------------------------------------------------------------------------

def inter_sub_tag(presets: list[dict]) -> dict:
    """
    Within each tag, cross every version of sub_tag A against every version
    of sub_tag B, for all unique (sub_tag_A, sub_tag_B) pairs.

    e.g. seasons: autumn/* vs summer/*, autumn/* vs spring/*, summer/* vs winter/*
         style:   bw/* vs cinematic/*, ...
    """
    by = _group(presets, "tag", "sub_tag")
    groups: list[dict] = []

    for tag in sorted(by):
        sub_tags = sorted(by[tag])
        if len(sub_tags) < 2:
            continue

        for i in range(len(sub_tags)):
            for j in range(i, len(sub_tags)): # i + 1 to avoid diagonal
                st_a = sub_tags[i]
                st_b = sub_tags[j]
                pairs_data = [compare_pair(a, b)
                              for a, b in _cross(by[tag][st_a], by[tag][st_b])]
                stats = _pair_stats(pairs_data)

                groups.append({
                    "tag":          tag,
                    "sub_tag_a":    st_a,
                    "sub_tag_b":    st_b,
                    "n_versions_a": len(by[tag][st_a]),
                    "n_versions_b": len(by[tag][st_b]),
                    **stats,
                    "pairs": pairs_data,
                })


    diff_pairs: list = []
    if groups:
        for g in groups:
            if g["n_equal_pairs"] == 1: # same preset, ignore it
                continue
                # overall = True
            diff_pairs.append(g['all_different'])
        overall = all(diff_pairs)
    else:
        overall = True

    # overall = all(g["all_different"] for g in groups) if groups else True
    return {"level": "inter_sub_tag", "overall_pass": overall, "groups": groups}


# ---------------------------------------------------------------------------
# Cross tag
# ---------------------------------------------------------------------------

def cross_tag(presets: list[dict]) -> dict:
    """
    Cross every preset in tag A against every preset in tag B, for all
    unique (tag_A, tag_B) pairs.

    e.g. seasons/* vs style/*
    """
    by = _group(presets, "tag")
    tag_names = sorted(by)
    groups: list[dict] = []

    for i in range(len(tag_names)):
        for j in range(i + 1, len(tag_names)):
            ta = tag_names[i]
            tb = tag_names[j]
            pairs_data = [compare_pair(a, b)
                          for a, b in _cross(by[ta], by[tb])]
            stats = _pair_stats(pairs_data)

            groups.append({
                "tag_a":       ta,
                "tag_b":       tb,
                "n_presets_a": len(by[ta]),
                "n_presets_b": len(by[tb]),
                **stats,
                "pairs": pairs_data,
            })

    overall = all(g["all_different"] for g in groups) if groups else True
    return {"level": "cross_tag", "overall_pass": overall, "groups": groups}
