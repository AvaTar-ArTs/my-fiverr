#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOCAL_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if command -v uv >/dev/null 2>&1; then
    cd "$LOCAL_ROOT"
    uv sync --dev
else
    echo "uv is required for the supported Seller OS setup path." >&2
    echo "Install uv, then rerun: $0" >&2
    exit 1
fi

chmod +x "$SCRIPT_DIR/setup.sh"
chmod +x "$SCRIPT_DIR/test_mcp.py"

echo "Seller OS local environment is ready."
echo "Run: $SCRIPT_DIR/test_mcp.py"
