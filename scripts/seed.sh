#!/usr/bin/env bash
# Seed baseline data: permissions, roles, first admin (added in steps F5-F6).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
[ -f "$BACKEND_DIR/app/seed.py" ] || fail "Seed module not available yet (added in steps F5-F6)."
cd "$BACKEND_DIR"
"$PY" -m app.seed
