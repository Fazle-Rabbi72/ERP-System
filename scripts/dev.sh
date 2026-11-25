#!/usr/bin/env bash
# Run API (hot reload) and, if present, the frontend dev server.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
[ -f "$BACKEND_DIR/app/main.py" ] || fail "app/main.py not found yet (added in step F2)."

pids=()
cleanup() { for p in "${pids[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM

(cd "$BACKEND_DIR" && "$PY" -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000) &
pids+=($!)
if has_frontend; then
  (cd "$FRONTEND_DIR" && npm run dev) &
  pids+=($!)
fi
wait
