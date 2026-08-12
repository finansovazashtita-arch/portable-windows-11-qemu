"""
Infisical Secrets Management Module.

Integrates with the Infisical Vault container running on macmini-primary (http://100.83.83.8:8080)
to manage DB credentials, VNC passwords, API tokens, and VM parameters securely.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("infisical_vault")


class InfisicalVaultClient:
    """Client for retrieving and managing secrets via Infisical standalone Vault."""

    def __init__(
        self,
        base_url: str = "http://100.83.83.8:8080",
        service_token: Optional[str] = None,
        environment: str = "dev",
        timeout: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.service_token = service_token or os.environ.get("INFISICAL_TOKEN", "")
        self.environment = environment
        self.timeout = timeout
        self.cached_secrets: Dict[str, str] = {}

    def is_healthy(self) -> bool:
        """Checks if Infisical Vault service is responsive."""
        url = f"{self.base_url}/health"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Infisical health check failed: {e}")
            return False

    def get_secret(self, secret_name: str, default_value: str = "") -> str:
        """
        Retrieves a secret by name from Infisical Vault.
        Falls back to environment variable or default_value if Vault is offline.
        """
        # Check environment variable first
        if secret_name in os.environ:
            return os.environ[secret_name]

        # Check local in-memory cache
        if secret_name in self.cached_secrets:
            return self.cached_secrets[secret_name]

        if not self.service_token:
            logger.debug("No Infisical service token provided; using default value fallback.")
            return default_value

        url = f"{self.base_url}/api/v3/secrets/raw/{secret_name}?environment={self.environment}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.service_token}",
                "Content-Type": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    val = payload.get("secret", {}).get("secretValue", default_value)
                    self.cached_secrets[secret_name] = val
                    return val
        except Exception as e:
            logger.warning(f"Failed to fetch secret '{secret_name}' from Infisical Vault: {e}")

        return default_value

    def get_vm_credentials(self) -> Dict[str, str]:
        """Returns QEMU Windows 11 & Microinvest MS SQL Server connection parameters."""
        return {
            "vnc_host": self.get_secret("QEMU_VNC_HOST", "127.0.0.1"),
            "vnc_port": self.get_secret("QEMU_VNC_PORT", "5901"),
            "mssql_host": self.get_secret("MSSQL_HOST", "127.0.0.1"),
            "mssql_user": self.get_secret("MSSQL_USER", "sa"),
            "mssql_password": self.get_secret("MSSQL_PASSWORD", "Microinvest123!"),
            "database": self.get_secret("MSSQL_DATABASE", "DeltaPro"),
        }
