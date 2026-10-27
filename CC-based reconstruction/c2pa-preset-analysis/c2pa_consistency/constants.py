"""
constants used across the c2pa-consistency module.
"""
#--------------------------------------
# main.py
#--------------------------------------

DEFAULT_INPUT_FOLDER = "./input_presets"
DEFAULT_OUTPUT_FOLDER = "./output/consistency"
BAR_WIDTH = 30

#--------------------------------------
# Shared constants
#--------------------------------------
# supported image file extensions 
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".avif"}
)

# Folder-name fragments ignored when building the preset stem from the path
# e.g.  lr-presets/season/autumn  →  season_autumn_…
# NOTE: to be updated with the actual folder structure where presets data is stored
PATH_SKIP: frozenset[str] = frozenset(
    {"lr-presets", "presets", "lightroom", "."}
)

EXCLUDED_ACTIONS = {"c2pa.opened"}
IGNORE_LR_NAMES = {"preset", "none to"}

#------------------------------------------
# Analyzer.py
#------------------------------------------

REPORT_FILENAME = "inconsistency_report.md"
ACTION_COL_WIDTH = 20
VALUE_COL_WIDTH = 10
VALUE_SUFFIX = ".value"
# ANSI colors cycled per distinct value within a row, so cells sharing the
# same value are visually grouped.
ROW_COLORS = [
    "\033[36m",   # cyan
    "\033[33m",   # yellow
    "\033[35m",   # magenta
    "\033[32m",   # green
    "\033[34m",   # blue
    "\033[31m",   # red
]
DIM = "\033[2m"     # used for blank/missing cells
RESET = "\033[0m"
BOLD = "\033[1m"