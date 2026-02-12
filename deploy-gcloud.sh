#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${2:-us-central1}"
SERVICE_NAME="${3:-bayut-competitor-gap-analysis}"
GCLOUD_BIN="${GCLOUD_BIN:-}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: ./deploy-gcloud.sh <project-id> [region] [service-name]"
  echo "Example: ./deploy-gcloud.sh my-project us-central1 bayut-gap-analysis"
  exit 1
fi

if [[ -z "${GCLOUD_BIN}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    GCLOUD_BIN="$(command -v gcloud)"
  elif [[ -x "/home/ubuntu/google-cloud-sdk/bin/gcloud" ]]; then
    GCLOUD_BIN="/home/ubuntu/google-cloud-sdk/bin/gcloud"
  else
    echo "Error: gcloud CLI is not installed or not on PATH."
    exit 1
  fi
fi

ACTIVE_ACCOUNT="$("${GCLOUD_BIN}" auth list --filter='status:ACTIVE' --format='value(account)' 2>/dev/null || true)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "Error: no active gcloud account found."
  echo "Run: ${GCLOUD_BIN} auth login"
  exit 1
fi

echo "Setting active project to: ${PROJECT_ID}"
"${GCLOUD_BIN}" config set project "${PROJECT_ID}" >/dev/null

echo "Enabling required Google Cloud services..."
"${GCLOUD_BIN}" services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com >/dev/null

echo "Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
"${GCLOUD_BIN}" run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated
