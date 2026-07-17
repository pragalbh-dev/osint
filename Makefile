# Chanakya OSINT — Makefile (F0 skeleton; SHIP fills the app targets).
#
# F0 wires the dev loop real (install/lint/typecheck/test — needed by CI + the acceptance gate);
# the app targets (extract/build/ingest/ask/run) are stubs that SHIP implements (master §4.1, §7).
# The Python package lives in backend/; config/ + corpus/ stay at repo root.

PY ?= python3
BACKEND := backend
VENV := $(BACKEND)/.venv
VPY := $(VENV)/bin/python

.DEFAULT_GOAL := help
.PHONY: help install lint typecheck test check extract build ingest ask run

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create the venv and install backend + dev deps
	$(PY) -m venv $(VENV)
	$(VPY) -m pip install --upgrade pip
	$(VPY) -m pip install -e "$(BACKEND)[dev]"

lint:  ## ruff (lint)
	cd $(BACKEND) && .venv/bin/ruff check .

typecheck:  ## mypy (types)
	cd $(BACKEND) && .venv/bin/mypy

test:  ## Full test suite incl. the G1–G12 abstraction gates
	cd $(BACKEND) && .venv/bin/python -m pytest

check: lint typecheck test  ## Everything CI runs (ruff + mypy + pytest incl. gates)

# ── App targets (F0 stubs → SHIP implements; master §7) ────────────────────────────────────────

extract:  ## [SHIP] Extract claims from the raw corpus (keyed LLM) → seed bundles
	@echo "TODO (SHIP): make extract — LLM extraction over corpus/ → claim bundles"

build:  ## [SHIP] Rebuild the knowledge view from the logs + config
	@echo "TODO (SHIP): make build — rebuild() the view"

ingest:  ## [SHIP] Ingest a document: make ingest DOC=path/to/doc
	@echo "TODO (SHIP): make ingest DOC=$(DOC) — append → rebuild → observable-eval"

ask:  ## [SHIP] Ask a cited multi-hop question: make ask Q="..."
	@echo "TODO (SHIP): make ask Q=\"$(Q)\" — bounded ReAct agent"

run:  ## [SHIP] Build the Docker image and serve the app
	@echo "TODO (SHIP): make run — docker build + serve (FastAPI + SPA)"
