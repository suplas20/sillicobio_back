#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-venv/bin/python}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

args=(
  -m uvicorn
  app.main:app
  --host "$HOST"
  --port "$PORT"
)

if [[ "${RELOAD:-0}" == "1" ]]; then
  args+=(--reload --reload-dir app)
fi

exec "$PYTHON_BIN" "${args[@]}"
