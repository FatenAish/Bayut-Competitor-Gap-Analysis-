#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-bayut-competitor-gap-v2}"
PROJECT_ID="${PROJECT_ID:-798732426681}"
REGION="${REGION:-us-central1}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Error: gcloud CLI is not installed." >&2
  echo "Install it first: https://cloud.google.com/sdk/docs/install" >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "Error: no active gcloud account found." >&2
  echo "Run: gcloud auth login" >&2
  exit 1
fi

echo "Deploying ${SERVICE_NAME} to Cloud Run (${REGION}, project ${PROJECT_ID})..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated

echo "Deployment started successfully."
