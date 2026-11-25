# Nexzen ERP

Product of Nexzen Solution Ltd. Multi-tenant (cloud) and single-tenant (on-premise) ERP for Bangladeshi businesses.

## Prerequisites (installed locally, no Docker)
- Python 3.12, Node.js 20+, PostgreSQL 16, Redis 7, Git
- Optional: GNU make (Windows scripts also work without it)
- WSL is NOT required. On Windows use the `.ps1` scripts; to run or syntax-check the `.sh` scripts use Git Bash (`C:\Program Files\Git\bin\bash.exe`, installed with Git for Windows).
- Windows: add PostgreSQL's and Redis's `bin` folders to `PATH` so `psql` and `redis-cli` are found by `setup`.

## Quick start
| Task | Make | Linux/macOS | Windows |
|---|---|---|---|
| Setup | `make setup` | `bash scripts/setup.sh` | `scripts\setup.ps1` |
| Migrate | `make migrate` | `bash scripts/migrate.sh` | `scripts\migrate.ps1` |
| Seed | `make seed` | `bash scripts/seed.sh` | `scripts\seed.ps1` |
| Dev | `make dev` | `bash scripts/dev.sh` | `scripts\dev.ps1` |
| Test | `make test` | `bash scripts/test.sh [unit\|integration\|all]` | `scripts\test.ps1 -Scope unit` |
| Lint | `make lint` | `bash scripts/lint.sh [--fix]` | `scripts\lint.ps1 -Fix` |

After `setup`, edit `.env` and replace every `CHANGE_ME`. Never commit `.env`.

## Layout
```
backend/    FastAPI app (router -> service -> repository -> model)
frontend/   React + TypeScript (added in step F9)
scripts/    .sh and .ps1 automation
infra/      systemd, nginx (F8); optional-docker/ later
docs/       documentation
```

## Status
Foundation step F1 (repo scaffold) only. Later steps are added on request.
