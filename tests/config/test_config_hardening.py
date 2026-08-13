"""
Unit tests for Production Configuration & Secrets Management Hardening (Milestone M69).
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.config.config_hardening import (
    ConfigHardeningManager,
    ConfigValidationError,
    SecretMetadata,
    SecretValidationError,
    get_config,
    reload_config,
)
from src.security.infisical_vault import InfisicalVaultClient


class TestConfigHardeningManager(unittest.TestCase):
    """Comprehensive test suite for ConfigHardeningManager and Secrets Validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.yaml_path = os.path.join(self.temp_dir.name, "config.yaml")

        # Create dummy YAML config for testing
        yaml_content = """
app:
  name: "Test Platform App"
  environment: "development"
  log_level: "DEBUG"
server:
  host: "127.0.0.1"
  port: 9090
database:
  mssql_host: "sql.internal"
  mssql_port: 1433
security:
  jwt_algorithm: "RS256"
"""
        with open(self.yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        # Clear environment overrides before each test
        self.env_cleanups = [
            "ENVIRONMENT",
            "PROFILE",
            "APP_ENVIRONMENT",
            "SERVER_PORT",
            "DATABASE_MSSQL_HOST",
            "JWT_SECRET",
            "INFISICAL_TOKEN",
            "MSSQL_PASSWORD",
            "NRA_API_KEY",
            "PQC_SIGNING_KEY",
        ]
        for k in self.env_cleanups:
            os.environ.pop(k, None)

    def tearDown(self):
        for k in self.env_cleanups:
            os.environ.pop(k, None)
        self.temp_dir.cleanup()

    def test_load_yaml_config_and_typed_getters(self):
        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="dev")

        self.assertEqual(manager.get_str("app.name"), "Test Platform App")
        self.assertEqual(manager.get_int("server.port"), 9090)
        self.assertEqual(manager.get_str("server.host"), "127.0.0.1")
        self.assertEqual(manager.get_str("database.mssql_host"), "sql.internal")
        self.assertFalse(manager.is_production())

    def test_environment_variable_override_precedence(self):
        os.environ["SERVER_PORT"] = "9999"
        os.environ["DATABASE_MSSQL_HOST"] = "env-db-host"

        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="dev")

        self.assertEqual(manager.get_str("DATABASE_MSSQL_HOST"), "env-db-host")
        self.assertEqual(manager.get_int("server.port"), 9999)

    def test_infisical_vault_precedence_over_env_and_yaml(self):
        os.environ["DATABASE_MSSQL_HOST"] = "env-db-host"

        mock_vault = MagicMock(spec=InfisicalVaultClient)
        mock_vault.service_token = "valid_vault_token"
        mock_vault.get_secret.side_effect = lambda k, default_value="": "vault-db-host" if k == "DATABASE_MSSQL_HOST" else default_value

        manager = ConfigHardeningManager(
            config_path=self.yaml_path,
            infisical_client=mock_vault,
            profile="dev",
        )

        self.assertEqual(manager.get_str("database.mssql_host"), "vault-db-host")

    def test_secret_complexity_validation_rules(self):
        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="prod")

        # Empty secret
        is_valid, reason = manager.validate_secret_complexity("JWT_SECRET", "")
        self.assertFalse(is_valid)
        self.assertIn("empty", reason)

        # Insecure default secret
        is_valid, reason = manager.validate_secret_complexity("MSSQL_PASSWORD", "Microinvest123!")
        self.assertFalse(is_valid)
        self.assertIn("insecure default", reason)

        # Short length
        is_valid, reason = manager.validate_secret_complexity("JWT_SECRET", "Short1!", min_length=16)
        self.assertFalse(is_valid)
        self.assertIn("below required minimum", reason)

        # Missing mixed case
        is_valid, reason = manager.validate_secret_complexity("JWT_SECRET", "lowercase_only_secret_123456789", min_length=16)
        self.assertFalse(is_valid)

        # Valid complex secret
        is_valid, reason = manager.validate_secret_complexity(
            "JWT_SECRET", "Complex_Production_Key_9918237_Valid!", min_length=16
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "Valid")

    def test_validate_startup_secrets_production_failure(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "short"  # Invalid short secret

        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="production")
        self.assertTrue(manager.is_production())

        with self.assertRaises(SecretValidationError) as ctx:
            manager.validate_startup_secrets()

        self.assertIn("Startup Secret Validation Failed", str(ctx.exception))

    def test_validate_startup_secrets_production_success(self):
        os.environ["ENVIRONMENT"] = "production"
        os.environ["JWT_SECRET"] = "Super_Secure_Production_JWT_Secret_Token_2026_Length_32+"
        os.environ["INFISICAL_TOKEN"] = "Secure_Infisical_Token_Val_9981273"
        os.environ["MSSQL_PASSWORD"] = "Strong_DB_Password_2026_Hardened!"
        os.environ["NRA_API_KEY"] = "NRA_Prod_API_Key_Secure_881923"
        os.environ["PQC_SIGNING_KEY"] = "PQC_Falcon1024_Lattice_Key_991823"

        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="production")
        results = manager.validate_startup_secrets()

        self.assertTrue(all(results.values()))

    def test_rotate_secret_generates_new_key_and_triggers_callbacks(self):
        manager = ConfigHardeningManager(config_path=self.yaml_path, profile="dev")

        callback_received = []

        def on_jwt_rotated(secret_name, new_val):
            callback_received.append((secret_name, new_val))

        manager.register_rotation_callback("JWT_SECRET", on_jwt_rotated)

        meta1 = manager.rotate_secret("JWT_SECRET", length=32)
        self.assertEqual(meta1.version, 1)
        self.assertEqual(meta1.status, "ACTIVE")
        self.assertTrue(len(meta1.fingerprint) > 0)

        # Check callback was invoked
        self.assertEqual(len(callback_received), 1)
        self.assertEqual(callback_received[0][0], "JWT_SECRET")

        new_secret_val = manager.get_secret("JWT_SECRET")
        self.assertEqual(new_secret_val, callback_received[0][1])

        # Rotate second time with explicit value
        meta2 = manager.rotate_secret("JWT_SECRET", new_value="Explicit_Rotated_Key_Value_12345!")
        self.assertEqual(meta2.version, 2)
        self.assertEqual(meta2.status, "ACTIVE")
        self.assertEqual(manager.get_secret("JWT_SECRET"), "Explicit_Rotated_Key_Value_12345!")

        history = manager.get_rotation_history("JWT_SECRET")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].status, "ROTATED")
        self.assertEqual(history[1].status, "ACTIVE")

    def test_global_singleton_accessors(self):
        cfg1 = get_config(config_path=self.yaml_path)
        cfg2 = get_config(config_path=self.yaml_path)
        self.assertIs(cfg1, cfg2)

        cfg_reloaded = reload_config()
        self.assertIsNot(cfg1, cfg_reloaded)


if __name__ == "__main__":
    unittest.main()
