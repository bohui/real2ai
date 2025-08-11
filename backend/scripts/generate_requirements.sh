#!/usr/bin/env bash

set -euo pipefail

# Determine directories
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
BACKEND_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

cd "$BACKEND_DIR"

echo "Working directory: $BACKEND_DIR"

# Check uv availability
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: 'uv' is not installed. Install it from https://docs.astral.sh/uv/ and re-run." >&2
  exit 1
fi

# Ensure pyproject exists
if [ ! -f "pyproject.toml" ]; then
  echo "Error: pyproject.toml not found in $BACKEND_DIR" >&2
  exit 1
fi

# Ensure lockfile exists (for reproducible exports)
if [ ! -f "uv.lock" ]; then
  echo "No uv.lock found. Creating lockfile with 'uv lock'..."
  uv lock
fi

echo "Generating requirements.txt (production)..."
uv export --format requirements-txt --output requirements.txt

echo "Generating requirements-dev.txt (includes dev extras)..."
uv export --format requirements-txt --extra dev --output requirements-dev.txt

echo "\nDone. Files generated:"
echo " - $BACKEND_DIR/requirements.txt"
echo " - $BACKEND_DIR/requirements-dev.txt"


