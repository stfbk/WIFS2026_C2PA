#!/usr/bin/env bash
set -euo pipefail

# Directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PACKAGE="c2pa_consistency"   # the package directory name (contains __main__.py, info.py, pipeline.py, ...)

echo "Checking for system requirements..."

if command -v c2patool >/dev/null 2>&1 && c2patool --version >/dev/null 2>&1; then
    echo "c2patool is installed and working."
else
    echo "Error: c2patool is missing or not functioning properly."
    exit 1
fi

echo "Running $PACKAGE ..."
echo ""

cd "$SCRIPT_DIR" && python3 -m "$PACKAGE" "$@"