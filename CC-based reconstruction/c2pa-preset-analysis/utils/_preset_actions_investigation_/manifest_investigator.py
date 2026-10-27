"""
iterate over all presets in ./results/_preset_actions_ and check common actions to all presets
expectation: c2pa.coloradjustment & c2pa.filtered should be the most common actions, compute also che most common parameters

save the data as a dict: {
    'action': {
        'param_name: value
        }
}

done for each preset so it's easier to comparer

"""

import argparse
import copy     
import json
import sys
from datetime import datetime
from pathlib import Path
import pprint

from c2pa_prescan.action_extractor import read_manifest_store, get_raw_actions, strip_opened


# supported image file extensions 
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}
)


def derive_preset_stem(folder: Path) -> str:
    """
    Build the preset stem used for file and folder names.

    Format: ``<category>_<style>_<preset_name>``

    *category* and *style* come from the last two meaningful path segments
    of *folder* (segments listed in :data:`~c2pa_pkg.constants.PATH_SKIP`
    are ignored).  *preset_name* comes from :func:`extract_preset_name`.
    
    --------
    Examples
   
        folder ./lr-presets/season/autumn  +  "None to SP01"  →  season_autumn_SP01
        folder ./lr-presets/season/autumn  +  no preset       →  season_autumn_None
    """
    parts = [p for p in folder.resolve().parts if p.lower() not in IMAGE_EXTENSIONS and p not in ("/", "\\", "")]

    print(f"parts: {parts}")

    category    = parts[-3].lower().replace(" ", "_") if len(parts) >= 2 else "unknown"
    style       = parts[-2].lower().replace(" ", "_") if len(parts) >= 1 else "unknown"
    # preset_name = extract_preset_name(actions) # solution that checks the preset_name from actions and extracts it -> to be simplified in a single function
    file_name = parts[-1] #.replace(".jpg", "") # naive way from folder structure
    # breakpoint()
    # print(f"{category}_{style}_{file_name}")
    # breakpoint()
    # return category, style #, preset_name
    # preset_stem = f'{category}_{style}'
    return category, style

def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/lr-presets/_test_/NEW_LR_PRESETS2TEST/LR_adaptivePresets/blurBgStrong/")
    out_path = Path(f'./{input_path.resolve().parts[-1]}_collapsed_images.json')
    print(out_path)
    # breakpoint()

    if not input_path.exists():
        sys.exit(f"ERROR: Path not found {input_path}")
    
    print(f"Scanning '{input_path}' and all subfolders for images...")
    image_files: list[Path] = sorted(f for f in input_path.rglob("*")  if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS)

    print(f"Found {len(image_files)} total images to process.\n")

    # image_files: list[Path] = sorted(f for f in input_path.iterdir() if f.suffix.lower() in IMAGE_EXTENSIONS)

    # Target structure: {preset_name: {image_name: {action_name: {param: value}}}}
    img_analysis: dict = {}

    for img_path in image_files:
        print(f"  Extracting: {img_path.name}")
        
        # Fetch raw manifest data for THIS image specifically
        mj = read_manifest_store(img_path)
        raw_actions = strip_opened(get_raw_actions(mj) if mj else [])
        
        _, preset_style = derive_preset_stem(img_path)
        # print(f"Preset stem found: {preset_stem}")
        
        # initialize the nested dictionary layers
        if preset_style not in img_analysis:
            img_analysis[preset_style] = {}
            
        # Collapse the actions list on-the-fly into the clean nested parameter structure
        collapsed_actions = {}
        for act in raw_actions:
            action_name = act.get('action')
            params = act.get('parameters', {})

            param_key = params.get('com.adobe.acr')
            param_value = params.get('com.adobe.acr.value')

            if action_name not in collapsed_actions:
                collapsed_actions[action_name] = {}
            
            if param_key:
                collapsed_actions[action_name][param_key] = param_value

        # Save to the key format: {preset_name: {image_name: collapsed_actions}}
        img_analysis[preset_style][img_path.name] = collapsed_actions

    print("\n--- Final Structured Data ---")
    pprint.pprint(img_analysis)

    # # Save the output to a local JSON file
    try:
        out_path.write_text(json.dumps(img_analysis, indent=2), encoding="utf-8")
        print(f"\nSuccessfully saved results to: {out_path.resolve()}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()