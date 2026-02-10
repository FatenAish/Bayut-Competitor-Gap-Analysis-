#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="bayut-competitor-gap-v2"
REGION="us-central1"
EXPECTED_URL="https://bayut-competitor-gap-v2-798732426681.us-central1.run.app/"
GCLOUD_BIN="${GCLOUD_BIN:-gcloud}"

if ! command -v "${GCLOUD_BIN}" >/dev/null 2>&1; then
  if [[ -x "/home/ubuntu/google-cloud-sdk/bin/gcloud" ]]; then
    GCLOUD_BIN="/home/ubuntu/google-cloud-sdk/bin/gcloud"
  else
    echo "gcloud CLI is required but not found in PATH." >&2
    exit 1
  fi
fi

PROJECT_ID="${1:-${PROJECT_ID:-}}"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "Usage: PROJECT_ID=<your-project-id> ./deploy_cloud_run.sh" >&2
  echo "   or: ./deploy_cloud_run.sh <your-project-id>" >&2
  exit 1
fi

echo "Deploying ${SERVICE_NAME} to Cloud Run (${REGION})..."
"${GCLOUD_BIN}" run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8080 \
  --quiet

DEPLOYED_URL="$("${GCLOUD_BIN}" run services describe "${SERVICE_NAME}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
[[ "${DEPLOYED_URL}" == */ ]] || DEPLOYED_URL="${DEPLOYED_URL}/"

echo "Cloud Run service URL: ${DEPLOYED_URL}"
if [[ "${DEPLOYED_URL}" != "${EXPECTED_URL}" ]]; then
  echo "ERROR: URL mismatch." >&2
  echo "Expected: ${EXPECTED_URL}" >&2
  echo "Actual:   ${DEPLOYED_URL}" >&2
  exit 1
fi

echo "Deployment successful and URL matches expected endpoint."
