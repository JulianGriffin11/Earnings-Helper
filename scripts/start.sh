#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
exec uv run uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
