#!/usr/bin/env bash
set -euo pipefail

RESULTS_DIR="results"

echo "Cleaning up..."

if [ -d "$RESULTS_DIR" ]; then
  echo "  Removing results folder ($RESULTS_DIR) ..."
  rm -rf "$RESULTS_DIR"
else
  echo "  No results folder found, skipping."
fi

echo "Done."