# C2PA Preset-Matching Pipeline

## Overview

This repository contains the implementation of the `cn-mapper` tool described in Sect. III-A of the paper *"Enhanced image forensics through partial C2PA-based provenance information"*.

> **Enhanced image forensics through partial C2PA-based provenance information**  
> *Riccardo Ziglio, Eleonora Marchesini, Andrea Montibeller, Giulia Boato, Silvio Ranise, Cecilia Pasquini*  
> Accepted to IEEE Workshop on Information Forensics and Security 2026

The pipeline analyzes C2PA provenance manifests embedded in images and matches their edit action profiles against a database of known application presets (e.g., Adobe Lightroom and Adobe Photoshop).

---

## Preset-matching pipeline

### Methodology

The pipeline processes target image files through a multi-step workflow:

#### 1. Extraction & Filtering

For each image, its manifest is parsed using `c2patool` (via `helper.manifest.read_manifest_store`) to select the active manifest store and extract the software used (`claim_generator_info[name]`) along with recorded actions from `c2pa.actions` and `c2pa.actions.v2`.

- Actions lacking both a name and parameters are removed, and `c2pa.opened` is excluded.
- For Adobe Lightroom specifically, preset-label-only entries (e.g., parameter values containing `preset` or `none to`) are dropped.
- Remaining actions retain their original order and duplicates, passing only action names and key-value parameters to the matcher.

#### 2. Tool Identification & Preset Loading

The software name is normalized (`tool_id.identify_tool`) and checked for support (**Adobe Lightroom** or **Adobe Photoshop**).

- If no evaluable active manifest is present or the tool is unsupported, execution halts early and returns the corresponding result category.
- For supported tools, `cn_mapper.py` locates the matching subdirectory in `database/` and recursively loads all JSON preset files. A unique preset identifier is derived from its relative path (appended with entry keys if a single JSON file contains multiple presets).

#### 3. Matching & Scoring

Each database preset is scored against the image's extracted actions via `helper.preset_match.score_preset`:

- Action names must match strictly, and every parameter key defined in the preset must exist in the extracted action.
- Parameter values must match exactly, except where the preset specifies `x_variable`, which acts as a wildcard.
- Matches are strictly one-to-one; a single extracted action cannot satisfy multiple preset actions.

#### 4. Classification & Output

- **Exact Match (`same`)**: Occurs when all preset actions match with no extra unassigned image actions (e.g., adaptive presets).
- **Partial Match (`similar`)**: Occurs when at least one preset action matches, but the overall match is non-exact. The top 5 partial candidates are retained, and the highest percentage match is reported.

The CLI outputs a human-readable result. The underlying `ClassificationRecord` captures the category, tool, match counts, match percentage, matching preset names, and partial-match shortlist, while providing JSON serialization methods.

> **Note:** Helper functions can extract ingredient-manifest references, but the current CLI workflow evaluates actions from the active manifest only; it does not recursively analyze ingredient manifests or process batch image folders.

### Usage

Run the pipeline from the repository root by passing an image path:

```bash
./run.sh <path_to_image> [--database ./database]
```

Supported image filename extensions are `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.heic`, and `.avif` (case-insensitive). The tool analyzes one image per invocation.

## Result categories

- `no_manifest`: no usable active manifest was found for the image.
- `unsupported_tool`: the manifest does not identify one of the two supported applications.
- `same`: in case of *adaptive presets*, all actions in one or more presets matched with no extra image actions.
- `similar`: at least one preset action matched, but the match was not exact.
- `none_in_db`: no preset matched, or no preset database directory was available for the supported tool.

Ingredient-manifest references can be extracted by helper functions, but the current command-line flow compares actions from the active manifest only; it does not recursively analyze ingredient manifests or process image batches.

## Folder Organization

```bash
├── c2pa_mapper/               # Core pipeline package & execution logic
│   ├── __main__.py            # CLI entry point (argument parser & pipeline execution)
│   ├── orchestrator.py        # Manifest loader, active manifest selector & action preparer
│   ├── tool_id.py             # Tool generator detector (Lightroom, Adobe Photoshop)
│   ├── cn_mapper.py           # Preset loader, matcher driver & record generator
│   ├── models.py              # Data structures (ClassificationRecord & result categories)
│   └── info.py                # Package version metadata & CLI banner printer

├── helper/                    # Reusable manifest parsing & matching utilities
│   ├── manifest.py            # c2patool wrapper, JSON parser & action/ingredient extractor
│   ├── manifest_clean.py      # Action filtering and normalization sanitizer
│   ├── preset_match.py        # Wildcard-aware action matching and scoring algorithms
│   └── compare.py             # Order-independent action list clustering utility

├── database/                  # DB of partial CCs
│   ├── Lightroom/             # 118 Lightroom profiles (seasons, styles, adaptive, etc.)
│   └── Adobe Photoshop/       # 24 Photoshop profiles (cinematic, b&w, landscape, etc.)

├── input/                     # Sample test images with embedded C2PA manifests
├── run.sh                     # Setup and run c2pa_mapper on an input image
└── README.md                  
```

## Requirements

### Python

Python 3.10 or later.

### c2patool

The analyzer relies on `c2patool` to read C2PA manifests from images. Install it before running the project.

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
