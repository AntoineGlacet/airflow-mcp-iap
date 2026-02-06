# Airflow MCP Server with Google IAP Authentication

A Model Context Protocol (MCP) server for Apache Airflow 3, designed for teams using Airflow deployed behind Google Identity-Aware Proxy (IAP).

## Features

- 🔐 **OAuth2 Desktop Authentication** - One-time browser authentication with secure token caching
- 🔄 **Automatic Token Refresh** - Background thread refreshes tokens every 50 minutes
- 👥 **Team-Friendly** - Each team member authenticates once, credentials cached locally
- 🛠️ **20 Airflow Tools** - Comprehensive API coverage for DAGs, runs, tasks, variables, connections, import errors, and more
- 🚀 **OpenCode Integration** - Works seamlessly as a local MCP server

## Quick Start for Team Members

### Prerequisites

1. **Python 3.10+** and **uv** package manager
2. **Google Cloud SDK** (gcloud)
3. **Access to Airflow** via IAP (ask your admin for permissions)

### Installation

**Option 1: Using uvx (Recommended)**

No installation needed! Just configure OpenCode to run the package directly from GitHub using `uvx`.

Set environment variables (add to your `~/.bashrc` or `~/.zshrc`):

**Note:** Ask your admin for these values, or find them in GCP Console:
- `AIRFLOW_HOST`: Your Airflow instance URL
- `IAP_CLIENT_ID`: Go to [GCP Console > Security > IAP](https://console.cloud.google.com/security/iap) and find the OAuth client ID for your Airflow service
- `IAP_DESKTOP_CLIENT_ID` & `IAP_DESKTOP_CLIENT_SECRET`: Go to [GCP Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials) and find the Desktop OAuth client credentials

```bash
export AIRFLOW_HOST="<your-airflow-host>"
export IAP_CLIENT_ID="<your-iap-client-id>.apps.googleusercontent.com"
export IAP_DESKTOP_CLIENT_ID="<your-desktop-client-id>"
export IAP_DESKTOP_CLIENT_SECRET="<your-desktop-client-secret>"
```

Then reload: `source ~/.bashrc`

**Option 2: Local Development**

1. Clone the repository:
   ```bash
   git clone https://github.com/AntoineGlacet/airflow-mcp-iap.git
   cd airflow-mcp-iap
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set environment variables as shown in Option 1

### First-Time Authentication

The first time you use the MCP server, it will open a browser for Google authentication:

```bash
# If using uvx
uvx --from git+https://github.com/AntoineGlacet/airflow-mcp-iap airflow-mcp-iap

# If using local installation
uv run airflow-mcp-iap
```

1. Your browser will open automatically
2. Sign in with your `@kansai-airports.co.jp` Google account
3. Grant the requested permissions
4. Return to the terminal

Your credentials will be cached at `~/.config/airflow-mcp-iap/oauth_token.json` and automatically refreshed.

### OpenCode Setup

**Option 1: Using uvx (Recommended)**

Add to your `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "airflow": {
      "type": "local",
      "command": [
        "uvx",
        "--from",
        "git+https://github.com/AntoineGlacet/airflow-mcp-iap",
        "airflow-mcp-iap"
      ],
      "environment": {
        "AIRFLOW_HOST": "{env:AIRFLOW_HOST}",
        "IAP_CLIENT_ID": "{env:IAP_CLIENT_ID}",
        "IAP_DESKTOP_CLIENT_ID": "{env:IAP_DESKTOP_CLIENT_ID}",
        "IAP_DESKTOP_CLIENT_SECRET": "{env:IAP_DESKTOP_CLIENT_SECRET}"
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

**Option 2: Local Installation**

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
        "/path/to/airflow-mcp-iap",
        "airflow-mcp-iap"
      ],
      "environment": {
        "AIRFLOW_HOST": "{env:AIRFLOW_HOST}",
        "IAP_CLIENT_ID": "{env:IAP_CLIENT_ID}",
        "IAP_DESKTOP_CLIENT_ID": "{env:IAP_DESKTOP_CLIENT_ID}",
        "IAP_DESKTOP_CLIENT_SECRET": "{env:IAP_DESKTOP_CLIENT_SECRET}"
      },
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

Replace `/path/to/airflow-mcp-iap` with your actual installation path.

## Usage in OpenCode

Once configured, you can interact with Airflow through OpenCode:

```
# Get Airflow health status
use airflow to get health status

# List all DAGs
use airflow to list all DAGs

# View recent DAG runs
use airflow to show me the last 10 runs of my_data_pipeline

# Trigger a DAG
use airflow to trigger the etl_pipeline DAG

# Get task logs
use airflow to get logs for task extract_data in DAG etl_pipeline, latest run

# Manage variables
use airflow to list all variables
use airflow to set variable my_config to "value"

# View connections
use airflow to list all connections

# Check for DAG import errors
use airflow to list import errors
use airflow to show me import error details for error ID 1
```

## Available Tools

### DAG Management
- `airflow_list_dags` - List all DAGs with pagination
- `airflow_get_dag` - Get details of a specific DAG
- `airflow_pause_dag` - Pause a DAG
- `airflow_unpause_dag` - Unpause a DAG

### DAG Runs
- `airflow_list_dag_runs` - List DAG runs for a specific DAG
- `airflow_trigger_dag` - Trigger a new DAG run with optional config
- `airflow_get_dag_run` - Get details of a specific DAG run

### Tasks
- `airflow_get_task_instance` - Get task instance details
- `airflow_get_task_logs` - Get logs for a task instance

### Variables
- `airflow_list_variables` - List all Airflow variables
- `airflow_get_variable` - Get a specific variable
- `airflow_set_variable` - Create or update a variable
- `airflow_delete_variable` - Delete a variable

### Connections
- `airflow_list_connections` - List all connections
- `airflow_get_connection` - Get connection details

### Pools
- `airflow_list_pools` - List all pools
- `airflow_get_pool` - Get pool details

### Monitoring
- `airflow_get_health` - Get Airflow health status
- `airflow_get_version` - Get Airflow version information

### Import Errors
- `airflow_list_import_errors` - List DAG files that failed to parse or import
- `airflow_get_import_error` - Get detailed error information for a specific import error

## Team Deployment

### Admin Setup

1. **Grant IAP Access** to team members:
   - Go to [GCP IAP Console](https://console.cloud.google.com/security/iap?project=your-gcp-project-id)
   - Select the Airflow backend service
   - Add team members with `IAP-secured Web App User` role

2. **Get IAP Client ID**:
   - Go to [GCP Console > Security > IAP](https://console.cloud.google.com/security/iap)
   - Find the OAuth client ID for your Airflow backend service
   - This is the `IAP_CLIENT_ID` value

3. **Create OAuth Desktop Client** (one-time setup):
   - Go to [GCP Console > APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
   - Click "CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: **Desktop app**
   - Name: "Airflow MCP Desktop Client"
   - Copy the Client ID and Client Secret
   - These are the `IAP_DESKTOP_CLIENT_ID` and `IAP_DESKTOP_CLIENT_SECRET` values
   - **Share these credentials with team members securely** (e.g., via password manager)

4. **Document Environment Variables**:
   - Provide all values to team members:
     - `AIRFLOW_HOST`: Your Airflow instance URL
     - `IAP_CLIENT_ID`: From step 2
     - `IAP_DESKTOP_CLIENT_ID`: From step 3
     - `IAP_DESKTOP_CLIENT_SECRET`: From step 3
   - Team members add these to their shell profiles

### For Team Members

**Quick Start (uvx method - no installation needed):**

1. Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Get credentials from your admin** or find them in GCP Console:
   - `AIRFLOW_HOST`, `IAP_CLIENT_ID`, `IAP_DESKTOP_CLIENT_ID`, `IAP_DESKTOP_CLIENT_SECRET`
   - See "Installation" section above for where to find these in GCP Console
3. Set environment variables in your `~/.bashrc` or `~/.zshrc`
4. Configure OpenCode with uvx command (see OpenCode Setup above)
5. Start using! Authentication will happen automatically on first use

**Alternative (local development):**

1. Clone and install the package
2. Set environment variables
3. Run once to authenticate: `uv run airflow-mcp-iap`
4. Configure OpenCode with local path
5. Start using!

## Troubleshooting

### "Failed to authenticate"

**Solution:** Make sure you have IAP access. Ask your admin to grant you the `IAP-secured Web App User` role.

### "Browser didn't open"

**Solution:** Manually copy the URL shown in the terminal and paste it into your browser.

### "Token expired" or "Invalid credentials"

**Solution:** Clear the cache and re-authenticate:
```bash
rm ~/.config/airflow-mcp-iap/oauth_token.json
uv run airflow-mcp-iap
```

### "Connection refused"

**Solution:** 
1. Verify `AIRFLOW_HOST` is correct
2. Check you're connected to VPN if required
3. Confirm Airflow is accessible in your browser

### OpenCode doesn't start the server

**Solution:**
1. Check environment variables are set: `echo $AIRFLOW_HOST`
2. Test manually: `uv run airflow-mcp-iap`
3. Check OpenCode logs for errors

## Security

- ✅ OAuth2 authentication (no passwords stored)
- ✅ Tokens cached locally with 600 permissions
- ✅ Auto-refresh prevents token expiry
- ✅ Each team member uses their own credentials
- ✅ IAP validates all requests

## Architecture

```
OpenCode (Local)
    ↓
MCP Server (Python - this package)
    ↓
OAuth2 Desktop Flow (one-time browser auth)
    ↓
Cached Credentials (~/.config/airflow-mcp-iap/oauth_token.json)
    ↓ (auto-refresh every 50 min)
Google IAP (validates user permissions)
    ↓
Airflow REST API (GKE)
```

## Development

### Running Tests

```bash
uv run pytest
```

### Clearing Token Cache

```bash
rm ~/.config/airflow-mcp-iap/oauth_token.json
```

### Debug Mode

Enable debug logging:
```bash
export AIRFLOW_MCP_DEBUG=true
uv run airflow-mcp-iap
```

## Project Structure

```
airflow-mcp-iap/
├── src/airflow_mcp_iap/
│   ├── __init__.py           # Package initialization
│   ├── iap_auth.py           # OAuth2 authentication & token management
│   ├── airflow_tools.py      # Airflow API client wrapper
│   └── server.py             # MCP server implementation
├── pyproject.toml            # Project dependencies
├── README.md                 # This file
└── .gitignore               # Git ignore rules
```

## Contributing

This is an internal tool for KAP data team. For improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Credits

- Inspired by [mcp-server-apache-airflow](https://github.com/yangkyeongmo/mcp-server-apache-airflow) by yangkyeongmo
- Built for KAP Data Team
- Powered by [OpenCode](https://opencode.ai)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run with debug mode enabled
3. Contact the data platform team
4. Open an issue on GitHub

---

**Built with ❤️ for KAP Data Team**
