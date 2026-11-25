#!/usr/bin/env bash
# Create venv, install dependencies, create .env. Safe to re-run.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || PYTHON_BIN=python3
require_cmd "$PYTHON_BIN" "Install Python 3.12."
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' \
  || fail "Python 3.12 required."

if [ ! -x "$PY" ]; then
  info "Creating virtualenv at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
info "Installing backend dependencies"
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$BACKEND_DIR/requirements-dev.txt"

if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  chmod 600 "$ROOT_DIR/.env"
  info "Created .env from .env.example - edit it and replace every CHANGE_ME."
fi

if has_frontend; then
  require_cmd npm "Install Node.js 20+."
  info "Installing frontend dependencies"
  (cd "$FRONTEND_DIR" && npm ci 2>/dev/null || npm install)
else
  info "frontend/package.json not found yet (added in step F9) - skipping."
fi

command -v psql >/dev/null 2>&1 || info "WARNING: psql not found. Install PostgreSQL 16."
command -v redis-cli >/dev/null 2>&1 || info "WARNING: redis-cli not found. Install Redis 7."
info "Setup complete."
