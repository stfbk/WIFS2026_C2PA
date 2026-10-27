"""
console-printing functions
"""
 
from __future__ import annotations


# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _g(s):  return f"{GREEN}{s}{RESET}"
def _r(s):  return f"{RED}{s}{RESET}"
def _y(s):  return f"{YELLOW}{s}{RESET}"
def _b(s):  return f"{BOLD}{s}{RESET}"
def _gb(s): return f"{BOLD}{GREEN}{s}{RESET}"
def _rb(s): return f"{BOLD}{RED}{s}{RESET}"
def _yb(s): return f"{BOLD}{YELLOW}{s}{RESET}"

# ---------------------------------------------------------------------------
# Console output helpers
# ---------------------------------------------------------------------------

SEP  = "=" * 72
SSEP = "─" * 72

def _verdict(all_different: bool) -> str:
    return _gb("✓ PASS — all unique") if all_different else _rb("✗ FAIL — duplicates found")


def _print_identical_pairs(pairs_data: list[dict], indent: int = 6) -> None:
    pad = " " * indent
    for p in pairs_data:
        if p["actions_equal"]:
            print(f"{pad}{_r('=')} {p['stem_a']}")
            print(f"{pad}  {p['stem_b']}")
            print(f"{pad}  {_y(str(p['matching_count']))} / "
                  f"{p['total_actions_a']} actions identical")


def _cell(all_different: bool, n_diff: int, n_total: int) -> str:
    """
    Render a single matrix cell (plain value only, no padding).

    1  (green) = all pairs different  → desired outcome
    0  (red)   = at least one identical pair → problem
    """
    if all_different:
        return _gb("1")
    else:
        return _rb("0")


def _padded_cell(all_different: bool, width: int) -> str:
    """Return a colour-coded cell value left-padded to *width* chars."""
    value = "1" if all_different else "0"
    padded = value.ljust(width)          # pad the plain character, then colour
    return _gb(padded) if all_different else _rb(padded)


# ---------------------------------------------------------------------------
# Matrix printers
# ---------------------------------------------------------------------------

def _truncate(s: str, width: int) -> str:
    """Truncate *s* to *width* chars, padding with spaces if shorter."""
    return (s[:width] if len(s) > width else s).ljust(width)


def print_inter_matrix(result: dict, presets: list[dict]) -> None:
    """
    Print one square symmetric matrix per tag.

    Rows and columns = sub_tag names within that tag.
    Diagonal = ■ (self-comparison, not applicable).
    Off-diagonal cell:
        1 (green)  all version-crosses between sub_tag_A and sub_tag_B differ
        0 (red)    at least one version-cross is identical

    Below the matrix, a detail line shows the ratio n_diff/n_total for every
    non-passing cell so the reader knows how many pairs actually collided.
    """
    # Build a lookup:  (tag, sub_tag_a, sub_tag_b) → group
    lookup: dict[tuple, dict] = {}
    for g in result["groups"]:
        # print(f"g: {g}")
        lookup[(g["tag"], g["sub_tag_a"], g["sub_tag_b"])] = g
        lookup[(g["tag"], g["sub_tag_b"], g["sub_tag_a"])] = g  # symmetric
    
    # print(f"lookup: {lookup}")
    # breakpoint()

    # Get all (tag → sorted sub_tags) from the presets
    by_tag: dict[str, list[str]] = {}
    for p in presets:
        by_tag.setdefault(p["tag"], set()).add(p["sub_tag"])
    by_tag = {tag: sorted(subs) for tag, subs in sorted(by_tag.items())}
    # print(f"by_tag: {by_tag}")
    # breakpoint()

    for tag, sub_tags in by_tag.items():
        n = len(sub_tags)
        if n < 2:
            continue

        # Column width = longest sub_tag name (min 8 for CN2, +2 for col and row labels)
        COL       = max(max(len(s) for s in sub_tags), 8) + 2
        ROW_LABEL = max(max(len(s) for s in sub_tags), 8) + 2

        # Header
        print(f"\n  {_b(f'[ {tag.upper()} ]')}  "
              f"{'inter sub_tag matrix'}")
        print(f"  {_g('1')} = different   {_r('0')} = identical   ■ = self")
        print(f"  Each cell: all {'version_A × version_B'} crosses must differ\n")

        header = " " * ROW_LABEL + "".join(
            _truncate(st, COL) for st in sub_tags
        )
        print("  " + header)
        print("  " + "─" * len(header))

        # Rows
        collisions: list[str] = []
        for row_st in sub_tags:
            label = _b(_truncate(row_st, ROW_LABEL))
            cells: list[str] = []
            for col_st in sub_tags:
                # if row_st == col_st:
                #     key = (tag, row_st, col_st)
                #     g   = lookup.get(key)
                #     if g is None:
                #         cells.append(_y("?".ljust(COL)))
                #     else:
                #         cells.append(_padded_cell(g["all_different"], COL))
                #     # cells.append("■".ljust(COL))
                # else:
                    key = (tag, row_st, col_st)
                    g   = lookup.get(key)
                    # print(f"inter_matrxi g: {g}")
                    if g is None:
                        cells.append(_y("?".ljust(COL)))
                    else:
                        cells.append(_padded_cell(g["all_different"], COL))

                        if not g["all_different"] and (row_st != col_st):
                            collisions.append(
                                f"    {_r('•')} {row_st} ↔ {col_st}: "
                                f"{_r(str(g['n_equal_pairs']))} identical pair(s) "
                                f"out of {g['n_pairs']}  "
                                f"({g['n_versions_a']} × {g['n_versions_b']} versions)"
                            )
            print("  " + label + "".join(cells))

        print("  " + "─" * len(header))

        if collisions:
            seen = set()
            print(f"\n  {_rb('Collisions:')}")
            for c in collisions:
                if c not in seen:
                    print(c)
                    seen.add(c)
        else:
            print(f"\n  {_gb('No collisions — all sub-presets are unique within this tag.')}")


def print_cross_matrix(result: dict, presets: list[dict]) -> None:
    """
    Print one rectangular matrix per (tag_A, tag_B) pair.

    Rows    = sub_tags of tag_A
    Columns = sub_tags of tag_B

    Cell value:
        1 (green)  all version-crosses between sub_tag_A and sub_tag_B differ
        0 (red)    at least one version-cross is identical

    Because tag_A and tag_B can have different numbers of sub_tags (and each
    sub_tag can have a different number of versions), the matrix is rectangular
    and non-square cells are perfectly valid.
    """
    # Build lookup: (tag_a, tag_b, sub_tag_a, sub_tag_b) → group
    # We need cross-tag pair data broken down by (sub_tag_a, sub_tag_b).
    # The cross_tag groups only store tag-level stats, so we recompute
    # sub_tag granularity from the pairs list.
    cross_detail: dict[tuple, dict] = {}
    # key = (tag_a, tag_b, sub_tag_a, sub_tag_b)

    for g in result["groups"]:
        ta, tb = g["tag_a"], g["tag_b"]
        # Aggregate pairs by (sub_tag_a, sub_tag_b)
        cell_pairs: dict[tuple, list[dict]] = {}
        for pair in g["pairs"]:
            key = (pair["sub_tag_a"], pair["sub_tag_b"])
            cell_pairs.setdefault(key, []).append(pair)

        for (st_a, st_b), plist in cell_pairs.items():
            n_eq   = sum(1 for p in plist if p["actions_equal"])
            n_tot  = len(plist)
            cross_detail[(ta, tb, st_a, st_b)] = {
                "n_pairs":       n_tot,
                "n_equal_pairs": n_eq,
                "n_diff_pairs":  n_tot - n_eq,
                "all_different": n_eq == 0,
            }

    # sub_tags per tag (from presets)
    by_tag: dict[str, list[str]] = {}
    for p in presets:
        by_tag.setdefault(p["tag"], set()).add(p["sub_tag"])
    by_tag = {tag: sorted(subs) for tag, subs in sorted(by_tag.items())}

    for g in result["groups"]:
        ta = g["tag_a"]
        tb = g["tag_b"]
        rows = by_tag.get(ta, [])
        cols = by_tag.get(tb, [])

        if not rows or not cols:
            continue

        COL       = max(max(len(s) for s in cols), 6) + 2
        ROW_LABEL = max(max(len(s) for s in rows), 6) + 2

        print(f"\n  {_b(f'[ {ta.upper()} ]')}  ×  "
              f"{_b(f'[ {tb.upper()} ]')}  "
              f"{'cross-tag matrix'}")
        print(f"  rows = {_b(ta)} sub_tags   "
              f"cols = {_b(tb)} sub_tags")
        print(f"  {_g('1')} = different   {_r('0')} = identical\n")

        # Column header
        header = " " * ROW_LABEL + "".join(
            _truncate(st, COL) for st in cols
        )
        print("  " + header)
        print("  " + "─" * len(header))

        collisions: list[str] = []
        for row_st in rows:
            label = _b(_truncate(row_st, ROW_LABEL))
            cells: list[str] = []
            for col_st in cols:
                detail = cross_detail.get((ta, tb, row_st, col_st))
                if detail is None:
                    # Try reversed direction (ta/tb might be swapped)
                    detail = cross_detail.get((tb, ta, col_st, row_st))
                if detail is None:
                    cells.append(_y("?".ljust(COL)))
                else:
                    cells.append(_padded_cell(detail["all_different"], COL))
                    if not detail["all_different"]:
                        collisions.append(
                            f"    {_r('•')} {ta}/{row_st} ↔ {tb}/{col_st}: "
                            f"{_r(str(detail['n_equal_pairs']))} identical pair(s) "
                            f"out of {detail['n_pairs']}"
                        )
            print("  " + label + "".join(cells))

        print("  " + "─" * len(header))

        if collisions:
            print(f"\n  {_rb('Collisions:')}")
            for c in collisions:
                print(c)
        else:
            print(f"\n  {_gb('No collisions — all cross-tag pairs are unique.')}")


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def print_inter(result: dict, presets: list[dict]) -> None:
    print(f"\n{_b(SEP)}")
    print(_b("  INTER SUB_TAG ANALYSIS  (within same tag)"))
    print(_b("  Matrix: rows × cols = sub_tag names within the same tag"))
    print(_b(SEP))
    print(f"  {'Question:'} Do different sub-presets have unique signatures?")
    print(f"  {'Expected:'} {_g('all cells = 1 (green)')}\n")

    print_inter_matrix(result, presets)
    print(f"\n  {'Sub-presets analysis results:'} {_verdict(result['overall_pass'])}")


def print_cross(result: dict, presets: list[dict]) -> None:
    print(f"\n{_b(SEP)}")
    print(_b("  CROSS TAG ANALYSIS"))
    print(_b("  Rectangular matrix: rows = tag_A sub_tags, cols = tag_B sub_tags"))
    print(_b(SEP))
    print(f"  {'Question:'} Do presets from different categories have unique signatures?")
    print(f"  {'Expected:'} {_g('all cells = 1 (green)')}\n")

    print_cross_matrix(result, presets)
    print(f"\n  {'Cross presets analysis results:'} {_verdict(result['overall_pass'])}")


def print_summary(presets, inter, cross, output_path, timestamp):
    tags     = sorted({p["tag"]     for p in presets})
    sub_tags = sorted({p["sub_tag"] for p in presets})

    print(f"\n{_b(SEP)}")
    print(_b("  GLOBAL SUMMARY"))
    print(_b(SEP))
    print(f"  {'Timestamp         :'} {timestamp}")
    print(f"  {'Tags              :'} {', '.join(tags)}")
    print(f"  {'Sub-tags          :'} {len(sub_tags)}  ({', '.join(sub_tags)})")
    print(f"  {'Total presets     :'} {len(presets)}")
    print()
    
    print(f"  {'Inter sub_tag     :'} {_verdict(inter['overall_pass'])}")
    print(f"  {'Cross tag         :'} {_verdict(cross['overall_pass'])}")
    print()
   
    overall = inter["overall_pass"] and cross["overall_pass"]
    label = _gb("✓ Every preset has a unique action signature") \
        if overall else _rb("✗ Some presets share identical action signatures")
    print(f"  {'Overall           :'} {label}")
    print()
    print(f"  {'Results saved to  :'} {output_path}")
    print(_b(SEP))