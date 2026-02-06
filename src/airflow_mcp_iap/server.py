"""MCP server for Apache Airflow with Google IAP authentication."""

import os
import sys
import json
import logging
from typing import Any, Optional
import asyncio

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.stdio import stdio_server

from .iap_auth import IAPTokenProvider
from .airflow_http_client import AirflowHTTPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize server
app = Server("airflow-mcp-iap")

# Global client instance
airflow_client: Optional[AirflowHTTPClient] = None


def initialize_client():
    """Initialize the Airflow HTTP client from environment variables."""
    global airflow_client

    # Get configuration from environment
    airflow_host = os.getenv("AIRFLOW_HOST")
    iap_client_id = os.getenv("IAP_CLIENT_ID")

    if not airflow_host:
        raise ValueError("AIRFLOW_HOST environment variable is required")
    if not iap_client_id:
        raise ValueError("IAP_CLIENT_ID environment variable is required")

    logger.info(f"Initializing Airflow client for {airflow_host}")

    # Create token provider
    token_provider = IAPTokenProvider(iap_client_id)

    # Create Airflow HTTP client with dual authentication (IAP + Airflow JWT)
    airflow_client = AirflowHTTPClient(airflow_host, token_provider)

    logger.info("Airflow HTTP client initialized successfully with dual authentication")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Airflow tools."""
    return [
        Tool(
            name="airflow_list_dags",
            description="List all DAGs in Airflow",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of DAGs to return (default: 100)",
                        "default": 100,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="airflow_get_dag",
            description="Get details of a specific DAG",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID"}
                },
                "required": ["dag_id"],
            },
        ),
        Tool(
            name="airflow_pause_dag",
            description="Pause a DAG",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID to pause"}
                },
                "required": ["dag_id"],
            },
        ),
        Tool(
            name="airflow_unpause_dag",
            description="Unpause a DAG",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID to unpause"}
                },
                "required": ["dag_id"],
            },
        ),
        Tool(
            name="airflow_list_dag_runs",
            description="List DAG runs for a specific DAG",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID"},
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of DAG runs to return (default: 25)",
                        "default": 25,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
                "required": ["dag_id"],
            },
        ),
        Tool(
            name="airflow_trigger_dag",
            description="Trigger a new DAG run",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {
                        "type": "string",
                        "description": "The DAG ID to trigger",
                    },
                    "conf": {
                        "type": "object",
                        "description": "Optional configuration JSON to pass to the DAG",
                        "default": {},
                    },
                    "logical_date": {
                        "type": "string",
                        "description": "Optional logical date for the DAG run (ISO 8601 format)",
                    },
                },
                "required": ["dag_id"],
            },
        ),
        Tool(
            name="airflow_get_dag_run",
            description="Get details of a specific DAG run",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID"},
                    "dag_run_id": {"type": "string", "description": "The DAG run ID"},
                },
                "required": ["dag_id", "dag_run_id"],
            },
        ),
        Tool(
            name="airflow_get_task_instance",
            description="Get details of a specific task instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID"},
                    "dag_run_id": {"type": "string", "description": "The DAG run ID"},
                    "task_id": {"type": "string", "description": "The task ID"},
                },
                "required": ["dag_id", "dag_run_id", "task_id"],
            },
        ),
        Tool(
            name="airflow_get_task_logs",
            description="Get logs for a specific task instance",
            inputSchema={
                "type": "object",
                "properties": {
                    "dag_id": {"type": "string", "description": "The DAG ID"},
                    "dag_run_id": {"type": "string", "description": "The DAG run ID"},
                    "task_id": {"type": "string", "description": "The task ID"},
                    "task_try_number": {
                        "type": "number",
                        "description": "The task try number (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["dag_id", "dag_run_id", "task_id"],
            },
        ),
        Tool(
            name="airflow_list_variables",
            description="List all Airflow variables",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of variables to return (default: 100)",
                        "default": 100,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="airflow_get_variable",
            description="Get a specific Airflow variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "variable_key": {
                        "type": "string",
                        "description": "The variable key",
                    }
                },
                "required": ["variable_key"],
            },
        ),
        Tool(
            name="airflow_set_variable",
            description="Create or update an Airflow variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "variable_key": {
                        "type": "string",
                        "description": "The variable key",
                    },
                    "value": {"type": "string", "description": "The variable value"},
                },
                "required": ["variable_key", "value"],
            },
        ),
        Tool(
            name="airflow_delete_variable",
            description="Delete an Airflow variable",
            inputSchema={
                "type": "object",
                "properties": {
                    "variable_key": {
                        "type": "string",
                        "description": "The variable key to delete",
                    }
                },
                "required": ["variable_key"],
            },
        ),
        Tool(
            name="airflow_list_connections",
            description="List all Airflow connections",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of connections to return (default: 100)",
                        "default": 100,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="airflow_get_connection",
            description="Get a specific Airflow connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connection_id": {
                        "type": "string",
                        "description": "The connection ID",
                    }
                },
                "required": ["connection_id"],
            },
        ),
        Tool(
            name="airflow_get_health",
            description="Get Airflow health status",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="airflow_get_version",
            description="Get Airflow version information",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="airflow_list_pools",
            description="List all Airflow pools",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of pools to return (default: 100)",
                        "default": 100,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="airflow_get_pool",
            description="Get a specific Airflow pool",
            inputSchema={
                "type": "object",
                "properties": {
                    "pool_name": {"type": "string", "description": "The pool name"}
                },
                "required": ["pool_name"],
            },
        ),
        Tool(
            name="airflow_list_import_errors",
            description="List DAG import errors - shows DAGs that failed to parse or import with their error messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of import errors to return (default: 100)",
                        "default": 100,
                    },
                    "offset": {
                        "type": "number",
                        "description": "Offset for pagination (default: 0)",
                        "default": 0,
                    },
                },
            },
        ),
        Tool(
            name="airflow_get_import_error",
            description="Get detailed information about a specific DAG import error by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "import_error_id": {
                        "type": "number",
                        "description": "The import error ID",
                    }
                },
                "required": ["import_error_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        # Map tool names to client methods
        if name == "airflow_list_dags":
            result = airflow_client.list_dags(
                limit=arguments.get("limit", 100), offset=arguments.get("offset", 0)
            )
        elif name == "airflow_get_dag":
            result = airflow_client.get_dag(arguments["dag_id"])
        elif name == "airflow_pause_dag":
            result = airflow_client.pause_dag(arguments["dag_id"])
        elif name == "airflow_unpause_dag":
            result = airflow_client.unpause_dag(arguments["dag_id"])
        elif name == "airflow_list_dag_runs":
            result = airflow_client.list_dag_runs(
                dag_id=arguments["dag_id"],
                limit=arguments.get("limit", 25),
                offset=arguments.get("offset", 0),
            )
        elif name == "airflow_trigger_dag":
            result = airflow_client.trigger_dag(
                dag_id=arguments["dag_id"],
                conf=arguments.get("conf"),
                logical_date=arguments.get("logical_date"),
            )
        elif name == "airflow_get_dag_run":
            result = airflow_client.get_dag_run(
                dag_id=arguments["dag_id"], dag_run_id=arguments["dag_run_id"]
            )
        elif name == "airflow_get_task_instance":
            result = airflow_client.get_task_instance(
                dag_id=arguments["dag_id"],
                dag_run_id=arguments["dag_run_id"],
                task_id=arguments["task_id"],
            )
        elif name == "airflow_get_task_logs":
            result = airflow_client.get_task_logs(
                dag_id=arguments["dag_id"],
                dag_run_id=arguments["dag_run_id"],
                task_id=arguments["task_id"],
                task_try_number=arguments.get("task_try_number", 1),
            )
        elif name == "airflow_list_variables":
            result = airflow_client.list_variables(
                limit=arguments.get("limit", 100), offset=arguments.get("offset", 0)
            )
        elif name == "airflow_get_variable":
            result = airflow_client.get_variable(arguments["variable_key"])
        elif name == "airflow_set_variable":
            result = airflow_client.set_variable(
                variable_key=arguments["variable_key"], value=arguments["value"]
            )
        elif name == "airflow_delete_variable":
            result = airflow_client.delete_variable(arguments["variable_key"])
        elif name == "airflow_list_connections":
            result = airflow_client.list_connections(
                limit=arguments.get("limit", 100), offset=arguments.get("offset", 0)
            )
        elif name == "airflow_get_connection":
            result = airflow_client.get_connection(arguments["connection_id"])
        elif name == "airflow_get_health":
            result = airflow_client.get_health()
        elif name == "airflow_get_version":
            result = airflow_client.get_version()
        elif name == "airflow_list_pools":
            result = airflow_client.list_pools(
                limit=arguments.get("limit", 100), offset=arguments.get("offset", 0)
            )
        elif name == "airflow_get_pool":
            result = airflow_client.get_pool(arguments["pool_name"])
        elif name == "airflow_list_import_errors":
            result = airflow_client.list_import_errors(
                limit=arguments.get("limit", 100), offset=arguments.get("offset", 0)
            )
        elif name == "airflow_get_import_error":
            result = airflow_client.get_import_error(arguments["import_error_id"])
        else:
            raise ValueError(f"Unknown tool: {name}")

        # Format result as JSON
        result_json = json.dumps(result, indent=2, default=str)

        return [TextContent(type="text", text=result_json)]

    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        error_msg = f"Error: {str(e)}"
        return [TextContent(type="text", text=error_msg)]


async def run_server():
    """Main entry point for the MCP server."""
    try:
        # Initialize the Airflow client
        initialize_client()

        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream, write_stream, app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Entry point for the command-line script."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
