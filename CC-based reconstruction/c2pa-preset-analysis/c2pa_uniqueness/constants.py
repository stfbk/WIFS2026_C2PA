"""Constants for c2pa_uniqueness."""

DEFAULT_INPUT_FOLDER = "./output/consistency/"
DEFAULT_OUTPUT_FOLDER = "./output/uniqueness/"

VALUE_SUFFIX = ".value"

# All 7 categories, finest (most constrained) to coarsest. This order
# drives the peeling algorithm in grouping.py.
CATEGORY_FULLY_IDENTICAL = "fully_identical"
CATEGORY_DIFFERS_AT_VALUES = "differs_at_values"
CATEGORY_DIFFERS_AT_PARAMETER_ORDER = "differs_at_parameter_order"
CATEGORY_DIFFERS_AT_PARAMETER_NAMES = "differs_at_parameter_names"
CATEGORY_DIFFERS_AT_ACTION_ORDER = "differs_at_action_order"
CATEGORY_DIFFERS_AT_ACTION_TYPES = "differs_at_action_types"
CATEGORY_DIFFERS_AT_ACTION_COUNT = "differs_at_action_count"

# Presets that share no signature with anyone, not even action count --
# truly unique in the pool. Reported separately, not as a "group".
KEY_UNIQUE = "unique"

STATUS_FULL_MATCH = "full_match"
STATUS_VALUE_MISMATCH = "value_mismatch"
STATUS_TYPE_MISMATCH = "type_mismatch"
STATUS_PARTIAL_PRESENCE = "partial_presence"

STATUS_LABELS = {
    STATUS_FULL_MATCH: "fully matched",
    STATUS_VALUE_MISMATCH: "same action, split on value(s)",
    STATUS_TYPE_MISMATCH: "different action type present",
    STATUS_PARTIAL_PRESENCE: "missing in some preset(s) / new action",
}

# Filenames written by c2pa_consistency / c2pa_uniqueness that must never
# be re-read as if they were preset JSON files.
INCONSISTENCY_REPORT_FILENAME = "inconsistency_report.md"
LOCAL_UNIQUENESS_FILENAME = "uniqueness_local.json"
NON_PRESET_FILENAMES = frozenset({LOCAL_UNIQUENESS_FILENAME})