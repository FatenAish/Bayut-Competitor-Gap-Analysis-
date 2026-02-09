#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${2:-us-central1}"
SERVICE_NAME="${3:-bayut-competitor-gap-analysis}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: ./deploy-gcloud.sh <project-id> [region] [service-name]"
  echo "Example: ./deploy-gcloud.sh my-project us-central1 bayut-gap-analysis"
  exit 1
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "Error: gcloud CLI is not installed or not on PATH."
  exit 1
fi

echo "Setting active project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "Enabling required Google Cloud services..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com >/dev/null

echo "Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated
