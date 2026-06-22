.PHONY: e2e e2e-headed backend frontend help

AETHOS_PS_WEB_URL ?= http://localhost:4201
AETHOS_PS_API_URL  ?= http://localhost:8011
AETHOS_TS_WEB_URL  ?= http://localhost:4202

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

## Start the backend API (port 8011)
backend:
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	  cd backend && uv run uvicorn app.main:app --reload --port 8011

## Start the Angular frontend (port 4201)
frontend:
	cd frontend && ng serve --port 4201

help:
	@grep -E '^##' Makefile | sed 's/^## //'
