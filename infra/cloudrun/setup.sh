#!/usr/bin/env bash
# One-time Cloud Run + Secret Manager setup for Aethos PS.
# Run this once from the repo root before the first deploy.
#
# Usage:
#   chmod +x infra/cloudrun/setup.sh
#   ./infra/cloudrun/setup.sh <GCP_PROJECT_ID>
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - Billing enabled on the GCP project

set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <GCP_PROJECT_ID>}"

echo "Setting up Aethos PS infrastructure on GCP project: ${PROJECT_ID}"
echo ""

# ── 1. Enable required APIs ────────────────────────────────────────────────────
echo "[1/3] Enabling GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project "${PROJECT_ID}"

# ── 2. Create Secret Manager secret ───────────────────────────────────────────
echo "[2/3] Creating Secret Manager secret..."
gcloud secrets create aethos-ps-secrets \
    --replication-policy="automatic" \
    --project "${PROJECT_ID}" 2>/dev/null || echo "  Secret 'aethos-ps-secrets' already exists — skipping."

# ── 3. Derive required secret keys from api-service.yaml ──────────────────────
echo "[3/3] Required secret keys (add all values in Secret Manager console):"
REQUIRED_KEYS=$(grep 'key:' "$(dirname "$0")/api-service.yaml" | awk '{print $2}' | sort -u)
for key in ${REQUIRED_KEYS}; do
    echo "  - ${key}"
done

echo ""
echo "Infrastructure ready."
echo ""
echo "Next steps:"
echo "  1. Add all secret values at:"
echo "     https://console.cloud.google.com/security/secret-manager?project=${PROJECT_ID}"
echo ""
echo "  2. Add GitHub repository secrets:"
echo "     GCP_PROJECT_ID  = ${PROJECT_ID}"
echo "     GCP_SA_KEY      = <service account JSON key with Cloud Run + GCR + Secret Manager access>"
echo "     VERCEL_TOKEN    = <Vercel personal access token>"
echo "     VERCEL_ORG_ID   = <Vercel org ID from vercel.com/account>"
echo "     VERCEL_PROJECT_ID = <Vercel project ID from project settings>"
echo ""
echo "  3. Push to main — GitHub Actions handles build, push, and deploy."
