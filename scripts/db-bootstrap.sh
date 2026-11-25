#!/usr/bin/env bash
# Bootstrap PostgreSQL roles and least-privilege grants (idempotent).
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$BACKEND_DIR"
"$PY" -m app.core.db_bootstrap
