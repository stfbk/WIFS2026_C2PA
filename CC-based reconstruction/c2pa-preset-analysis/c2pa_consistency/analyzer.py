"""
Post-hoc analysis of inconsistent preset folders.

Given the output of the consistency analysis, write a table, for folder path of inconsistency, with the following columns:
- Action
- {Image Name}_n

Then in Action reports every action that is inconsistent, and in the columns for each image name, report the value of the action for that image.
If the action is missing for an image, leave it blank.

For example, we got before two inconsistent folders:
  ! input_presets/lr-presets/style/film-inspired/bold-b&w — 12 image(s), 10 distinct presets
  ! input_presets/lr-presets/style/film-inspired/cool-b&w — 10 image(s), 10 distinct presets
Now:
output/consistency/style/film-inspired/bold-b&w
 |----------|-----------|------------|------|------|----------|-----------|------------|------|--------|--------|----------|----------|
 | Action | Image1.jpg | Image2.jpg | Image3.jpg | ...  | Image12.jpg |
 |----------|-----------|------------|------|------|----------|-----------|------------|------|--------|--------|----------|----------|
 | c2pa.color.adjustment | 0.1 | 2 | -3 | ... | 0.1 |
 ...

 Reporting only when it spots a difference.
"""
from __future__ import annotations
from pathlib import Path
import textwrap

from .constants import VALUE_SUFFIX, REPORT_FILENAME, ACTION_COL_WIDTH, VALUE_COL_WIDTH, ROW_COLORS, DIM, RESET, BOLD
from .pipeline import FolderResult

def _flatten_action(action_name: str, parameters: dict) -> dict[str, object]:
    """
    Flatten one action's parameters into {row_label: value}.
    The row label is "<action>.<key>" for non-Lightroom, and "<action>[<value>]" for Lightroom.
    """
    flattened: dict[str, object] = {}
    consumed: set[str] = set()

    for key, value in parameters.items():
        #Lightroom
        value_key = f"{key}{VALUE_SUFFIX}"
        if value_key in parameters:
            flattened[f"{action_name}[{value}]"] = parameters[value_key]
            consumed.add(key)
            consumed.add(value_key)
        #non-Lightroom
        else:
          flattened[f"{action_name}[{key}]"] = value

    return flattened

def flatten_actions(actions: list[dict]) -> dict[str, object]:
    """Flatten a full filtered action list for one image into {row: value}."""
    flat: dict[str, object] = {}
    for entry in actions:
        action_name = entry.get("action")
        parameters = entry.get("parameters") or {}
        if not action_name or not parameters:
            continue
        flat.update(_flatten_action(action_name, parameters))
    return flat

def build_report_rows(action_lists: dict[str, list[dict]]) -> tuple[list[str], list[dict]]:
    """
    action_lists: {image_name: filtered_actions}
    Returns (sorted_image_names, rows), where each row is
    {"Action": label, image_name: value_or_None, ...} -- only for rows
    where the value differs across images (missing vs present counts as a
    difference too).
    """
    per_image_flat = {name: flatten_actions(actions) for name, actions in action_lists.items()}
    image_names = sorted(per_image_flat)
    all_labels = sorted({label for flat in per_image_flat.values() for label in flat})

    rows: list[dict] = []
    for label in all_labels:
        values = {name: per_image_flat[name].get(label) for name in image_names}
        if len({repr(v) for v in values.values()}) > 1:
            row = {"Action": label}
            row.update(values)
            rows.append(row)

    return image_names, rows

def format_markdown_table(image_names: list[str], rows: list[dict]) -> str:
    if not rows:
        return "No differing actions found.\n"

    headers = ["Action"] + image_names
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        cells = [str(row["Action"])]
        for name in image_names:
            value = row.get(name)
            cells.append("" if value is None else str(value))
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"

def _row_colors_by_value(row: dict, image_names: list[str]) -> dict[str, str | None]:
    """
    Assign one color per value that's shared by 2+ images in this row;
    values that appear in only one image get None (left uncolored/white),
    so the eye is drawn to matches, not singletons.
    """
    counts: dict[object, int] = {}
    for name in image_names:
        value = row.get(name)
        if value is not None:
            counts[value] = counts.get(value, 0) + 1

    shared_values = [v for v in counts if counts[v] > 1]
    # preserve first-seen order for stable color assignment
    seen_order: list[object] = []
    for name in image_names:
        value = row.get(name)
        if value in shared_values and value not in seen_order:
            seen_order.append(value)

    palette: dict[object, str | None] = {v: None for v in counts}
    for i, value in enumerate(seen_order):
        palette[value] = ROW_COLORS[i % len(ROW_COLORS)]

    return palette

def _wrap(text: str, width: int) -> list[str]:
    """Wrap text to width, always returning at least one (possibly empty) line."""
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False) or [""]

def format_terminal_table(image_names: list[str], rows: list[dict]) -> str:
    """
    Aligned, colored, wrapped table for terminal display. Long filenames,
    action labels, and values wrap onto extra lines within the same row
    instead of stretching the table. Cells with the same value within a row
    share a color; blank/missing cells are dimmed.
    """
    if not rows:
        return "No differing actions found.\n"

    headers = ["Action"] + image_names
    widths = [ACTION_COL_WIDTH] + [VALUE_COL_WIDTH] * len(image_names)

    def pad(text: str, width: int) -> str:
        return text + " " * (width - len(text))

    def render_wrapped_line(cells: list[str], colors: list[str | None]) -> list[str]:
        """cells: raw (unwrapped) text per column -> list of aligned output lines."""
        wrapped_cols = [_wrap(cell, w) for cell, w in zip(cells, widths)]
        height = max(len(col) for col in wrapped_cols)
        out_lines = []
        for line_idx in range(height):
            parts = []
            for col_idx, col_lines in enumerate(wrapped_cols):
                text = col_lines[line_idx] if line_idx < len(col_lines) else ""
                padded = pad(text, widths[col_idx])
                color = colors[col_idx]
                parts.append(f"{color}{padded}{RESET}" if color else padded)
            out_lines.append("  ".join(parts))
        return out_lines

    lines: list[str] = []
    lines.extend(render_wrapped_line(headers, [BOLD] * len(headers)))
    lines.append("  ".join("-" * w for w in widths))

    for row in rows:
        palette = _row_colors_by_value(row, image_names)
        raw_cells = [str(row["Action"])]
        colors: list[str | None] = [None]
        for name in image_names:
            value = row.get(name)
            raw_cells.append("" if value is None else str(value))
            if value is None:
                colors.append(DIM)
            else:
                colors.append(palette[value])  # shared -> color, unique -> None (white)
        lines.extend(render_wrapped_line(raw_cells, colors))

    return "\n".join(lines) + "\n"

def analyse_inconsistency(result: FolderResult) -> Path | None:
    """
    Build and write the diff table for one inconsistent FolderResult.
    Returns the path of the written report, or None if there was nothing to
    analyse (e.g. action_lists wasn't populated).
    """
    if not result.action_lists:
        return None

    image_names, rows = build_report_rows(result.action_lists)
    
    print(f"\n{result.output_dir}")
    print(format_terminal_table(image_names, rows))

    report_path = result.output_dir / REPORT_FILENAME
    report_path.write_text(format_markdown_table(image_names, rows), encoding="utf-8")
    print(f"  wrote {report_path}")

    return report_path
