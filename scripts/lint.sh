#!/usr/bin/env bash
# Lint + type check + security scan. Pass --fix to auto-fix formatting.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$BACKEND_DIR"
if [ "${1:-}" = "--fix" ]; then
  "$PY" -m ruff check --fix .
  "$PY" -m ruff format .
else
  "$PY" -m ruff check .
  "$PY" -m ruff format --check .
fi
if [ -d app ]; then
  "$PY" -m mypy
  "$PY" -m bandit -q -r app -c pyproject.toml || "$PY" -m bandit -q -r app
fi
if has_frontend; then
  (cd "$FRONTEND_DIR" && npm run lint --if-present && npm run typecheck --if-present)
fi
info "Lint OK."
