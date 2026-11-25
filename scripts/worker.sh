#!/usr/bin/env bash
# Run the ARQ background worker.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
require_venv
cd "$BACKEND_DIR"
"$PY" -m arq app.workers.settings.WorkerSettings
