#!/bin/bash
# Usage: ./deploy.sh [test]
#   (no argument) — deploy to coha-gcloud (production)
#   test          — deploy to coha-gcloud-test

set -e

REGION="us-west1"

if [ "${1}" = "test" ]; then
    SERVICE="coha-gcloud-test"
else
    SERVICE="coha-gcloud"
fi

echo "Deploying to Cloud Run service: ${SERVICE} (region: ${REGION})"

# Load env vars from .env.local (gitignored) and pass them to Cloud Run.
# This ensures secrets are never dropped by a deployment, without storing
# them in the repository.
ENV_FILE=".env.local"
ENV_VAR_ARG=""
if [ -f "${ENV_FILE}" ]; then
    echo "Loading environment variables from ${ENV_FILE}..."
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Skip blank lines and comments
        [[ -z "$key" || "$key" == \#* ]] && continue
        if [ -z "${ENV_VAR_ARG}" ]; then
            ENV_VAR_ARG="${key}=${value}"
        else
            ENV_VAR_ARG="${ENV_VAR_ARG},${key}=${value}"
        fi
    done < "${ENV_FILE}"
    gcloud run deploy "${SERVICE}" --source . --region "${REGION}" \
        --update-env-vars "${ENV_VAR_ARG}"
else
    echo "WARNING: ${ENV_FILE} not found — deploying without updating env vars."
    echo "Create ${ENV_FILE} with your secret values (see Deployment.md) to avoid dropping them."
    gcloud run deploy "${SERVICE}" --source . --region "${REGION}"
fi

echo ""
echo "Checking environment variables on ${SERVICE}..."

# Fetch env var names currently set on the service
DEPLOYED_VARS=$(gcloud run services describe "${SERVICE}" \
    --region "${REGION}" \
    --format="value(spec.template.spec.containers[0].env[].name)" 2>/dev/null \
    | tr ';' '\n')

REQUIRED_VARS=(
    COHA_MAPS_API_KEY
    COHA_GOOGLE_MAP_ID
    COHA_GCP_PROJECT_ID
    COHA_ADMIN_PASSWORD
)

MISSING=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if ! echo "${DEPLOYED_VARS}" | grep -qx "${VAR}"; then
        MISSING+=("${VAR}")
    fi
done

if [ ${#MISSING[@]} -eq 0 ]; then
    echo "All required environment variables are set."
else
    echo ""
    echo "WARNING: The following required environment variables are not set on ${SERVICE}:"
    for VAR in "${MISSING[@]}"; do
        echo "  - ${VAR}"
    done
    echo ""
    echo "To fix, run:"
    echo "  gcloud run services update ${SERVICE} --region ${REGION} \\"
    echo "    --set-env-vars COHA_MAPS_API_KEY=YOUR_VALUE,COHA_GOOGLE_MAP_ID=YOUR_VALUE,COHA_GCP_PROJECT_ID=YOUR_VALUE"
    echo ""
    echo "Set the admin password separately (single quotes prevent special-character issues):"
    echo "  gcloud run services update ${SERVICE} --region ${REGION} \\"
    echo "    --set-env-vars 'COHA_ADMIN_PASSWORD=YOUR_VALUE'"
    echo ""
    echo "See Deployment.md section 9 for details."
fi

echo ""
echo "Pruning old container images for ${SERVICE} (keeping 5 most recent)..."
KEEP=5
REGISTRY="us-west1-docker.pkg.dev/wildresearch-coha/cloud-run-source-deploy/${SERVICE}"
OLD_DIGESTS=$(gcloud artifacts docker images list "${REGISTRY}" \
    --sort-by="~CREATE_TIME" \
    --format="value(version)" 2>/dev/null \
    | tail -n +$((KEEP + 1)))

if [ -z "${OLD_DIGESTS}" ]; then
    echo "Nothing to prune."
else
    while IFS= read -r DIGEST; do
        echo "  Deleting ${DIGEST}"
        gcloud artifacts docker images delete "${REGISTRY}@${DIGEST}" --quiet 2>/dev/null || true
    done <<< "${OLD_DIGESTS}"
    echo "Pruning complete."
fi
