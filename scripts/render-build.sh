#!/usr/bin/env bash
# Build the frontend and install Python dependencies for deploy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

corepack enable
corepack prepare pnpm@10.14.0 --activate

pnpm install --frozen-lockfile
pnpm --filter frontend build

cd "$ROOT/backend"
uv sync --frozen --no-dev
