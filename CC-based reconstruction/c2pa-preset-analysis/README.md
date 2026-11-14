# C2PA Presets Analyzer

## Overview

This repository contains the C2PA-based analysis that led to the definition of: *Full Consistency (FC)*, *Partial Consistency (PC)*, *Full Uniqueness (FU)*, and *Partial Uniqueness (PU)*, as discussed in Sect. IV of our paper *"Enhanced image forensics through partial C2PA-based provenance information"*.

The analysis consists of two main stages:

- **Consistency analysis** (`c2pa_consistency`)
- **Uniqueness analysis** (`c2pa_uniqueness`)

---

## Running the full analysis

Run the complete pipeline with the default paths:

```bash
bash run.sh [path_to_presets]
```

By default, `run.sh` scans `./DB`, writes consistency profiles and inconsistency reports to `./output/consistency`, runs global uniqueness analysis, and builds the summary reports. The script checks that `c2patool` is installed before starting. 
<!-- Its default `choice` is `1` (the full pipeline); set the environment variable to select another mode:

- `choice=1 bash run.sh` — consistency, uniqueness, and summary (default).
- `choice=2 bash run.sh` — consistency and summary, without uniqueness.
- `choice=3 bash run.sh` — uniqueness and summary using existing consistency output. -->

The summary outputs default to `./output/summary_table.md`, `./output/summary_grouped.json`, and `./output/summary_table.csv`.

---

## Consistency analysis

The consistency analysis checks whether images in the same preset folder have the same filtered C2PA action profile. An action profile consists of the retained actions and their parameters.

- **Full Consistency (FC):** every image in the preset folder has the same actions and parameter values. Action and parameter ordering does not affect this comparison.
- **Partial Consistency (PC):** profiles differ in some parameter values, but share the same action and parameter structure after preset-specific values are disregarded. The differing values are candidates for preset-specific details; review the inconsistency report and merged `_UNIQUE.json` output before concluding that a folder is partially consistent.

The script groups images with identical filtered profiles and writes one JSON file for each distinct profile. The comparison ignores action-list and parameter-dictionary ordering. It flags a folder as inconsistent when it finds more than one distinct profile. It does not automatically classify every inconsistent folder as PC: PC requires interpreting which differences are preset-specific and whether the remaining profile is shared.

### Methodology

For each supported image, the pipeline reads the active C2PA manifest, identifies the generating software from `claim_generator_info[name]`, and filters the recorded actions. It excludes `c2pa.opened` and, for Lightroom, preset-label-only entries such as `c2pa.filtered` / `"Preset"`. Images without a readable manifest or active manifest are skipped. The remaining profiles are compared independent of action-list and parameter-dictionary ordering.

For inconsistent folders, the `inconsistency_report.md` lists action/parameter values that differ across images. Missing values are shown as blank cells. This report is the per-image evidence for reviewing whether the differences are limited to preset-specific values.

### Usage

Run the analysis by passing the path to your input presets directory and, optionally, the consistency output directory. If omitted, the defaults from `c2pa_common/paths.py` are used:

```bash
bash run_consistency.sh [path_to_presets] [consistency_output_path]
```

### Output Files

The pipeline writes one JSON file per distinct filtered action profile. Output paths mirror the input folder structure under the generating software's directory (`Lightroom` or `Adobe Photoshop`).

- A folder with one profile is fully consistent and produces one JSON file.
- A folder with multiple profiles produces a base JSON file and `_variantN.json` files, plus an `inconsistency_report.md`.
- The consistency entry point automatically runs the clustering step for inconsistent folders and may write merged `_UNIQUE.json` files. These are JSON files despite the `_UNIQUE` name; they are not Markdown files and are not the global uniqueness result. The step groups profile files by their ordered sequence of actions and parameter names. Files with different sequences cannot be merged. For each matching group with at least two files, it writes a merged profile: parameter values that agree are retained, while values that differ are replaced with `"x_variable"`. If the profiles split into multiple matching groups (for example, because their partial action/parameter profiles differ), the step can write multiple files: `<preset>_UNIQUE.json`, `<preset>_UNIQUE_variant2.json`, and so on. Groups with only one file do not produce a merged file. Originals that contributed to a merged file are moved into an `old_variants/` subfolder.

Use the inconsistency report together with the merged `_UNIQUE.json` file(s) to review potential partial consistency: check that the shared actions and parameters remain the same and that the replaced values correspond to the expected preset-specific differences. The merged files are comparison aids, not an automatic PC verdict.

---

## Uniqueness analysis

This step compares the per-preset profiles produced by the consistency analysis to determine whether presets can be distinguished using their actions and parameters. It is separate from the `_UNIQUE.json` merge described above: `_UNIQUE.json` summarizes variants within one inconsistent folder, while global uniqueness compares different presets.

The analysis, implemented in `./c2pa_uniqueness`, is executed in two main tasks:

### 1. Inconsistent Preset Analysis (Local Level)

For each preset folder flagged as inconsistent during the consistency analysis (one containing an `inconsistency_report.md`), the analysis reports:

- A **positional action-slot summary**, mapping exact positions in the action sequence where preset variants agree or diverge.
- A **local uniqueness grouping**, comparing variations exclusively within that specific preset’s folder (e.g., variants of `film_inspired_coolB&W` and `film_inspired_boldB&W`).

### 2. Equivalence Class & Uniqueness Grouping (Global Level)

The global analysis reads JSON profiles recursively from the input tree (by default `./output/consistency`). Each profile is assigned to its most-specific equivalence group shared with at least one other profile. The comparisons are applied from most specific to least specific:

- `fully_identical`
- `differs_at_values`
- `differs_at_parameter_order`
- `differs_at_parameter_names`
- `differs_at_action_order`
- `differs_at_action_types` (same action count, but different action types)

The matching signatures preserve action and parameter order except where a class explicitly ignores that order. Parameter names use the flattened names described in `c2pa_uniqueness/flatten.py`. Each class below contains profiles that share the listed signature; profiles already assigned to a more-specific class are removed before the next comparison.

Examples use the shorthand `A{x:1, y:2}` for an action of type `A` with parameters `x=1` and `y=2`. Each pair illustrates the shared signature that places the profiles in that class:

| Class | Profiles share | Example |
| --- | --- | --- |
| `fully_identical` | Same action types in the same order, same parameter names in the same order, and same values. | `[A{x:1}]` and `[A{x:1}]` |
| `differs_at_values` | Same ordered actions and ordered parameter names; values differ. | `[A{x:1}]` and `[A{x:2}]` |
| `differs_at_parameter_order` | Same ordered actions and same parameter-name set per action, ignoring parameter order; no more-specific match was found. | `[A{x:1, y:2}]` and `[A{y:2, x:1}]` |
| `differs_at_parameter_names` | Same action types in the same order, but parameter names or their order differ; no more-specific match was found. | `[A{x:1}]` and `[A{y:1}]` |
| `differs_at_action_order` | Same action types, ignoring action order; no more-specific match was found. | `[A{x:1}, B{y:2}]` and `[B{y:2}, A{x:1}]` |
| `differs_at_action_types` | Same number of actions, but different action-type sequences; no more-specific match was found. | `[A{x:1}]` and `[B{x:1}]` |

These are equivalence classes of profiles, not a claim that every pair differs only in the named feature. The name describes the loosest signature the group shares after more-specific groups have been assigned. Groups contain two or more profiles. A profile that shares no signature with another profile at any stage, including action count, is categorized as `**UNIQUE**`.

The global pass includes JSON profile files found recursively in the input tree; this can include `_UNIQUE.json` files and originals in `old_variants/` when those are present.

### Usage

Execute the uniqueness analysis without additional arguments (it automatically reads from `./output/consistency/`):

```bash
bash run_uniqueness.sh
```

### Output Files

- **Terminal Summary:** High-level grouping statistics and uniqueness counts.
- **Global Report:** Saves a `uniqueness_report.json` file summarising the equivalence groups and unique profiles found in the global input tree.
- **Local Reports:** Generates JSON reports of action-slot differences and local uniqueness groups for inconsistent folders.

All files are saved to `./output/uniqueness`.

#### Example of Terminal Summary

```bash
Summary of the C2PA preset scan results for consistency and uniqueness.

Summary table: 146 folder(s)
  consistency: 144 full, 2 partial
  uniqueness:  137 full, 9 partial
Wrote output/summary_table.md
Wrote output/summary_grouped.json
Wrote output/summary_table.csv

Done.
```

---

## Folder Organization

```bash
c2pa-presets-analysis/
├─ c2pa_common/             # Shared constants, descriptions, and default paths
│  ├─ constants.py
│  ├─ info.py
│  └─ paths.py
├─ c2pa_consistency/    
│  ├─ __main__.py           # Entrypoint for c2pa_consistency
│  ├─ actions.py            # Action filtering
│  ├─ analyzer.py           # Analysis of inconsistent preset folders
│  ├─ compare.py            # Cluster images within a preset folder by order-independent action equality
│  ├─ constants.py          # Constants used across the c2pa_consistency module
│  ├─ info.py               # c2pa_consistency logo and versioning information
│  ├─ manifest.py           # Read and traverse manifest data structures
│  ├─ naming.py             # Derive a stable key for a fingerprint from its folder path
│  ├─ pipeline.py           # Orchestration: one preset folder in, JSON file(s) out
│  ├─ writer.py             # Write one JSON file per action-list cluster, mirroring the input tree
├─ c2pa_summary/            # Markdown, CSV, and grouped-JSON summary reports
│  ├─ __main__.py
│  └─ table.py
├─ c2pa_uniqueness/   
│  ├─ __main__.py           # Entrypoint for c2pa_uniqueness
│  ├─ compare.py            # Staged comparison between two presets' action lists, cheapest/coarsest checks first
│  ├─ constants.py          # Constants used across the c2pa_uniqueness module
│  ├─ flatten.py            # Shared parameter-flattening logic: generic K / K.value pairing
│  ├─ grouping.py           # Assign each preset to exactly one group
│  ├─ info.py               # c2pa_uniqueness logo and versioning information
│  ├─ loader.py             # Load presets produced by c2pa_consistency for uniqueness analysis
│  ├─ report.py             # Write grouping and slot-summary results as JSON, print terminal summaries
│  ├─ slot_summary.py       # Cross-preset action-slot summary for one folder
├─ DB/                      # Default path to presets   
├─ output/
│  ├─ consistency/          # Profiles and inconsistency reports
│  ├─ uniqueness/           # Global and local uniqueness reports
│  ├─ summary_table.md
│  ├─ summary_table.csv
│  └─ summary_grouped.json
├─ run_consistency.sh       # Run consistency analysis
├─ run_uniqueness.sh        # Run uniqueness analysis
├─ run.sh                   # Run the full analysis by default
└─ clean.sh                 # Remove output folder
```

---

## Requirements

### Python

Python 3.10 or later.

### c2patool

The analyzer relies on `c2patool` (v. 0.26.70) to read C2PA manifests from images. Install it before running the project.

**Option A — via Cargo (Rust):**

```bash
cargo install c2patool
```

Then make sure `~/.cargo/bin` is in your `PATH`:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

Add that line to your `~/.bashrc` or `~/.zshrc` to make it permanent.

**Option B — pre-built binary:**
Download the latest release for your platform from:
<https://github.com/contentauth/c2patool/releases>