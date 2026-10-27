# C2PA Presets Analysis

## Overview

This repository contains the C2PA-based analysis that led to the definition of: *Full Consistency (FC)*, *Partial Consistency (PC)*, *Full Uniqueness (FU)*, and *Partial Uniqueness (PU)*, as discussed in Sect. III of the paper *"Enhanced image forensics through partial C2PA-based provenance information"*.

The analysis consists of two main steps:

- **Consistency analysis** (`c2pa_consistency`)
- **Uniqueness analysis** (`c2pa_uniqueness`)

---

## Consistency analysis

A discussed in the paper, this analysis aims to verify if all manifests for a given preset share the same *action profile*; defined as the non-ordered set of actions and all the nested key-value pairs contained in the manifest.
For a certain preset the possible outcomes could be:

- *Full Consistency (FC)*: all manifests for that preset have the same full set of action and parameters, the **same full action profile**.
- *Partial Consistency (PC)*: all manifests have the **same partial action profile**, which is the aciton profile minus the parameters key-value pairs which add preset-specific details.

The code in `./c2pa_consistency` implement this analysis. 

### Methodology

The code process C2PA image manifests through a three-step pipeline:

#### 1. Extraction & Filtering

For each image, its mnaifest (if preset) is parsed to extract the software used (`claim_generator_info[name]`) and recorded actions.

- From the set of action, only those containing both `actions` and `parameters` key are retained, excluding `c2pa.opened` if present.
- For Adobe Lightroom speicially, preset-label-only entry (e.g. c2pa.filtered / "Preset") are also dropped

#### 2. Comparison

The resulting action lists are compared across images in an oder-independent manner on both actions and parameters. If an image's action profile differs, it is treated as a secodn reference sample to compare against the reamining images in the input folder.

### Usage

Run the analysis by pasing the path to your input presets directory (otherwise the default one defined in `./c2pa_consistency/constants.py` will used):

```bash
bash run_consistency.sh <path_to_prests>
```

### Output Files

The pipeline generates one or more JSON files (at least one per preset) stored in the output directory. Output paths mirrors the input folder structure, prefixed by the software name (either `Lightroom` or `Adobe Photoshop`; collected from the `claim_generator_info[name]`) and edning with the preset name folder.

- For *PC Presets*: as noted in the paper, only two Lightroom (LR) presets fail *FC* but yield *PC*: `film_inspired_coolB&W` and `film_inspired_boldB&W`. Because these presets share the same reference partial action profile, a dedicated JSON file is generated for all inconsistent images (referred to as *variants* in the code). An `inconsistency_report.md` deteails the specific profile difference across all analyzed images.

- For *PC Presets*: when a preset achieves *FC*, a JSON file containing the preset name, the actions, parameter names, and values is saved to `./output/consistency/` (organized by generator, i.e., Lightroom or Adobe Photoshop, and preset name).

---

## Uniqueness analysis

Based on the consistency analysis carried out previously, this step investigates whether a preset can be distinguished from all others in the database by the combination of its actions and parameters alone. A preset is defined as **unique** if its manifest signature cannot be matched by any other preset.

The analysis, implemented in `./c2pa_uniqueness`, is executed in two main tasks:

### 1. Inconsistent Preset Analysis (Local Level)

For each presets flagged as inconsistent during the consistency analysis (those containing an `inconsistency_report.md`), report:

- A **positional action-slot summary**, mapping exact positions in the action sequence where preset variants agree or diverge.
- A **local uniqueness grouping**, comparing variations exclusively within that specific preset’s folder (e.g., variants of `film_inspired_coolB&W` and `film_inspired_boldB&W`).

### 2. Equivalence Class & Uniqueness Grouping (Global Level)

For all presets found in the `./output/consistency` folder, group each preset into its single most-constrained equivalence classe from the fowlloing categorgies:

- `fully_identical`
- `differs_at_values`
- `differs_at_parameter_order`
- `differs_at_parameter_names`
- `differs_at_actions_order`
- `differs_at_actions_type`

Presets that match no other preset at any level are categorized as **unique**. The grouping output filters out singletons, retaining only groups containing two or more presets.

### Usage

Execute the uniqueness analysis without additional arguments (it will automatically reads from `./output/consistency/`):
```bash
bash run_uniqueness.sh
```

### Output Files

- **Terminal Summary:** High-level grouping statistics and uniqueness counts.
- **Global Report:** Saves a `uniqueness_report.json` file summarising the results for all consistent presets.
- **Local Reports:** Generates specific JSON reports of variant-level differences for inconsistent presets (`film_inspired_coolB&W` and `film_inspired_boldB&W`).

All files are saved to `./output/uniqueness`.

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

<!-- TODO check requirements -->

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