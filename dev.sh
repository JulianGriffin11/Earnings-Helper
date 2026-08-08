#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

free_port() {
  local port=$1
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "Freeing port $port..."
    kill -9 $pids 2>/dev/null || true
  fi
}

cleanup() {
  kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT INT TERM

free_port 8000
free_port 5173

(cd "$ROOT/backend" && uv run uvicorn app.main:app --reload) &
(cd "$ROOT/frontend" && pnpm run dev) &

wait


# To run: ./dev.sh
