"""Google IAP authentication using OAuth2 Desktop flow with token caching."""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class IAPTokenProvider:
    """Manages IAP token generation and automatic refresh using OAuth2 Desktop flow."""

    # Default to Google Cloud SDK's desktop OAuth client (public, safe to hardcode)
    # Can be overridden with environment variables for project-specific client
    DEFAULT_DESKTOP_CLIENT_ID = (
        "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
    )
    DEFAULT_DESKTOP_CLIENT_SECRET = "d-FL95Q19q7MQmFpd7hHD0Ty"

    # OAuth scopes needed for IAP
    # Note: Google may return these in a different order
    SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email"]

    def __init__(self, iap_client_id: str, refresh_interval: int = 3000):
        """
        Initialize IAP token provider with OAuth2 Desktop flow.

        Args:
            iap_client_id: The OAuth 2.0 client ID for IAP
            refresh_interval: Token refresh interval in seconds (default: 3000 = 50 minutes)

        Environment Variables (optional):
            IAP_DESKTOP_CLIENT_ID: Custom Desktop OAuth client ID (from same GCP project as IAP)
            IAP_DESKTOP_CLIENT_SECRET: Custom Desktop OAuth client secret
        """
        self.iap_client_id = iap_client_id
        self.refresh_interval = refresh_interval
        self._credentials: Optional[Credentials] = None
        self._token_expiry: Optional[datetime] = None
        self._lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()

        # Get OAuth client credentials (custom or default)
        self.desktop_client_id = os.getenv(
            "IAP_DESKTOP_CLIENT_ID", self.DEFAULT_DESKTOP_CLIENT_ID
        )
        self.desktop_client_secret = os.getenv(
            "IAP_DESKTOP_CLIENT_SECRET", self.DEFAULT_DESKTOP_CLIENT_SECRET
        )

        # Check if using custom client from same project
        self._using_custom_client = os.getenv("IAP_DESKTOP_CLIENT_ID") is not None
        if self._using_custom_client:
            logger.info(
                "Using custom Desktop OAuth client for IAP-compatible ID tokens"
            )
        else:
            logger.warning(
                "Using default Google Cloud SDK OAuth client. "
                "For full IAP compatibility, set IAP_DESKTOP_CLIENT_ID and "
                "IAP_DESKTOP_CLIENT_SECRET environment variables to a Desktop "
                "OAuth client from the same GCP project as the IAP client."
            )

        # Token cache file location
        self._token_cache_dir = Path.home() / ".config" / "airflow-mcp-iap"
        self._token_cache_file = self._token_cache_dir / "oauth_token.json"

        # Load cached credentials or perform OAuth flow
        self._initialize_credentials()

        # Start background refresh thread
        self._start_refresh_thread()

    def _initialize_credentials(self) -> None:
        """Load cached credentials or perform OAuth flow."""
        with self._lock:
            # Try to load cached credentials
            if self._load_cached_credentials():
                logger.info("Loaded cached OAuth credentials")
                return

            # No cached credentials, perform OAuth flow
            logger.info("No cached credentials found, starting OAuth flow...")
            self._perform_oauth_flow()

    def _load_cached_credentials(self) -> bool:
        """
        Load credentials from cache file.

        Returns:
            True if credentials were loaded successfully, False otherwise
        """
        if not self._token_cache_file.exists():
            return False

        try:
            with open(self._token_cache_file, "r") as f:
                creds_data = json.load(f)

            self._credentials = Credentials.from_authorized_user_info(creds_data)

            # Check if credentials are valid
            if self._credentials.valid:
                self._update_expiry_from_credentials()
                return True

            # Try to refresh if we have a refresh token
            if self._credentials.expired and self._credentials.refresh_token:
                logger.info("Cached credentials expired, attempting refresh...")
                self._credentials.refresh(Request())
                self._save_credentials()
                self._update_expiry_from_credentials()
                return True

            logger.warning("Cached credentials are invalid and cannot be refreshed")
            return False

        except Exception as e:
            logger.error(f"Failed to load cached credentials: {e}")
            return False

    def _save_credentials(self) -> None:
        """Save credentials to cache file."""
        try:
            # Create directory if it doesn't exist
            self._token_cache_dir.mkdir(parents=True, exist_ok=True)

            # Save credentials
            creds_data = {
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "token_uri": self._credentials.token_uri,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
                "scopes": self._credentials.scopes,
                "expiry": self._credentials.expiry.isoformat()
                if self._credentials.expiry
                else None,
            }

            with open(self._token_cache_file, "w") as f:
                json.dump(creds_data, f, indent=2)

            # Set restrictive permissions (600)
            self._token_cache_file.chmod(0o600)

            logger.info(f"Saved credentials to {self._token_cache_file}")

        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")

    def _perform_oauth_flow(self) -> None:
        """Perform OAuth2 Desktop flow to get credentials with ID token."""
        try:
            # Configure OAuth flow with Desktop client
            client_config = {
                "installed": {
                    "client_id": self.desktop_client_id,
                    "client_secret": self.desktop_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"],
                }
            }

            flow = InstalledAppFlow.from_client_config(
                client_config, scopes=self.SCOPES
            )

            # Run local server for OAuth callback
            # We request 'offline' access to ensure we get a refresh token
            logger.info("Opening browser for OAuth authentication...")
            print("\n" + "=" * 80)
            print("🔐 AUTHENTICATION REQUIRED")
            print("=" * 80)
            print("\nA browser window will open for Google authentication.")
            print("Please sign in with your Google account that has access to Airflow.")
            print(
                "\nIf the browser doesn't open automatically, copy and paste the URL shown below."
            )
            print("=" * 80 + "\n")

            self._credentials = flow.run_local_server(
                port=0,
                success_message="Authentication successful! You can close this window and return to the terminal.",
            )

            # Save credentials for future use
            self._save_credentials()
            self._update_expiry_from_credentials()

            logger.info("OAuth flow completed successfully")
            print("\n" + "=" * 80)
            print("✅ Authentication successful!")
            print("=" * 80 + "\n")

        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            raise RuntimeError(f"Failed to authenticate with Google. Error: {e}")

    def _update_expiry_from_credentials(self) -> None:
        """Update token expiry time from credentials."""
        if self._credentials and self._credentials.expiry:
            self._token_expiry = self._credentials.expiry
        else:
            # Default to 1 hour from now if no expiry info
            self._token_expiry = datetime.utcnow() + timedelta(seconds=3600)

    def _refresh_token(self) -> None:
        """Refresh the token if needed."""
        with self._lock:
            try:
                # Check if credentials need refresh
                if not self._credentials:
                    logger.error("No credentials available")
                    return

                if self._credentials.valid:
                    logger.debug("Token is still valid, no refresh needed")
                    return

                if not self._credentials.refresh_token:
                    logger.warning(
                        "No refresh token available, re-authentication required"
                    )
                    self._perform_oauth_flow()
                    return

                # Refresh the token
                logger.info("Refreshing OAuth token...")
                self._credentials.refresh(Request())
                self._save_credentials()
                self._update_expiry_from_credentials()
                logger.info(
                    f"Token refreshed successfully, expires at {self._token_expiry}"
                )

            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                # If refresh fails, clear credentials and force re-auth on next request
                if "invalid_grant" in str(e).lower():
                    logger.warning(
                        "Refresh token is invalid, re-authentication required"
                    )
                    self._credentials = None
                    # Delete cache file
                    if self._token_cache_file.exists():
                        self._token_cache_file.unlink()

    def _refresh_loop(self) -> None:
        """Background thread that refreshes the token periodically."""
        while not self._stop_refresh.is_set():
            # Wait for refresh interval or until stop is signaled
            if self._stop_refresh.wait(timeout=self.refresh_interval):
                break  # Stop signal received

            try:
                self._refresh_token()
            except Exception as e:
                logger.error(f"Background token refresh failed: {e}")

    def _start_refresh_thread(self) -> None:
        """Start the background refresh thread."""
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop, daemon=True, name="IAP-Token-Refresh"
        )
        self._refresh_thread.start()
        logger.info("Started background token refresh thread")

    def get_token(self) -> str:
        """
        Get the current valid IAP token (ID token).

        Returns:
            Valid IAP ID token

        Raises:
            RuntimeError: If token generation fails
        """
        with self._lock:
            # Check if credentials exist
            if not self._credentials:
                logger.info("No credentials available, performing OAuth flow...")
                self._perform_oauth_flow()

            # Check if token needs immediate refresh
            if self._credentials.expired:
                logger.info("Token expired, refreshing...")
                self._refresh_token()

            # Check if we're close to expiry (within 5 minutes)
            if (
                self._token_expiry
                and datetime.utcnow() >= self._token_expiry - timedelta(seconds=300)
            ):
                logger.info("Token about to expire, refreshing...")
                self._refresh_token()

            if not self._credentials or not self._credentials.token:
                raise RuntimeError("Failed to obtain valid credentials")

            # For IAP with user OAuth credentials, we need to request an ID token
            # with the IAP client ID as the audience using the OpenID Connect token endpoint
            try:
                import requests

                # Google's OpenID Connect token endpoint
                token_endpoint = "https://oauth2.googleapis.com/token"

                # Request an ID token using the refresh token
                # This is the correct way to get an IAP-compatible ID token from user credentials
                payload = {
                    "client_id": self.desktop_client_id,
                    "client_secret": self.desktop_client_secret,
                    "refresh_token": self._credentials.refresh_token,
                    "grant_type": "refresh_token",
                    "audience": self.iap_client_id,  # CRITICAL: IAP client as audience
                }

                logger.debug(
                    f"Requesting ID token for IAP audience: {self.iap_client_id}"
                )
                response = requests.post(token_endpoint, data=payload)

                if response.status_code != 200:
                    logger.error(
                        f"Token endpoint returned {response.status_code}: {response.text}"
                    )
                    # If the audience parameter doesn't work, try without it and see what we get
                    logger.warning(
                        "Attempting token request without audience parameter..."
                    )
                    payload_no_aud = {
                        "client_id": self.desktop_client_id,
                        "client_secret": self.desktop_client_secret,
                        "refresh_token": self._credentials.refresh_token,
                        "grant_type": "refresh_token",
                    }
                    response = requests.post(token_endpoint, data=payload_no_aud)
                    response.raise_for_status()

                token_response = response.json()

                # The response should contain an id_token field
                if "id_token" in token_response:
                    logger.debug("Successfully obtained ID token from token endpoint")
                    return token_response["id_token"]
                else:
                    logger.error(
                        f"Token response missing id_token: {list(token_response.keys())}"
                    )
                    raise RuntimeError(
                        "Token endpoint did not return an ID token. "
                        "Response fields: " + str(list(token_response.keys()))
                    )

            except Exception as e:
                logger.error(f"Failed to obtain IAP ID token: {e}")
                raise RuntimeError(
                    f"Failed to obtain IAP ID token for user credentials. "
                    f"This might indicate IAP is not properly configured or the OAuth "
                    f"client doesn't have the required permissions. Error: {e}"
                )

    def clear_cache(self) -> None:
        """Clear cached credentials (forces re-authentication on next use)."""
        with self._lock:
            if self._token_cache_file.exists():
                self._token_cache_file.unlink()
                logger.info("Cleared cached credentials")
            self._credentials = None

    def stop(self) -> None:
        """Stop the background refresh thread."""
        self._stop_refresh.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
            logger.info("Stopped background token refresh thread")

    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()
