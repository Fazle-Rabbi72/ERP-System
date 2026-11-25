#!/usr/bin/env bash
# Backend tests (pytest) and frontend tests (Vitest) if present.
# Usage: scripts/test.sh [unit|integration|all]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
scope="${1:-all}"
cd "$BACKEND_DIR"
case "$scope" in
  unit) "$PY" -m pytest -m unit ;;
  integration) "$PY" -m pytest -m integration ;;
  all) "$PY" -m pytest --cov --cov-report=term-missing ;;
  *) fail "Unknown scope '$scope' (use unit|integration|all)." ;;
esac
if has_frontend && [ "$scope" != "integration" ]; then
  (cd "$FRONTEND_DIR" && npm run test --if-present -- --run)
fi
