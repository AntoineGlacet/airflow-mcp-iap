# Setup Guide

Follow these steps to set up the Airflow MCP server with IAP authentication.

## Step-by-Step Setup

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
```

This will open a browser window for you to authenticate.

### 2. Find Your IAP Client ID

Run the helper script:

```bash
./find-iap-client-id.sh
```

This will guide you to find your IAP Client ID from the GCP Console.

Alternatively, manually get it from:
- https://console.cloud.google.com/security/iap
- Find your Airflow backend service
- Click the three dots → "Edit OAuth Client"
- Copy the Client ID (format: `XXXXX.apps.googleusercontent.com`)

### 3. Configure Environment Variables

Create a `.env` file with your configuration:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
AIRFLOW_HOST=https://your-airflow-domain.com
IAP_CLIENT_ID=XXXXX.apps.googleusercontent.com
```

Or export them in your shell:

```bash
export AIRFLOW_HOST="https://your-airflow-domain.com"
export IAP_CLIENT_ID="XXXXX.apps.googleusercontent.com"
```

### 4. Test the Connection

Run the test script:

```bash
./test-iap-connection.sh
```

This will:
- Generate an IAP token using your gcloud credentials
- Test the connection to your Airflow instance
- Verify that authentication works

If successful, you should see:
```
✅ Success! Airflow is accessible via IAP
```

### 5. Test the MCP Server

Run the server locally to make sure it works:

```bash
# Load environment variables
source .env

# Run the server
uv run airflow-mcp-iap
```

The server should start and wait for MCP requests on stdin.

Press `Ctrl+C` to stop it.

### 6. Configure OpenCode

#### Option A: Using Environment Variables (Recommended)

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export AIRFLOW_HOST="https://your-airflow-domain.com"
export IAP_CLIENT_ID="XXXXX.apps.googleusercontent.com"
```

Reload your shell:

```bash
source ~/.bashrc  # or ~/.zshrc
```

Add to OpenCode config (`~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "airflow": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--directory",
        "/home/antoine/airflow-mcp-iap",
        "airflow-mcp-iap"
      ],
      "environment": {
        "AIRFLOW_HOST": "{env:AIRFLOW_HOST}",
        "IAP_CLIENT_ID": "{env:IAP_CLIENT_ID}"
      },
      "enabled": true,
      "timeout": 10000
    }
  }
}
```

#### Option B: Hardcoded Values (Quick Test)

Add to OpenCode config (`~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "airflow": {
      "type": "local",
      "command": [
        "uv",
        "run",
        "--directory",
        "/home/antoine/airflow-mcp-iap",
        "airflow-mcp-iap"
      ],
      "environment": {
        "AIRFLOW_HOST": "https://your-airflow-domain.com",
        "IAP_CLIENT_ID": "XXXXX.apps.googleusercontent.com"
      },
      "enabled": true,
      "timeout": 10000
    }
  }
}
```

### 7. Start OpenCode

```bash
opencode
```

Test the integration by asking:

```
use airflow to list all DAGs
```

or

```
use airflow to get health status
```

## Troubleshooting

### "Failed to generate IAP token"

**Solution:**
```bash
gcloud auth login
```

### "403 Forbidden"

**Problem:** You don't have IAP access to the Airflow instance.

**Solution:** Ask your GCP admin to grant you the `IAP-secured Web App User` role for the Airflow backend service.

### "401 Unauthorized"

**Problem:** IAP Client ID might be incorrect or token expired.

**Solutions:**
1. Verify your IAP Client ID is correct
2. Re-run the test script to generate a fresh token
3. Check that IAP is properly configured for your Airflow instance

### "Connection refused" or timeout

**Problem:** Airflow URL might be incorrect or not accessible.

**Solutions:**
1. Verify `AIRFLOW_HOST` is correct
2. Check that you can access Airflow in your browser
3. Verify VPN is connected if required

### OpenCode doesn't see the Airflow tools

**Problem:** Environment variables not loaded or server not starting.

**Solutions:**
1. Check OpenCode logs: look for "Airflow IAP client initialized successfully"
2. Verify environment variables are set: `echo $AIRFLOW_HOST`
3. Test the server manually: `uv run airflow-mcp-iap`

### Token expiry during long sessions

**Don't worry!** The server automatically refreshes tokens every 50 minutes in the background. You should never see token expiry errors.

If you do encounter issues:
1. Check server logs for refresh errors
2. Restart OpenCode to get a fresh MCP server instance

## Next Steps

Once everything is working:

1. **Try different commands:**
   ```
   use airflow to list the last 10 DAG runs for my_dag
   use airflow to trigger the data_pipeline DAG
   use airflow to get logs for task extract in DAG my_dag
   ```

2. **Check the README.md** for a full list of available tools

3. **Explore the Airflow API** through OpenCode!

## Support

If you encounter issues:

1. Run the test script: `./test-iap-connection.sh`
2. Check server logs when running: `uv run airflow-mcp-iap`
3. Enable debug logging: `export AIRFLOW_MCP_DEBUG=true`
4. Create an issue on GitHub with logs and error messages
