#!/usr/bin/env bash
# Apply database migrations (Alembic arrives in step F3).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
[ -f "$BACKEND_DIR/alembic.ini" ] || fail "Alembic not configured yet (added in step F3)."
cd "$BACKEND_DIR"
"$PY" -m alembic upgrade "${1:-head}"
