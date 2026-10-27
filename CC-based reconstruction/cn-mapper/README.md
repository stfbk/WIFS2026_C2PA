# C2PA preset-matching pipeline (cn-mapper)

This repository contains the implementation of the cn-mapper described in section III A of our paper *"Enhanced image forensics through partial C2PA-based provenance information"*.

## Example usage

From the repository root, pass an image path:

```bash
./run.sh ./input/rome.jpg --database ./database
```

Supported image filename extensions are `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.heic`, and `.avif` (case-insensitive). The tool analyzes one image per invocation.

## Processing flow

1. `run.sh` resolves the repository directory, verifies `c2patool --version` succeeds, and runs `python3 -m c2pa_mapper` with the supplied arguments.
2. `c2pa_mapper.__main__` checks that the preset database path exists and calls `analyse_image`.
3. `orchestrator.analyse_image` rejects unsupported filename extensions, invokes `c2patool` through `helper.manifest.read_manifest_store`, and selects the active manifest. It reads the claim-generator name and extracts actions from the `c2pa.actions` and `c2pa.actions.v2` assertions.
4. `helper.manifest_clean.filter_actions` removes actions without a name or parameters and excludes `c2pa.opened`. For Lightroom it also removes actions whose parameter values contain the label terms `preset` or `none to`, which are treated as preset-name-only entries. Remaining actions retain their order and duplicates, with only the action name and parameters passed on.
5. `tool_id.identify_tool` normalizes the claim-generator name to lowercase and accepts only `lightroom` or `adobe photoshop`. If there is no evaluable active manifest or the tool is unsupported, the CLI reports the corresponding result without attempting preset matching.
6. `cn_mapper` maps the tool name to its database subdirectory and recursively loads its JSON preset files. A preset identifier is derived from its path relative to the tool directory; if a JSON file contains multiple preset entries, the entry key is appended to the identifier.
7. `helper.preset_match.score_preset` compares each preset action to the extracted actions. Action names must match, every preset parameter key must be present, and values must match except where the preset value is `x_variable`, which acts as a wildcard. Matching is one-to-one, so a single extracted action cannot satisfy multiple preset actions.
8. The mapper classifies a preset as an exact match when all of its actions match and there are no extra extracted actions. Otherwise, presets with at least one matched action are partial candidates. The top five partial candidates are retained in the result; the highest percentage is reported as the similar preset.
9. The CLI prints the resulting human-readable message. The `ClassificationRecord` also carries the category, tool, match counts, percentage, matching preset names, and partial-match shortlist, and provides a JSON conversion method for callers.

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
