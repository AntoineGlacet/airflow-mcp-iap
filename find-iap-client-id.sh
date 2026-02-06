#!/bin/bash
# Script to help find IAP Client ID for your Airflow deployment

set -euo pipefail

echo "=== Finding IAP Client ID for Airflow ==="
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

# Get current project
PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
if [ -z "$PROJECT" ]; then
    echo "No default project set. Please select your GCP project:"
    gcloud projects list --format="table(projectId,name)" --limit=20
    echo ""
    read -p "Enter project ID: " PROJECT
    gcloud config set project "$PROJECT"
fi

echo "📦 Using project: $PROJECT"
echo ""

# List IAP-secured backend services
echo "🔍 Searching for IAP-secured backend services..."
echo ""

# Try to list backend services
BACKEND_SERVICES=$(gcloud compute backend-services list --format="value(name)" 2>/dev/null || echo "")

if [ -z "$BACKEND_SERVICES" ]; then
    echo "⚠️  No backend services found or insufficient permissions"
    echo ""
    echo "Alternative methods to find your IAP Client ID:"
    echo ""
    echo "1. Via GCP Console:"
    echo "   - Go to: https://console.cloud.google.com/security/iap?project=$PROJECT"
    echo "   - Find your Airflow backend service"
    echo "   - Click the three dots → 'Edit OAuth Client'"
    echo "   - Copy the Client ID"
    echo ""
    echo "2. Ask your GCP admin for the IAP OAuth Client ID"
    echo ""
    exit 0
fi

echo "Found backend services:"
gcloud compute backend-services list --format="table(name,description,protocol)" 2>/dev/null
echo ""

# Try to get IAP settings
echo "Checking IAP settings..."
echo ""

for service in $BACKEND_SERVICES; do
    echo "🔍 Checking service: $service"
    
    # Try to get IAP web settings
    IAP_INFO=$(gcloud iap web get-iam-policy "$service" --format=json 2>/dev/null || echo "")
    
    if [ -n "$IAP_INFO" ]; then
        echo "   ✅ IAP is enabled on this service"
    fi
done

echo ""
echo "====================================================="
echo "To get your IAP Client ID:"
echo ""
echo "1. Visit the GCP Console:"
echo "   https://console.cloud.google.com/security/iap?project=$PROJECT"
echo ""
echo "2. Look for your Airflow backend service in the list"
echo ""
echo "3. Click the three dots (⋮) next to it and select 'Edit OAuth Client'"
echo ""
echo "4. Copy the Client ID (format: XXXXX.apps.googleusercontent.com)"
echo ""
echo "5. Add it to your .env file:"
echo "   IAP_CLIENT_ID=XXXXX.apps.googleusercontent.com"
echo "====================================================="
