# C2PA Presets Analyzer

## Overview

This repository contains the C2PA-based analysis that led to the definition of: *Full Consistency (FC)*, *Partial Consistency (PC)*, *Full Uniqueness (FU)*, and *Partial Uniqueness (PU)*, as discussed in Sect. IV of our paper *"Enhanced image forensics through partial C2PA-based provenance information"*.

The analysis consists of two main steps:

- **Consistency analysis** (`c2pa_consistency`)
- **Uniqueness analysis** (`c2pa_uniqueness`)

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

Run the analysis by passing the path to your input presets directory. If omitted, the default defined in `./c2pa_consistency/constants.py` is used:

```bash
bash run_consistency.sh <path_to_prests>
```

### Output Files

The pipeline writes one JSON file per distinct filtered action profile. Output paths mirror the input folder structure under the generating software's directory (`Lightroom` or `Adobe Photoshop`).

- A folder with one profile is fully consistent and produces one JSON file.
- A folder with multiple profiles produces a base JSON file and `_variantN.json` files, plus an `inconsistency_report.md` when the inconsistency analysis is run.
- When you choose to further analyze inconsistencies, the clustering step may also write merged `_UNIQUE.json` files. These are JSON files despite the `_UNIQUE` name; they are not Markdown files and are not the global uniqueness result. The step groups profile files by their ordered sequence of actions and parameter names. Files with different sequences cannot be merged. For each matching group with at least two files, it writes a merged profile: parameter values that agree are retained, while values that differ are replaced with `"x_variable"`. If the profiles split into multiple matching groups (for example, because their partial action/parameter profiles differ), the step can write multiple files: `<preset>_UNIQUE.json`, `<preset>_UNIQUE_variant2.json`, and so on. Groups with only one file do not produce a merged file. Originals that contributed to a merged file are moved into an `old_variants/` subfolder.

Use the inconsistency report together with the merged `_UNIQUE.json` file(s) to review potential partial consistency: check that the shared actions and parameters remain the same and that the replaced values correspond to the expected preset-specific differences. The merged files are comparison aids, not an automatic PC verdict.

<!-- For each image, its manifest is taken (if present), and the claim_generator_info[name] and actions are extracted.
From the set of actions, ones with "action" and "parameters" are kept, except "c2pa.opened" (if present); for Lightroom specifically, the preset-label-only entry (e.g. c2pa.filtered / "Preset") is also dropped.

The resulting list is compared between images (order-independent on both actions and parameters); if one differs it is taken as a second sample to be compared with the remaining images.

The output is one or more JSON files, at least one per preset, stored in the output folder. The output folder is structured with the name of the software (taken from claim_generator_info[name]) and the same structure as the input folder, with the name of the preset as the last folder.

As discussed in the paper, we observed that only two Lightroom (LR) presets fail *FC* but yield *PC*: `film_inspired_coolB&W` and `film_inspired_boldB&W`.
Therefore, only for these presets, being characterized by the same reference partial action profile, a specific JSON file will be created for all inconsistent images (called variant in the code); an inconsistency_report will highlight the differences in the action profiles for all analyzed images.

Instead, in case of *FC* for a preset, a JSON file containing the preset name, actions, and parameter names and values is saved in the `./output/consistency/` directory (organized by application, i.e., Lightroom or Adobe Photoshop, and preset name). -->

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

In order, the comparison checks full action/parameter identity, parameter values, parameter ordering, parameter names, action ordering, and finally action types among profiles with the same action count. Unlike the consistency comparison, these uniqueness signatures preserve action and parameter order. `fully_identical` means the ordered action and parameter profiles, including values, match. A `differs_at_...` group identifies the most specific structure shared with another profile despite the named difference. At the final stage, profiles with the same number of actions are grouped even if their action types differ. A profile that shares no signature with another profile at any stage, including action count, is categorized as **unique**. Groups contain two or more profiles; ungrouped profiles are listed under `unique`.

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
Global uniqueness:
  fully_identical: 2 group(s), 4 preset(s)
    Group_1 (2 action(s)): 7 preset(s)
    Group_2 (1 action(s)): 2 preset(s)
  differs_at_values: 7 group(s), 14 preset(s)
    Group_1 (1 action(s)): 12 preset(s)
    Group_2 (1 action(s)): 12 preset(s)
    Group_3 (27 action(s)): 5 preset(s)
    Group_4 (23 action(s)): 3 preset(s)
    Group_5 (27 action(s)): 11 preset(s)
    Group_6 (20 action(s)): 11 preset(s)
    Group_7 (40 action(s)): 2 preset(s)
  differs_at_parameter_names: 23 group(s), 46 preset(s)
    Group_1 (24 action(s)): 9 preset(s)
    Group_2 (25 action(s)): 3 preset(s)
    Group_3 (30 action(s)): 2 preset(s)
    Group_4 (27 action(s)): 6 preset(s)
    Group_5 (39 action(s)): 4 preset(s)
    Group_6 (28 action(s)): 5 preset(s)
    Group_7 (29 action(s)): 4 preset(s)
    Group_8 (22 action(s)): 5 preset(s)
    Group_9 (35 action(s)): 2 preset(s)
    Group_10 (34 action(s)): 3 preset(s)
    Group_11 (41 action(s)): 3 preset(s)
    Group_12 (33 action(s)): 5 preset(s)
    Group_13 (40 action(s)): 5 preset(s)
    Group_14 (43 action(s)): 2 preset(s)
    Group_15 (36 action(s)): 4 preset(s)
    Group_16 (19 action(s)): 5 preset(s)
    Group_17 (38 action(s)): 3 preset(s)
    Group_18 (12 action(s)): 2 preset(s)
    Group_19 (18 action(s)): 4 preset(s)
    Group_20 (32 action(s)): 4 preset(s)
    Group_21 (14 action(s)): 2 preset(s)
    Group_22 (23 action(s)): 2 preset(s)
    Group_23 (16 action(s)): 4 preset(s)
  unique: 13 preset(s)
```

<!-- Building upon the consistency analysis, this step investigates whether a preset can be distinguished from all others in the database based solely on its action and parameter combinations. If it does, the preset is defined as **unique**.

While the consistency analysis established that most presets share identical actions and parameter values across images, this step evaluates whether a preset's specific combination of actions and parameters can uniquely identify it among all presets in the database.

The code in `./c2pa_uniqueness` will:

- Start from the results of the consistency analysis step.
- Iteratively check parameter matches between different preset versions to identify:
  - Missing or additional actions
  - Different action types (typically, all presets share the same `c2pa.action`, either one or two depending on the preset class)
  - Different parameter values for a given action
  - Full matches between actions and parameters
- Automatically group presets into the following categories:
  - `fully_identical`
  - `differs_at_values`
  - `differs_at_parameter_order`
  - `differs_at_parameter_names`
  - `differs_at_actions_order`
  - `differs_at_actions_type`

The procedure iterates over all possible groups and retains only those containing two or more presets (a single preset in a category is already considered unique).

Similar to the consistency check, the script prints a summary to the terminal and saves a complete report as a JSON file. A `uniqueness_report` summarizes the results for all consistent presets, while dedicated reports are generated for inconsistent presets (`film_inspired_coolB&W` and `film_inspired_boldB&W`).

description from main:
Task 1: for each folder flagged inconsistent by c2pa_consistency (has an
        inconsistency_report.md), report a positional action-slot summary
        (where in the sequence presets agree/split) plus a local uniqueness
        grouping among just that folder's own preset variants.
Task 2: across ALL presets found under output_path, group each preset into
        its single most-constrained equivalence class (one of 7 categories),
        or report it as unique if it matches nobody at any level.
-------------------

Global uniqueness:
  fully_identical: 2 group(s), 4 preset(s)
    Group_1 (2 action(s)): 7 preset(s)
    Group_2 (1 action(s)): 2 preset(s)
  differs_at_values: 7 group(s), 14 preset(s)
    Group_1 (1 action(s)): 12 preset(s)
    Group_2 (1 action(s)): 12 preset(s)
    Group_3 (27 action(s)): 5 preset(s)
    Group_4 (23 action(s)): 3 preset(s)
    Group_5 (27 action(s)): 11 preset(s)
    Group_6 (20 action(s)): 11 preset(s)
    Group_7 (40 action(s)): 2 preset(s)
  differs_at_parameter_names: 23 group(s), 46 preset(s)
    Group_1 (24 action(s)): 9 preset(s)
    Group_2 (25 action(s)): 3 preset(s)
    Group_3 (30 action(s)): 2 preset(s)
    Group_4 (27 action(s)): 6 preset(s)
    Group_5 (39 action(s)): 4 preset(s)
    Group_6 (28 action(s)): 5 preset(s)
    Group_7 (29 action(s)): 4 preset(s)
    Group_8 (22 action(s)): 5 preset(s)
    Group_9 (35 action(s)): 2 preset(s)
    Group_10 (34 action(s)): 3 preset(s)
    Group_11 (41 action(s)): 3 preset(s)
    Group_12 (33 action(s)): 5 preset(s)
    Group_13 (40 action(s)): 5 preset(s)
    Group_14 (43 action(s)): 2 preset(s)
    Group_15 (36 action(s)): 4 preset(s)
    Group_16 (19 action(s)): 5 preset(s)
    Group_17 (38 action(s)): 3 preset(s)
    Group_18 (12 action(s)): 2 preset(s)
    Group_19 (18 action(s)): 4 preset(s)
    Group_20 (32 action(s)): 4 preset(s)
    Group_21 (14 action(s)): 2 preset(s)
    Group_22 (23 action(s)): 2 preset(s)
    Group_23 (16 action(s)): 4 preset(s)
  unique: 13 preset(s)

Wrote output/uniqueness/uniqueness_report.json

--- -->

---

## Folder Organization

```bash
c2pa-compare-lr-presets/
├─ c2pa_consistency/    
│  ├─ __main__.py       # Entrypoint for c2pa_consistency
│  ├─ actions.py        # Action filtering
│  ├─ analyzer.py       # Analysis of inconsistent preset folders
│  ├─ compare.py        # Cluster images within a preset folder by order-independent action equality
│  ├─ constants.py      # Constants used across the c2pa_consistency module
│  ├─ info.py           # c2pa_consistency logo and versioning information
│  ├─ manifest.py       # Read and traverse manifest data structures
│  ├─ naming.py         # Derive a stable key for a fingerprint from its folder path
│  ├─ pipeline.py       # Orchestration: one preset folder in, JSON file(s) out
│  ├─ writer.py         # Write one JSON file per action-list cluster, mirroring the input tree

├─ c2pa_uniqueness/   
│  ├─ __main__.py       # Entrypoint for c2pa_uniqueness
│  ├─ compare.py        # Staged comparison between two presets' action lists, cheapest/coarsest checks first
│  ├─ constants.py      # Constants used across the c2pa_uniqueness module
│  ├─ flatten.py        # Shared parameter-flattening logic: generic K / K.value pairing
│  ├─ grouping.py       # Assign each preset to exactly one group
│  ├─ info.py           # c2pa_uniqueness logo and versioning information
│  ├─ loader.py         # Load presets produced by c2pa_consistency for uniqueness analysis
│  ├─ report.py         # Write grouping and slot-summary results as JSON, print terminal summaries
│  ├─ slot_summary.py   # Cross-preset action-slot summary for one folder

├─ output/              # Results of the consistency and uniqueness analysis
│  ├─ consistency/
├── ├─ Adobe Photoshop/
├── ├─ Lightroom/
│  ├─ uniqueness/ 

├─ clean.sh             # Teardown
├─ run_consistency.sh   # Setup and run consistency check
├─ run_uniqueness.sh    # Setup and run uniqueness check 
            
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