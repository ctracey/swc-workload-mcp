#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
uv sync --quiet --directory "$DIR"
exec "$DIR/.venv/bin/swc-workload-mcp"
