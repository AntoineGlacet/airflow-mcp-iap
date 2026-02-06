# Quick Start Guide

Get your Airflow MCP server running in 5 minutes!

## Prerequisites Check

```bash
# Verify gcloud is authenticated
gcloud auth list

# Should show: antoine.glacet@kansai-airports.co.jp as ACTIVE
# If not, run: gcloud auth login
```

## Quick Setup (5 steps)

### 1️⃣ Get IAP Client ID

Open this URL in your browser:
```
https://console.cloud.google.com/security/iap?project=your-gcp-project-id
```

Find service: **gkegw1-26e6-airflow-airflow-api-server-8080-guzi9tddibi2**

Click ⋮ → "Edit OAuth Client" → Copy the Client ID

### 2️⃣ Get Airflow URL

What's your Airflow URL? It should look like:
- `https://airflow.your-gcp-project-id.example.com`
- Or whatever domain you access Airflow through

### 3️⃣ Create .env File

```bash
cd ~/airflow-mcp-iap
cat > .env << 'EOF'
AIRFLOW_HOST=https://YOUR_AIRFLOW_DOMAIN.com
IAP_CLIENT_ID=XXXXX.apps.googleusercontent.com
EOF
```

Replace with your actual values!

### 4️⃣ Test Connection

```bash
./test-iap-connection.sh
```

Expected output:
```
✅ Success! Airflow is accessible via IAP
```

If you get errors, see troubleshooting section below.

### 5️⃣ Configure OpenCode

**Option A: Quick test (hardcoded values)**

Edit `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "airflow": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/home/antoine/airflow-mcp-iap", "airflow-mcp-iap"],
      "environment": {
        "AIRFLOW_HOST": "https://YOUR_AIRFLOW_DOMAIN.com",
        "IAP_CLIENT_ID": "XXXXX.apps.googleusercontent.com"
      },
      "enabled": true
    }
  }
}
```

**Option B: Environment variables (recommended)**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export AIRFLOW_HOST="https://YOUR_AIRFLOW_DOMAIN.com"
export IAP_CLIENT_ID="XXXXX.apps.googleusercontent.com"
```

Then run: `source ~/.bashrc`

Edit `~/.config/opencode/opencode.json`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "airflow": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/home/antoine/airflow-mcp-iap", "airflow-mcp-iap"],
      "environment": {
        "AIRFLOW_HOST": "{env:AIRFLOW_HOST}",
        "IAP_CLIENT_ID": "{env:IAP_CLIENT_ID}"
      },
      "enabled": true
    }
  }
}
```

## Test It!

```bash
opencode
```

Try:
```
use airflow to get health status
```

Expected response: JSON with Airflow health information ✅

## Troubleshooting

### ❌ "403 Forbidden"

You need IAP access. Ask your admin to grant you:
- Role: `IAP-secured Web App User`
- Resource: `gkegw1-26e6-airflow-airflow-api-server-8080-guzi9tddibi2`

### ❌ "401 Unauthorized"

IAP Client ID is wrong. Double-check:
1. Go to https://console.cloud.google.com/security/iap?project=your-gcp-project-id
2. Verify the Client ID you copied
3. It should end with `.apps.googleusercontent.com`

### ❌ "Connection refused"

Airflow URL is wrong. Verify:
1. Can you access Airflow in your browser?
2. What's the exact URL you use?
3. Make sure to include `https://`

### ❌ "Failed to generate IAP token"

Re-authenticate:
```bash
gcloud auth login
```

## What's Next?

Once it's working, try these:

```bash
# List all DAGs
use airflow to list all DAGs

# Get recent runs
use airflow to show me the last 10 DAG runs for my_dag

# Trigger a DAG
use airflow to trigger the my_pipeline DAG

# Get task logs
use airflow to get logs for task extract in DAG my_pipeline, latest run

# Check variables
use airflow to list all variables

# View connections (without passwords)
use airflow to list all connections
```

## Full Documentation

- **README.md** - Complete documentation
- **SETUP.md** - Detailed setup guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## Need Help?

1. Check the test script output: `./test-iap-connection.sh`
2. Enable debug mode: `export AIRFLOW_MCP_DEBUG=true`
3. Check logs when running: `uv run airflow-mcp-iap`
4. Review SETUP.md for detailed troubleshooting

---

**🎉 Enjoy your Airflow MCP server!**
