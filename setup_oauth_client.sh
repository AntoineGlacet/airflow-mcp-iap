#!/bin/bash
#
# Setup script to create a Desktop OAuth client for IAP authentication
#
# This script guides you through creating a Desktop OAuth 2.0 client
# in your GCP project and configuring the environment variables.
#

set -e

# TODO: Set these values for your environment
PROJECT_ID="your-gcp-project-id"
IAP_CLIENT_ID="your-iap-client-id.apps.googleusercontent.com"

echo "======================================================================"
echo "Airflow MCP IAP - Desktop OAuth Client Setup"
echo "======================================================================"
echo ""
echo "To use this MCP server with IAP, you need a Desktop OAuth 2.0 client"
echo "from the same GCP project as your IAP configuration."
echo ""
echo "Project: $PROJECT_ID"
echo "IAP Client ID: $IAP_CLIENT_ID"
echo ""
echo "======================================================================"
echo ""

# Check if gcloud is authenticated
echo "Checking gcloud authentication..."
CURRENT_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "")
if [ -z "$CURRENT_ACCOUNT" ]; then
    echo "❌ Not authenticated with gcloud"
    echo "Run: gcloud auth login"
    exit 1
fi
echo "✅ Authenticated as: $CURRENT_ACCOUNT"
echo ""

# Check if already configured
if [ -n "$IAP_DESKTOP_CLIENT_ID" ] && [ -n "$IAP_DESKTOP_CLIENT_SECRET" ]; then
    echo "✅ Environment variables already set:"
    echo "   IAP_DESKTOP_CLIENT_ID=$IAP_DESKTOP_CLIENT_ID"
    echo "   IAP_DESKTOP_CLIENT_SECRET=[REDACTED]"
    echo ""
    read -p "Do you want to reconfigure? (y/N): " reconfigure
    if [ "$reconfigure" != "y" ] && [ "$reconfigure" != "Y" ]; then
        echo "Keeping existing configuration."
        exit 0
    fi
fi

echo "======================================================================"
echo "MANUAL STEP: Create Desktop OAuth Client"
echo "======================================================================"
echo ""
echo "1. Open this URL in your browser:"
echo "   https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
echo ""
echo "2. Click 'CREATE CREDENTIALS' → 'OAuth client ID'"
echo ""
echo "3. Configure the client:"
echo "   - Application type: Desktop app"
echo "   - Name: Airflow MCP Desktop Client"
echo ""
echo "4. Click 'CREATE'"
echo ""
echo "5. In the popup, copy the Client ID and Client Secret"
echo ""
echo "======================================================================"
echo ""
read -p "Press ENTER when you have created the OAuth client..."
echo ""

# Prompt for credentials
echo "Enter the OAuth client credentials:"
echo ""
read -p "Client ID: " DESKTOP_CLIENT_ID
read -s -p "Client Secret: " DESKTOP_CLIENT_SECRET
echo ""
echo ""

# Validate inputs
if [ -z "$DESKTOP_CLIENT_ID" ] || [ -z "$DESKTOP_CLIENT_SECRET" ]; then
    echo "❌ Both Client ID and Client Secret are required"
    exit 1
fi

# Add to secrets.env
SECRETS_FILE="$HOME/dotfiles/shell/secrets.env"
echo "Adding credentials to $SECRETS_FILE..."

# Check if file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Secrets file not found: $SECRETS_FILE"
    exit 1
fi

# Backup secrets file
cp "$SECRETS_FILE" "$SECRETS_FILE.backup.$(date +%Y%m%d_%H%M%S)"

# Remove existing entries if any
sed -i '/^export IAP_DESKTOP_CLIENT_ID=/d' "$SECRETS_FILE"
sed -i '/^export IAP_DESKTOP_CLIENT_SECRET=/d' "$SECRETS_FILE"

# Add new entries
echo "" >> "$SECRETS_FILE"
echo "# Airflow MCP IAP - Desktop OAuth Client" >> "$SECRETS_FILE"
echo "export IAP_DESKTOP_CLIENT_ID=\"$DESKTOP_CLIENT_ID\"" >> "$SECRETS_FILE"
echo "export IAP_DESKTOP_CLIENT_SECRET=\"$DESKTOP_CLIENT_SECRET\"" >> "$SECRETS_FILE"

echo "✅ Credentials added to secrets.env"
echo ""

# Encrypt if using git-crypt
if command -v git-crypt &> /dev/null; then
    if git -C "$HOME/dotfiles" config --get filter.git-crypt.smudge &> /dev/null; then
        echo "Encrypting secrets.env with git-crypt..."
        cd "$HOME/dotfiles"
        git add shell/secrets.env
        echo "✅ Secrets encrypted"
    fi
fi

echo "======================================================================"
echo "✅ Setup Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "1. Source the secrets file:"
echo "   source ~/dotfiles/shell/secrets.env"
echo ""
echo "2. Clear the OAuth token cache to force re-authentication:"
echo "   rm ~/.config/airflow-mcp-iap/oauth_token.json"
echo ""
echo "3. Test the MCP server:"
echo "   cd ~/airflow-mcp-iap"
echo "   source .venv/bin/activate"
echo "   python -m src.airflow_mcp_iap.server"
echo ""
echo "======================================================================"
