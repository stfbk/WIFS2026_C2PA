#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INPUT_PATH_cons="${1:-./input_presets}"
OUTPUT_PATH_cons="${2:-./output/consistency}"
INPUT_PATH_uniq="${3:-./output/consistency}"
OUTPUT_PATH_uniq="${4:-./output/uniqueness}"
OUTPUT_PATH="${5:-./output/}"
REPORT_FILE="${6:-./output/summary_table.md}"

echo "Checking for system requirements..."
if command -v c2patool >/dev/null 2>&1 && c2patool --version >/dev/null 2>&1; then
    echo "c2patool is installed and working."
else
    echo "Error: c2patool is missing or not functioning properly."
    exit 1
fi
echo ""

echo "Which stage(s) do you want to run?"
echo "  1) Both (consistency + uniqueness/report)"
echo "  2) Consistency only"
echo "  3) Uniqueness/report only"
read -rp "Choice [1]: " choice
choice="${choice:-1}"

cd "$SCRIPT_DIR"

run_consistency() {
    echo ""
    echo "Running consistency analysis..."
    python3 -m c2pa_consistency "$INPUT_PATH_cons" "$OUTPUT_PATH_cons"
}

run_uniqueness_and_clustering() {
    echo ""
    echo "Checking if clustering is needed..."
    python3 -m c2pa_clustering.cluster "$OUTPUT_PATH_cons"
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
echo "Done."