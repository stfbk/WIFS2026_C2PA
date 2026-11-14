#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Defaults live in c2pa_common/paths.py (the single place to edit them)
default_path() { python3 -c "from c2pa_common import paths; print(paths.$1)"; }

INPUT_PATH_cons="${1:-$(default_path INPUT_PRESETS)}"
OUTPUT_PATH_cons="${2:-$(default_path CONSISTENCY_OUTPUT)}"
INPUT_PATH_uniq="${3:-$(default_path UNIQUENESS_INPUT)}"
OUTPUT_PATH_uniq="${4:-$(default_path UNIQUENESS_OUTPUT)}"
OUTPUT_PATH="${5:-$(default_path OUTPUT_ROOT)}"
REPORT_FILE="${6:-$(default_path SUMMARY_TABLE)}"
GROUPED_FILE="${7:-$(default_path SUMMARY_GROUPED)}"

echo "Checking for system requirements..."
if command -v c2patool >/dev/null 2>&1 && c2patool --version >/dev/null 2>&1; then
    echo "c2patool is installed and working."
else
    echo "Error: c2patool is missing or not functioning properly."
    exit 1
fi
echo ""

# echo "Which stage(s) do you want to run?"
# echo "  1) Both (consistency + uniqueness/report)"
# echo "  2) Consistency only"
# echo "  3) Uniqueness/report only"
# read -rp "Choice [1]: " choice
choice="${choice:-1}"

run_consistency() {
    echo ""
    echo "Running consistency analysis..."
    python3 -m c2pa_consistency "$INPUT_PATH_cons" "$OUTPUT_PATH_cons"
}

run_uniqueness_and_clustering() {
    echo ""
    echo "Checking if clustering is needed..."
    python3 -m c2pa_consistency.cluster "$OUTPUT_PATH_cons"
    echo ""
    echo "Running uniqueness analysis..."
    python3 -m c2pa_uniqueness "$INPUT_PATH_uniq" "$OUTPUT_PATH_uniq"
}

case "$choice" in
    1) run_consistency; run_uniqueness_and_clustering ;;
    2) run_consistency ;;
    3) run_uniqueness_and_clustering ;;
    *) echo "Invalid choice."; exit 1 ;;
esac

echo ""
echo "Building summary table..."
python3 -m c2pa_summary "$OUTPUT_PATH_cons" "$REPORT_FILE" "$GROUPED_FILE"

echo ""
echo "Done."