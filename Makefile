# Nexzen ERP - task runner. Delegates to scripts/ so Windows, Linux and macOS behave the same.
# Windows: requires GNU make (e.g. `winget install GnuWin32.Make`); otherwise call scripts\*.ps1 directly.

ifeq ($(OS),Windows_NT)
  RUN = powershell -NoProfile -ExecutionPolicy Bypass -File
  EXT = ps1
else
  RUN = bash
  EXT = sh
endif

.PHONY: help setup migrate seed dev test lint

help:
	@echo "Targets: setup | migrate | seed | dev | test | lint"

setup:
	$(RUN) scripts/setup.$(EXT)

migrate:
	$(RUN) scripts/migrate.$(EXT)

seed:
	$(RUN) scripts/seed.$(EXT)

dev:
	$(RUN) scripts/dev.$(EXT)

test:
	$(RUN) scripts/test.$(EXT)

lint:
	$(RUN) scripts/lint.$(EXT)
