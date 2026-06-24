.PHONY: e2e e2e-headed demo-ready backend frontend help

AETHOS_PS_WEB_URL ?= http://localhost:4201
AETHOS_PS_API_URL  ?= http://localhost:8011
AETHOS_TS_WEB_URL  ?= http://localhost:4202
DEMO_E2E_SPECS ?= e2e/demo-v2-meridian.spec.ts
DEMO_TENANT_ID ?=

## Run the full Playwright e2e suite (headless, chromium only)
e2e:
	cd frontend && \
	  AETHOS_PS_WEB_URL=$(AETHOS_PS_WEB_URL) \
	  AETHOS_PS_API_URL=$(AETHOS_PS_API_URL) \
	  AETHOS_TS_WEB_URL=$(AETHOS_TS_WEB_URL) \
	  npx playwright test --project=chromium

## Run e2e in headed mode with slow-mo (useful for local debugging)
e2e-headed:
	cd frontend && \
	  AETHOS_PS_WEB_URL=$(AETHOS_PS_WEB_URL) \
	  AETHOS_PS_API_URL=$(AETHOS_PS_API_URL) \
	  AETHOS_TS_WEB_URL=$(AETHOS_TS_WEB_URL) \
	  npx playwright test --project=chromium --headed

## Reset/seed a demo tenant, smoke the API, then run selected demo e2e specs
demo-ready:
	AETHOS_PS_WEB_URL=$(AETHOS_PS_WEB_URL) \
	AETHOS_PS_API_URL=$(AETHOS_PS_API_URL) \
	AETHOS_TS_WEB_URL=$(AETHOS_TS_WEB_URL) \
	DEMO_TENANT_ID="$(DEMO_TENANT_ID)" \
	DEMO_E2E_SPECS="$(DEMO_E2E_SPECS)" \
	./scripts/demo_readiness.sh

## Start the backend API (port 8011)
backend:
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	  cd backend && uv run uvicorn app.main:app --reload --port 8011

## Start the Angular frontend (port 4201)
frontend:
	cd frontend && ng serve --port 4201

help:
	@grep -E '^##' Makefile | sed 's/^## //'
