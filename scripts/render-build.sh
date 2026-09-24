#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pnpm install --frozen-lockfile
pnpm --filter frontend build

cd "$ROOT/backend"
uv sync --frozen --no-dev
