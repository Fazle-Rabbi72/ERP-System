#!/usr/bin/env bash
# Shared helpers. Sourced by the other scripts.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
PY="$VENV_DIR/bin/python"

info() { printf '\033[1;34m[nexzen]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[nexzen] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "'$1' not found. $2"
}

require_venv() {
  [ -x "$PY" ] || fail "Virtualenv missing. Run: make setup"
}

has_frontend() { [ -f "$FRONTEND_DIR/package.json" ]; }
