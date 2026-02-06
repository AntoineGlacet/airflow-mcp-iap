#!/bin/bash
# Script to test IAP authentication and Airflow connection

set -euo pipefail

# Load .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "=== Testing IAP Authentication to Airflow ==="
echo ""

# Check required variables
if [ -z "${IAP_CLIENT_ID:-}" ]; then
    echo "❌ IAP_CLIENT_ID not set"
    echo "Please set it in .env or export it:"
    echo "  export IAP_CLIENT_ID=XXXXX.apps.googleusercontent.com"
    exit 1
fi

if [ -z "${AIRFLOW_HOST:-}" ]; then
    echo "❌ AIRFLOW_HOST not set"
    echo "Please set it in .env or export it:"
    echo "  export AIRFLOW_HOST=https://your-airflow-domain.com"
    exit 1
fi

echo "📝 Configuration:"
echo "   AIRFLOW_HOST: $AIRFLOW_HOST"
echo "   IAP_CLIENT_ID: $IAP_CLIENT_ID"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    echo "❌ Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "✅ Authenticated as: $ACCOUNT"
echo ""

# Generate IAP token
echo "🔑 Generating IAP token..."
if ! TOKEN=$(gcloud auth print-identity-token --audiences="$IAP_CLIENT_ID" 2>&1); then
    echo "❌ Failed to generate IAP token:"
    echo "$TOKEN"
    exit 1
fi
echo "✅ Token generated successfully"
echo ""

# Test Airflow health endpoint
echo "🏥 Testing Airflow health endpoint..."
HEALTH_URL="${AIRFLOW_HOST}/api/v1/health"
echo "   URL: $HEALTH_URL"
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -H "Authorization: Bearer ${TOKEN}" "$HEALTH_URL" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success! Airflow is accessible via IAP"
    echo ""
    echo "Health status:"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    echo ""
    echo "====================================================="
    echo "🎉 IAP authentication is working correctly!"
    echo ""
    echo "Next steps:"
    echo "1. Update your OpenCode config with these settings"
    echo "2. Run: uv run airflow-mcp-iap"
    echo "====================================================="
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ HTTP 403 Forbidden"
    echo ""
    echo "This means:"
    echo "  - Authentication worked, but you don't have IAP access"
    echo "  - Ask your GCP admin to grant you 'IAP-secured Web App User' role"
    echo ""
    echo "Response:"
    echo "$BODY"
elif [ "$HTTP_CODE" = "401" ]; then
    echo "❌ HTTP 401 Unauthorized"
    echo ""
    echo "This means:"
    echo "  - IAP Client ID might be incorrect"
    echo "  - Token might be expired (try re-running this script)"
    echo ""
    echo "Response:"
    echo "$BODY"
else
    echo "❌ HTTP $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$BODY"
fi

echo ""
echo "Debug info:"
echo "  Token (first 50 chars): ${TOKEN:0:50}..."
echo "  Token length: ${#TOKEN}"
