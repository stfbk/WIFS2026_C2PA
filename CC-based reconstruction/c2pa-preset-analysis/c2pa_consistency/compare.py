"""Cluster images within a preset folder by order-independent action equality."""
from __future__ import annotations


def _canonical_key(actions: list[dict]) -> tuple:
    """
    Order-independent fingerprint: same actions with same parameters compare
    equal regardless of list order or parameter-dict key order.
    Assumes parameter values are hashable (str/number/bool), which holds for
    the c2pa data seen so far.
    """
    entries = tuple(
        sorted(
            (action["action"], tuple(sorted(action["parameters"].items())))
            for action in actions
        )
    )
    return entries

def cluster_action_lists(action_lists: dict[str, list[dict]]) -> list[dict]:
    """
    action_lists: {image_filename: filtered_actions}
    Returns: [{"actions": list[dict], "images": [filenames]}, ...]
    The stored "actions" is the first-seen list in its original order;
    equality for clustering purposes is order-independent.
    """
    clusters: list[dict] = []
    for image_name, actions in action_lists.items():
        key = _canonical_key(actions)
        for cluster in clusters:
            if cluster["key"] == key:
                cluster["images"].append(image_name)
                break
        else:
            clusters.append({"key": key, "actions": actions, "images": [image_name]})
    return clusters