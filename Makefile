# Chanakya OSINT — Makefile (F0 skeleton → SHIP's real app targets).
#
# Two audiences, deliberately separated:
#
#   REVIEWER (Docker only, no Python, no venv):  make run · make ask · make ingest · make stop
#   DEVELOPER (needs `make install` first):      make check · make build · make extract · make beat
#
# The Python package lives in backend/; config/ + corpus/ stay at repo root and are resolved via
# CHANAKYA_ROOT (chanakya/settings.py), which is why the dev targets set it to $(CURDIR).

PY ?= python3
BACKEND := backend
VENV := $(BACKEND)/.venv
VPY := $(VENV)/bin/python

# One image name for BOTH reviewer paths, so `make run` and `docker run ghcr.io/...` are the same
# artifact by construction (md/07 "dev == prod"). Override IMAGE/TAG to build under another name.
IMAGE ?= ghcr.io/pragalbh-dev/osint
TAG ?= latest
CONTAINER ?= chanakya
PORT ?= 8000
URL := http://127.0.0.1:$(PORT)
CLI := $(PY) deploy/chanakya-cli.py --url $(URL)
SCENARIO ?= hq9p_primary
# `--env-file .env` is only passed when a .env actually exists — the app boots keyless and a reviewer
# who never created one must not hit a docker error.
ENV_FILE_ARG = $(shell test -f .env && echo --env-file .env)

.DEFAULT_GOAL := help
.PHONY: help install lint typecheck test check extract build ingest ask run image stop logs push beat

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
	cd $(BACKEND) && CHANAKYA_ROOT=$(CURDIR) .venv/bin/python -m pytest

check: lint typecheck test  ## Everything CI runs (ruff + mypy + pytest incl. gates)

# ── Reviewer path: one command from a clean clone ──────────────────────────────────────────────
#
# `make run` builds the production image (Node builds the SPA, Python installs the backend, and
# config/ + corpus/ + the pre-extracted claim bundles are baked in) and serves it. No key, no
# network, no volume: the app boots from the frozen bundles and /health flips 503 → 200 once the
# boot rebuild() lands. Set PORT=… if 8000 is taken on your box.

image:  ## Build the production image (tags $(IMAGE):$(TAG))
	docker build -t $(IMAGE):$(TAG) .

run: image  ## Build + serve the whole app (SPA + API) on one origin — THE reviewer command
	-@docker rm -f $(CONTAINER) >/dev/null 2>&1
	docker run -d --name $(CONTAINER) --restart unless-stopped $(ENV_FILE_ARG) \
		-p 127.0.0.1:$(PORT):8000 $(IMAGE):$(TAG)
	@printf 'waiting for /health'
	@for i in $$(seq 1 60); do \
		if curl -fsS $(URL)/health >/dev/null 2>&1; then \
			echo; curl -sS $(URL)/health; echo; \
			echo "  → open $(URL) in a browser (SPA + API, same origin)"; exit 0; fi; \
		printf '.'; sleep 1; done; \
	echo; echo "app did not become ready in 60s — see: make logs"; docker logs --tail 40 $(CONTAINER); exit 1

stop:  ## Stop and remove the running container
	-docker rm -f $(CONTAINER)

logs:  ## Tail the running container's logs
	docker logs -f --tail 100 $(CONTAINER)

push:  ## Push the image to GHCR (needs `docker login ghcr.io`; see deploy/README.md)
	docker push $(IMAGE):$(TAG)

# ── App targets against the RUNNING app (no venv needed — plain python3 + urllib) ───────────────

ingest:  ## Ingest a document into the running app: make ingest DOC=path/to/doc
	@test -n "$(DOC)" || { echo 'usage: make ingest DOC=corpus/scenarios/$(SCENARIO)/claims/<doc>.json'; exit 2; }
	$(CLI) ingest --doc "$(DOC)" $(if $(SOURCE_TYPE),--source-type "$(SOURCE_TYPE)")

ask:  ## Ask a cited multi-hop question of the running app: make ask Q="..."
	@test -n "$(Q)" || { echo 'usage: make ask Q="Trace the long-range SAM battery now based at Rahwali ..."'; exit 2; }
	$(CLI) ask --question "$(Q)" $(if $(SUBJECT),--subject "$(SUBJECT)")

# ── Developer targets (need `make install`) ────────────────────────────────────────────────────

build:  ## Rebuild the knowledge view from the frozen logs + config, and report what it holds
	cd $(BACKEND) && CHANAKYA_ROOT=$(CURDIR) .venv/bin/python -c "$$BUILD_PY"

extract:  ## Re-record the claim bundles from the raw corpus (KEYED: needs GEMINI_/ANTHROPIC_API_KEY)
	cd $(BACKEND) && CHANAKYA_ROOT=$(CURDIR) .venv/bin/python -m chanakya.ingest extract --scenario $(SCENARIO) $(EXTRACT_ARGS)

# The relocation tripwire, driven the way the design always specified: by an ingest, not a scripted
# reveal. Holds the 2025 Rahwali overhead passes out of the evidence log, rebuilds, ingests them,
# rebuilds again, and evaluates the armed observables over that before/after pair. Keyless + offline;
# STAGE overrides which documents arrive (e.g. `make beat STAGE="--stage d19_rahwali_confirm"`).
beat:  ## Run the relocation tripwire off a staged live ingest (before → ingest → after → alert)
	cd $(BACKEND) && CHANAKYA_ROOT=$(CURDIR) .venv/bin/python -m eval beat $(STAGE)

# `make build`'s body: boot the same keyless state the app boots, rebuild, and print the shape of the
# resulting graph (including what the boot seed deliberately withholds for the live-ingest demo).
define BUILD_PY
from chanakya.api.state import build_default_state, resolve_withheld_docs
from chanakya.config import ConfigStore
from chanakya import settings
state = build_default_state()
state.boot()
view = state.view()
withheld = resolve_withheld_docs(ConfigStore.seed_from(settings.config_dir()))
print(f"rebuilt: {len(view.nodes)} nodes, {len(view.edges)} edges, "
      f"{len(view.known_gaps)} known gaps, from {len(list(state.evidence.replay()))} claims")
print(f"withheld from the boot seed (ingest live to release): {', '.join(withheld) or '(none)'}")
endef
export BUILD_PY
