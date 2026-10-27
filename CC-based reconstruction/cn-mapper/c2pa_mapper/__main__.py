"""
image(s) -> ToolID -> cn_mapper -> final model.

SINGLE IMAGE: classify it, then call the matching model handler directly
    on that one image. No output folder, no subfolder routing -- there's
    nothing to batch, so go straight to inference.

        ./run.sh ./input/rome.jpg --database ./database
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from c2pa_mapper.models import Category, ClassificationRecord
from c2pa_mapper.orchestrator import analyse_image
from c2pa_mapper.info import __c2pa_mapper_logo__, __description_c2pa__
from c2pa_mapper.tool_id import identify_tool
from c2pa_mapper.cn_mapper import cn_mapper

DEFAULT_DATABASE_DIR = "./database"
DEFAULT_IMAGE_PATH = "./input/X_Fake_StyleGAN3_conf-t-psi-0p5_00482.png"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="c2pa_mapper")
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=Path(DEFAULT_IMAGE_PATH),
        help="Path to the image to analyse",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DATABASE_DIR),
        help="Path to the preset database",
    )
    return parser.parse_args()

def main(image_path: Path, database_path: Path) -> ClassificationRecord:
    # 1. Extract manifest and actions from the image
    analysis = analyse_image(image_path)
    if analysis is None:
        return ClassificationRecord(
            image=image_path.name,
            category=Category.NO_MANIFEST,
            message=f"no evaluable: no valid manifest found for {image_path}",
        )

    # 2. Identify the editing tool (TOOL_ID)
    tool = identify_tool(analysis.tool)
    if tool is None:
        return ClassificationRecord(
            image=image_path.name,
            category=Category.UNSUPPORTED_TOOL,
            message=f"unsupported tool: {analysis.tool!r} in {image_path}",
        )

    # 3. Compare the extracted actions with the preset database (CN_MAPPER)
    # 4. Return the final result
    return cn_mapper(image_path.name, analysis.actions, tool, database_path)

if __name__ == "__main__":
    args = parse_args()

    if not args.database.exists():
        sys.exit(f"ERROR: Path not found {args.database}")

    print(__c2pa_mapper_logo__)
    print(__description_c2pa__)
    print()

    record = main(args.image, args.database)
    print(record.message)