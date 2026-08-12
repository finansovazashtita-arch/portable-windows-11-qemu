"""
Unit tests for Infisical Vault Client.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from src.security.infisical_vault import InfisicalVaultClient


class TestInfisicalVaultClient(unittest.TestCase):
    """Test suite for InfisicalVaultClient."""

    def setUp(self):
        self.client = InfisicalVaultClient(
            base_url="http://127.0.0.1:8080",
            service_token="test_token",
            environment="dev",
            timeout=2
        )

    def test_get_secret_env_fallback(self):
        os.environ["TEST_SECRET_KEY"] = "ENV_SECRET_VALUE"
        try:
            secret = self.client.get_secret("TEST_SECRET_KEY", "default")
            self.assertEqual(secret, "ENV_SECRET_VALUE")
        finally:
            del os.environ["TEST_SECRET_KEY"]

    def test_get_secret_default_fallback(self):
        secret = self.client.get_secret("NON_EXISTENT_KEY_12345", "DEFAULT_VAL")
        self.assertEqual(secret, "DEFAULT_VAL")

    @patch("urllib.request.urlopen")
    def test_is_healthy_true(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        self.assertTrue(self.client.is_healthy())

    def test_get_vm_credentials(self):
        creds = self.client.get_vm_credentials()
        self.assertIn("vnc_host", creds)
        self.assertIn("vnc_port", creds)
        self.assertIn("mssql_host", creds)
        self.assertIn("mssql_password", creds)


if __name__ == "__main__":
    unittest.main()
