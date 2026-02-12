# Cloud Run deployment

This repository includes a deterministic deployment script for the Streamlit app in `app.py`.

## Target service

- Service name: `bayut-competitor-gap-v2`
- Region: `us-central1`
- Expected URL: `https://bayut-competitor-gap-v2-798732426681.us-central1.run.app/`

## Deploy

1. Install Google Cloud CLI (`gcloud`).
2. Authenticate:

   ```bash
   gcloud auth login
   ```

3. Run deployment from repository root:

   ```bash
   PROJECT_ID=<your-gcp-project-id> ./deploy_cloud_run.sh
   ```

The script deploys from source, then verifies the deployed service URL matches the expected exact URL above.
