"""Simple HTTP client for Airflow API with IAP authentication."""

import httpx
import logging
from typing import Any, Optional

from .iap_auth import IAPTokenProvider

logger = logging.getLogger(__name__)


class AirflowHTTPClient:
    """Direct HTTP client for Airflow API with IAP + JWT authentication."""

    def __init__(
        self,
        airflow_host: str,
        token_provider: IAPTokenProvider,
        airflow_username: Optional[str] = None,
        airflow_password: Optional[str] = None,
    ):
        """
        Initialize Airflow HTTP client.

        Args:
            airflow_host: Airflow base URL
            token_provider: IAP token provider
            airflow_username: Airflow username (optional, defaults to anonymous)
            airflow_password: Airflow password (optional)
        """
        self.airflow_host = airflow_host.rstrip("/")
        self.token_provider = token_provider
        self.airflow_username = airflow_username or ""
        self.airflow_password = airflow_password or ""
        self._airflow_jwt_token: Optional[str] = None

        # Obtain Airflow JWT token
        self._refresh_airflow_jwt()

    def _refresh_airflow_jwt(self):
        """Obtain Airflow JWT token."""
        iap_token = self.token_provider.get_token()

        response = httpx.post(
            f"{self.airflow_host}/auth/token",
            json={"username": self.airflow_username, "password": self.airflow_password},
            headers={"Authorization": f"Bearer {iap_token}"},
            timeout=30.0,
        )
        response.raise_for_status()

        self._airflow_jwt_token = response.json()["access_token"]
        logger.info("Obtained Airflow JWT token")

    def _get_headers(self) -> dict:
        """Get headers with both IAP and Airflow JWT tokens."""
        if not self._airflow_jwt_token:
            self._refresh_airflow_jwt()

        return {
            "Authorization": f"Bearer {self._airflow_jwt_token}",
            "Proxy-Authorization": f"Bearer {self.token_provider.get_token()}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make HTTP request to Airflow API."""
        url = f"{self.airflow_host}{path}"
        headers = self._get_headers()

        response = httpx.request(method, url, headers=headers, timeout=30.0, **kwargs)
        response.raise_for_status()

        return response.json()

    # Health and monitoring
    def get_health(self) -> dict:
        """Get Airflow health status."""
        return self._request("GET", "/api/v2/monitor/health")

    def get_version(self) -> dict:
        """Get Airflow version."""
        return self._request("GET", "/api/v2/version")

    # DAG operations
    def list_dags(self, limit: int = 100, offset: int = 0) -> dict:
        """List DAGs."""
        return self._request("GET", f"/api/v2/dags?limit={limit}&offset={offset}")

    def get_dag(self, dag_id: str) -> dict:
        """Get DAG details."""
        return self._request("GET", f"/api/v2/dags/{dag_id}")

    def pause_dag(self, dag_id: str) -> dict:
        """Pause a DAG."""
        return self._request(
            "PATCH", f"/api/v2/dags/{dag_id}", json={"is_paused": True}
        )

    def unpause_dag(self, dag_id: str) -> dict:
        """Unpause a DAG."""
        return self._request(
            "PATCH", f"/api/v2/dags/{dag_id}", json={"is_paused": False}
        )

    # DAG Run operations
    def list_dag_runs(self, dag_id: str, limit: int = 25, offset: int = 0) -> dict:
        """List DAG runs."""
        return self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns?limit={limit}&offset={offset}"
        )

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> dict:
        """Get DAG run details."""
        return self._request("GET", f"/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}")

    def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[dict] = None,
        logical_date: Optional[str] = None,
    ) -> dict:
        """Trigger a new DAG run."""
        payload = {}
        if conf:
            payload["conf"] = conf
        if logical_date:
            payload["logical_date"] = logical_date
        return self._request("POST", f"/api/v2/dags/{dag_id}/dagRuns", json=payload)

    # Task instance operations
    def get_task_instance(self, dag_id: str, dag_run_id: str, task_id: str) -> dict:
        """Get task instance details."""
        return self._request(
            "GET", f"/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}"
        )

    def get_task_logs(
        self, dag_id: str, dag_run_id: str, task_id: str, task_try_number: int = 1
    ) -> dict:
        """Get task logs."""
        return self._request(
            "GET",
            f"/api/v2/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/{task_try_number}",
        )

    # Variable operations
    def list_variables(self, limit: int = 100, offset: int = 0) -> dict:
        """List variables."""
        return self._request("GET", f"/api/v2/variables?limit={limit}&offset={offset}")

    def get_variable(self, variable_key: str) -> dict:
        """Get variable value."""
        return self._request("GET", f"/api/v2/variables/{variable_key}")

    def set_variable(self, variable_key: str, value: str) -> dict:
        """Set variable value."""
        return self._request(
            "POST", "/api/v2/variables", json={"key": variable_key, "value": value}
        )

    def delete_variable(self, variable_key: str) -> None:
        """Delete a variable."""
        self._request("DELETE", f"/api/v2/variables/{variable_key}")

    # Connection operations
    def list_connections(self, limit: int = 100, offset: int = 0) -> dict:
        """List connections."""
        return self._request(
            "GET", f"/api/v2/connections?limit={limit}&offset={offset}"
        )

    def get_connection(self, connection_id: str) -> dict:
        """Get connection details."""
        return self._request("GET", f"/api/v2/connections/{connection_id}")

    # Pool operations
    def list_pools(self, limit: int = 100, offset: int = 0) -> dict:
        """List pools."""
        return self._request("GET", f"/api/v2/pools?limit={limit}&offset={offset}")

    def get_pool(self, pool_name: str) -> dict:
        """Get pool details."""
        return self._request("GET", f"/api/v2/pools/{pool_name}")

    # Import error operations
    def list_import_errors(self, limit: int = 100, offset: int = 0) -> dict:
        """List DAG import errors."""
        return self._request(
            "GET", f"/api/v2/importErrors?limit={limit}&offset={offset}"
        )

    def get_import_error(self, import_error_id: int) -> dict:
        """Get a specific import error by ID."""
        return self._request("GET", f"/api/v2/importErrors/{import_error_id}")
