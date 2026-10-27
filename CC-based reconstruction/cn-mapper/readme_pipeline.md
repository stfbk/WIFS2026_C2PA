# C2PA preset-matching pipeline

This repository contains a command-line tool that reads the C2PA manifest embedded in one image and compares its recorded editing actions with JSON action lists for Adobe Lightroom and Adobe Photoshop presets. It reports whether the actions match a known preset exactly, resemble one, or have no usable database match.

## Repository contents

- `c2pa_wifs/` contains the command-line entry point and the classification pipeline:
  - `__main__.py` parses the image and database arguments, runs the pipeline, and prints the result.
  - `orchestrator.py` reads the image manifest, selects its active manifest, and prepares its actions.
  - `tool_id.py` recognizes supported claim-generator names: `Lightroom` and `Adobe Photoshop`.
  - `cn_mapper.py` loads the presets for the identified tool, scores them, and creates a classification record.
  - `models.py` defines the result categories and the `ClassificationRecord` data structure.
  - `info.py` holds the package version and the command-line banner.
- `helper/` contains reusable manifest and action utilities:
  - `manifest.py` invokes `c2patool`, reads manifest JSON, selects active-manifest data, and extracts actions and ingredient references.
  - `manifest_clean.py` filters actions that are not useful for preset comparison.
  - `preset_match.py` performs wildcard-aware action matching and scoring.
  - `compare.py` clusters action lists by order-independent equality; this is a utility and is not part of the current single-image command path.
- `database/` contains 142 JSON preset files: 118 under `Lightroom/` and 24 under `Adobe Photoshop/`. Each file maps one or more preset identifiers to ordered lists of C2PA actions and parameters. The directory hierarchy organizes presets into families such as Lightroom seasons, styles, and adaptive presets, and Photoshop black-and-white, cinematic, creative, landscape, portrait, and other groups.
- `input/` contains sample image files for trying the command-line tool.
- `run.sh` checks that `c2patool` is installed and working, then launches the Python package.
- `README.md` is the repository's current GitLab template README; this file documents the implementation and pipeline.

## Requirements and usage

The command runs with Python 3 and requires the `c2patool` executable to be available on `PATH`. The repository does not include a Python dependency manifest; the code uses the Python standard library.

From the repository root, pass an image path:

```bash
./run.sh ./input/rome.jpg --database ./database
```

The database argument is optional and defaults to `./database`. The image argument is also optional in the parser, but it is best to provide it explicitly because the configured default image path may not exist in the checked-in `input/` directory.

Supported image filename extensions are `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.heic`, and `.avif` (case-insensitive). The tool analyzes one image per invocation.

## Processing flow

1. `run.sh` resolves the repository directory, verifies `c2patool --version` succeeds, and runs `python3 -m c2pa_wifs` with the supplied arguments.
2. `c2pa_wifs.__main__` checks that the preset database path exists and calls `analyse_image`.
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
- `same`: all actions in one or more presets matched with no extra image actions.
- `similar`: at least one preset action matched, but the match was not exact.
- `none_in_db`: no preset matched, or no preset database directory was available for the supported tool.

Ingredient-manifest references can be extracted by helper functions, but the current command-line flow compares actions from the active manifest only; it does not recursively analyze ingredient manifests or process image batches.
