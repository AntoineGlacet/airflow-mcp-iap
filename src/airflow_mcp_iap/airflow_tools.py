"""Airflow MCP tools with IAP authentication."""

import json
from typing import Any, Optional
import httpx
import logging

from airflow_client.client.api import (
    dag_api,
    dag_run_api,
    task_instance_api,
    variable_api,
    connection_api,
    pool_api,
    monitor_api,
    version_api,
    config_api,
)
from airflow_client.client import ApiClient, Configuration

from .iap_auth import IAPTokenProvider

logger = logging.getLogger(__name__)


class AirflowIAPClient:
    """Airflow API client with IAP authentication."""

    def __init__(
        self,
        airflow_host: str,
        token_provider: IAPTokenProvider,
        api_version: str = "v2",
        airflow_username: Optional[str] = None,
        airflow_password: Optional[str] = None,
    ):
        """
        Initialize Airflow IAP client.

        Args:
            airflow_host: Airflow base URL (e.g., https://airflow.example.com)
            token_provider: IAP token provider instance
            api_version: Airflow API version (default: v2 for Airflow 3.x)
            airflow_username: Airflow username for API authentication (optional, defaults to anonymous)
            airflow_password: Airflow password for API authentication (optional)
        """
        self.airflow_host = airflow_host.rstrip("/")
        self.token_provider = token_provider
        self.api_version = api_version
        self.airflow_username = airflow_username
        self.airflow_password = airflow_password
        self._airflow_jwt_token: Optional[str] = None

        # Configure Airflow client
        self.configuration = Configuration(
            host=f"{self.airflow_host}/api/{self.api_version}"
        )

        # We'll set the token dynamically for each request
        self.api_client = ApiClient(self.configuration)

        # Obtain Airflow JWT token
        self._refresh_airflow_jwt()

        # Initialize API instances
        self.dag_api = dag_api.DAGApi(self.api_client)
        self.dag_run_api = dag_run_api.DagRunApi(self.api_client)
        self.task_instance_api = task_instance_api.TaskInstanceApi(self.api_client)
        self.variable_api = variable_api.VariableApi(self.api_client)
        self.connection_api = connection_api.ConnectionApi(self.api_client)
        self.pool_api = pool_api.PoolApi(self.api_client)
        self.monitor_api = monitor_api.MonitorApi(self.api_client)
        self.version_api = version_api.VersionApi(self.api_client)
        self.config_api = config_api.ConfigApi(self.api_client)

    def _refresh_airflow_jwt(self):
        """Obtain Airflow JWT token for API authentication."""
        try:
            # Get IAP token first
            iap_token = self.token_provider.get_token()

            # Request Airflow JWT token
            auth_url = f"{self.airflow_host}/auth/token"

            # Airflow requires username and password fields (can be empty for anonymous)
            auth_payload = {
                "username": self.airflow_username or "",
                "password": self.airflow_password or "",
            }

            # Make request with IAP token
            response = httpx.post(
                auth_url,
                json=auth_payload,
                headers={"Authorization": f"Bearer {iap_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

            # Extract JWT token
            token_data = response.json()
            self._airflow_jwt_token = token_data.get("access_token")

            if not self._airflow_jwt_token:
                raise RuntimeError("No access_token in response")

            logger.info("Successfully obtained Airflow JWT token")

        except Exception as e:
            logger.error(f"Failed to obtain Airflow JWT token: {e}")
            raise RuntimeError(f"Airflow authentication failed: {e}")

    def _set_auth_header(self):
        """Set both IAP and Airflow authentication headers."""
        # Get IAP token
        iap_token = self.token_provider.get_token()

        # Set Airflow JWT token (for API authorization)
        if not self._airflow_jwt_token:
            self._refresh_airflow_jwt()

        # Set both tokens in headers
        self.api_client.set_default_header("Proxy-Authorization", f"Bearer {iap_token}")
        self.api_client.set_default_header(
            "Authorization", f"Bearer {self._airflow_jwt_token}"
        )

    def _api_call(self, func, *args, **kwargs):
        """
        Wrapper for API calls that ensures authentication header is set.

        Args:
            func: API function to call
            *args, **kwargs: Arguments to pass to the function

        Returns:
            API call result
        """
        self._set_auth_header()
        return func(*args, **kwargs)

    # DAG operations
    def list_dags(
        self, limit: int = 100, offset: int = 0, order_by: Optional[str] = None
    ) -> dict:
        """List all DAGs."""
        result = self._api_call(
            self.dag_api.get_dags, limit=limit, offset=offset, order_by=order_by
        )
        return result.to_dict()

    def get_dag(self, dag_id: str) -> dict:
        """Get details of a specific DAG."""
        result = self._api_call(self.dag_api.get_dag, dag_id)
        return result.to_dict()

    def pause_dag(self, dag_id: str) -> dict:
        """Pause a DAG."""
        from airflow_client.client.model.dag import DAG

        dag_update = DAG(is_paused=True)
        result = self._api_call(self.dag_api.patch_dag, dag_id, dag_update)
        return result.to_dict()

    def unpause_dag(self, dag_id: str) -> dict:
        """Unpause a DAG."""
        from airflow_client.client.model.dag import DAG

        dag_update = DAG(is_paused=False)
        result = self._api_call(self.dag_api.patch_dag, dag_id, dag_update)
        return result.to_dict()

    # DAG Run operations
    def list_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0,
        order_by: Optional[str] = None,
    ) -> dict:
        """List DAG runs for a specific DAG."""
        result = self._api_call(
            self.dag_run_api.get_dag_runs,
            dag_id,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )
        return result.to_dict()

    def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[dict] = None,
        logical_date: Optional[str] = None,
    ) -> dict:
        """Trigger a new DAG run."""
        # Create the request body
        body = {"conf": conf or {}}
        if logical_date:
            body["logical_date"] = logical_date

        result = self._api_call(self.dag_run_api.trigger_dag_run, dag_id, body)
        return result.to_dict()

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        """Get details of a specific DAG run."""
        result = self._api_call(self.dag_run_api.get_dag_run, dag_id, dag_run_id)
        return result.to_dict()

    # Task Instance operations
    def get_task_instance(self, dag_id: str, dag_run_id: str, task_id: str) -> dict:
        """Get details of a specific task instance."""
        result = self._api_call(
            self.task_instance_api.get_task_instance, dag_id, dag_run_id, task_id
        )
        return result.to_dict()

    def get_task_logs(
        self, dag_id: str, dag_run_id: str, task_id: str, task_try_number: int = 1
    ) -> dict:
        """Get logs for a specific task instance."""
        result = self._api_call(
            self.task_instance_api.get_log, dag_id, dag_run_id, task_id, task_try_number
        )
        return {"content": result}

    # Variable operations
    def list_variables(self, limit: int = 100, offset: int = 0) -> dict:
        """List all Airflow variables."""
        result = self._api_call(
            self.variable_api.get_variables, limit=limit, offset=offset
        )
        return result.to_dict()

    def get_variable(self, variable_key: str) -> dict:
        """Get a specific Airflow variable."""
        result = self._api_call(self.variable_api.get_variable, variable_key)
        return result.to_dict()

    def set_variable(self, variable_key: str, value: str) -> dict:
        """Create or update an Airflow variable."""
        from airflow_client.client.model.variable import Variable

        variable = Variable(key=variable_key, value=value)
        result = self._api_call(self.variable_api.post_variable, variable)
        return result.to_dict()

    def delete_variable(self, variable_key: str) -> dict:
        """Delete an Airflow variable."""
        self._api_call(self.variable_api.delete_variable, variable_key)
        return {"status": "deleted", "variable_key": variable_key}

    # Connection operations
    def list_connections(self, limit: int = 100, offset: int = 0) -> dict:
        """List all Airflow connections."""
        result = self._api_call(
            self.connection_api.get_connections, limit=limit, offset=offset
        )
        return result.to_dict()

    def get_connection(self, connection_id: str) -> dict:
        """Get a specific Airflow connection."""
        result = self._api_call(self.connection_api.get_connection, connection_id)
        return result.to_dict()

    # Monitoring operations
    def get_health(self) -> dict:
        """Get Airflow health status."""
        result = self._api_call(self.monitor_api.get_health)
        return result.to_dict()

    def get_version(self) -> dict:
        """Get Airflow version information."""
        result = self._api_call(self.version_api.get_version)
        return result.to_dict()

    # Pool operations
    def list_pools(self, limit: int = 100, offset: int = 0) -> dict:
        """List all Airflow pools."""
        result = self._api_call(self.pool_api.get_pools, limit=limit, offset=offset)
        return result.to_dict()

    def get_pool(self, pool_name: str) -> dict:
        """Get a specific Airflow pool."""
        result = self._api_call(self.pool_api.get_pool, pool_name)
        return result.to_dict()
