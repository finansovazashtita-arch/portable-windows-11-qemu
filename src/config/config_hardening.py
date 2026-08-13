"""
Milestone M69: Production Configuration & Secrets Management Hardening Module.

Provides:
1. Centralized configuration management with precedence:
   Infisical Vault > Environment Variables (`os.environ`) > config.yaml > Hardcoded Defaults.
2. Startup secret validation & complexity checking (raises SecretValidationError / ConfigValidationError).
3. Infisical Vault key rotation manager (supports key generation, forced rotation, version tracking, callbacks).
4. Profile management (production, development, staging, test).
"""

import datetime
import hashlib
import json
import logging
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

try:
    import yaml
except ImportError:
    yaml = None

from src.security.infisical_vault import InfisicalVaultClient

logger = logging.getLogger("config_hardening")

# Insecure/default secrets forbidden in production profile
FORBIDDEN_PRODUCTION_SECRETS = {
    "secret",
    "supersecret",
    "password",
    "admin",
    "123456",
    "changeme",
    "change_me",
    "default",
    "Microinvest123!",
    "dev_secret",
    "test_token",
}

# Required secrets for production deployment
DEFAULT_REQUIRED_SECRETS = [
    "JWT_SECRET",
    "INFISICAL_TOKEN",
    "MSSQL_PASSWORD",
    "NRA_API_KEY",
    "PQC_SIGNING_KEY",
]


class ConfigValidationError(Exception):
    """Raised when configuration parameter validation fails."""

    pass


class SecretValidationError(ConfigValidationError):
    """Raised when startup secret validation fails (missing, weak, or insecure secret)."""

    pass


@dataclass
class SecretMetadata:
    """Metadata tracking secret lifecycle and rotation history."""

    secret_name: str
    version: int
    last_rotated_at: str
    algorithm: str = "PQC_HMAC_SHA256"
    status: str = "ACTIVE"  # "ACTIVE", "ROTATED", "EXPIRED"
    fingerprint: str = ""  # SHA-256 hash preview (first 16 hex chars)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConfigHardeningManager:
    """
    Centralized configuration and secrets manager enforcing production hardening standards.
    Precedence: Infisical Vault > Environment Variables > config.yaml > Default Values.
    """

    def __init__(
        self,
        config_path: str = "config.yaml",
        env_file: Optional[str] = None,
        infisical_client: Optional[InfisicalVaultClient] = None,
        profile: Optional[str] = None,
    ):
        self.config_path = config_path
        self.env_file = env_file
        self.infisical_client = infisical_client
        self.profile = (profile or os.environ.get("ENVIRONMENT") or os.environ.get("PROFILE") or "development").lower()

        # Normalization of profile string
        if self.profile in ("prod", "production"):
            self.profile = "production"
        elif self.profile in ("dev", "development"):
            self.profile = "development"
        elif self.profile in ("test", "testing"):
            self.profile = "test"
        elif self.profile in ("stage", "staging"):
            self.profile = "staging"

        self._yaml_config: Dict[str, Any] = {}
        self._defaults: Dict[str, Any] = {}
        self._rotation_history: Dict[str, List[SecretMetadata]] = {}
        self._rotation_callbacks: Dict[str, List[Callable[[str, str], None]]] = {}
        self._secret_cache: Dict[str, str] = {}

        self._load_defaults()
        self._load_yaml_config()
        self._init_infisical()

    def _load_defaults(self):
        """Populates hardcoded system defaults."""
        self._defaults = {
            "app.name": "Microinvest Bank Statement OCR & FinansProtect Platform",
            "app.version": "1.0.0",
            "app.environment": self.profile,
            "app.log_level": "INFO",
            "server.host": "0.0.0.0",
            "server.port": 8090,
            "server.dashboard_port": 8095,
            "security.jwt_algorithm": "HS256",
            "security.jwt_expiration_minutes": 60,
            "security.min_password_length": 12,
            "infisical.enabled": True,
            "infisical.base_url": "http://100.83.83.8:8080",
            "infisical.environment": "dev" if self.profile != "production" else "prod",
            "database.mssql_host": "127.0.0.1",
            "database.mssql_port": 1433,
            "database.mssql_user": "sa",
            "database.mssql_database": "DeltaPro",
            "database.supabase_url": "http://100.83.83.8:8002",
            "nra.api_url": "https://e-services.nap.bg/api/v1",
            "nra.vat_refund_threshold_eur": 5000.0,
            "integrations.n8n_webhook_url": "http://100.83.83.8:5679/webhook/microinvest-ocr",
            "integrations.openbalancer_url": "https://n8n.openbalancer.com",
            "qemu.vnc_host": "127.0.0.1",
            "qemu.vnc_port": 5901,
        }

    def _load_yaml_config(self):
        """Loads and parses configuration from config.yaml if present."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config YAML file not found at '{self.config_path}'. Proceeding with defaults & env vars.")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                if yaml:
                    content = yaml.safe_load(f) or {}
                else:
                    # Basic JSON fallback if YAML parser unavailable
                    content = json.load(f)
                if isinstance(content, dict):
                    self._yaml_config = content
        except Exception as e:
            logger.error(f"Failed to parse config file '{self.config_path}': {e}")

    def _init_infisical(self):
        """Initializes Infisical Vault client if not provided."""
        if self.infisical_client is None:
            infisical_url = os.environ.get("INFISICAL_URL", self.get("infisical.base_url", "http://100.83.83.8:8080"))
            token = os.environ.get("INFISICAL_TOKEN", "")
            self.infisical_client = InfisicalVaultClient(
                base_url=infisical_url,
                service_token=token,
                environment="prod" if self.profile == "production" else "dev",
            )

    def is_production(self) -> bool:
        """Returns True if current profile is production."""
        return self.profile == "production"

    def get_profile(self) -> str:
        """Returns normalized active configuration profile."""
        return self.profile

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves configuration setting following strict precedence:
        Infisical Vault > os.environ > config.yaml > Defaults.
        Supports dotted path lookup (e.g., 'database.mssql_host').
        """
        # 1. Check Infisical Vault if online and secret exists
        env_key_name = key.upper().replace(".", "_")
        if self.infisical_client and self.infisical_client.service_token:
            vault_val = self.infisical_client.get_secret(env_key_name, default_value="")
            if vault_val:
                return vault_val

        # 2. Check cached secrets
        if env_key_name in self._secret_cache:
            return self._secret_cache[env_key_name]

        # 3. Check environment variables
        if env_key_name in os.environ:
            return os.environ[env_key_name]
        if key in os.environ:
            return os.environ[key]

        # 4. Check YAML config (nested lookup)
        parts = key.split(".")
        current = self._yaml_config
        found_in_yaml = True
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found_in_yaml = False
                break

        if found_in_yaml:
            return current

        # 5. Check defaults
        if key in self._defaults:
            return self._defaults[key]

        return default

    def get_str(self, key: str, default: str = "") -> str:
        """Returns string configuration value."""
        val = self.get(key, default)
        return str(val) if val is not None else default

    def get_int(self, key: str, default: int = 0) -> int:
        """Returns integer configuration value."""
        val = self.get(key, default)
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Returns boolean configuration value."""
        val = self.get(key, default)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes", "on", "enabled")
        return bool(val)

    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """Returns dictionary configuration value."""
        val = self.get(key, default)
        return val if isinstance(val, dict) else (default or {})

    def get_secret(self, secret_name: str, default: str = "") -> str:
        """
        Retrieves secret value using strict key lookup precedence.
        """
        return str(self.get(secret_name, default))

    # --- Secret & Configuration Hardening Validation ---

    def validate_secret_complexity(
        self,
        secret_name: str,
        secret_value: str,
        min_length: int = 16,
        require_mixed_case: bool = True,
        require_digits: bool = True,
        require_special: bool = False,
    ) -> Tuple[bool, str]:
        """
        Validates secret length, complexity, and checks against forbidden defaults.
        Returns (is_valid, error_reason).
        """
        if not secret_value:
            return False, f"Secret '{secret_name}' is empty or missing."

        if secret_value.strip() in FORBIDDEN_PRODUCTION_SECRETS:
            return False, f"Secret '{secret_name}' matches a known insecure default value."

        if len(secret_value) < min_length:
            return (
                False,
                f"Secret '{secret_name}' length ({len(secret_value)}) is below required minimum ({min_length}).",
            )

        if require_mixed_case:
            if not (re.search(r"[a-z]", secret_value) and re.search(r"[A-Z]", secret_value)):
                return False, f"Secret '{secret_name}' must contain both uppercase and lowercase characters."

        if require_digits:
            if not re.search(r"\d", secret_value):
                return False, f"Secret '{secret_name}' must contain at least one numeric digit."

        if require_special:
            if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", secret_value):
                return False, f"Secret '{secret_name}' must contain at least one special character."

        return True, "Valid"

    def validate_startup_secrets(
        self,
        required_secrets: Optional[List[str]] = None,
        raise_on_failure: Optional[bool] = None,
    ) -> Dict[str, bool]:
        """
        Validates presence and security of all mandatory deployment secrets.
        Raises SecretValidationError if validation fails in production profile.
        """
        secrets_to_check = required_secrets or DEFAULT_REQUIRED_SECRETS
        if raise_on_failure is None:
            raise_on_failure = self.is_production()

        results: Dict[str, bool] = {}
        errors: List[str] = []

        for sec_name in secrets_to_check:
            val = self.get_secret(sec_name, "")

            if not val:
                results[sec_name] = False
                errors.append(f"Missing mandatory secret '{sec_name}'.")
                continue

            # Special length rule for JWT secret (minimum 32 characters in production)
            min_len = 32 if sec_name == "JWT_SECRET" and self.is_production() else 12

            # Perform complexity validation in production mode or if non-empty
            if self.is_production():
                is_valid, reason = self.validate_secret_complexity(
                    secret_name=sec_name,
                    secret_value=val,
                    min_length=min_len,
                    require_mixed_case=(sec_name in ("JWT_SECRET", "MSSQL_PASSWORD")),
                    require_digits=(sec_name in ("MSSQL_PASSWORD",)),
                )
                results[sec_name] = is_valid
                if not is_valid:
                    errors.append(reason)
            else:
                # In non-production, check basic non-emptiness & default strings check
                is_valid = val not in ("secret", "admin", "123456")
                results[sec_name] = is_valid
                if not is_valid:
                    errors.append(f"Secret '{sec_name}' is set to weak default.")

        if errors and raise_on_failure:
            error_msg = f"Startup Secret Validation Failed ({len(errors)} errors):\n" + "\n".join(f" - {e}" for e in errors)
            logger.critical(error_msg)
            raise SecretValidationError(error_msg)

        return results

    # --- Infisical Key Rotation Integration ---

    def _compute_fingerprint(self, secret_val: str) -> str:
        """Computes a SHA-256 fingerprint for secret audit tracking without exposing plaintext."""
        return hashlib.sha256(secret_val.encode("utf-8")).hexdigest()[:16]

    def rotate_secret(
        self,
        secret_name: str,
        new_value: Optional[str] = None,
        length: int = 32,
        force: bool = False,
    ) -> SecretMetadata:
        """
        Triggers cryptographic rotation for a target secret.
        Generates secure random key if new_value is not supplied,
        updates internal cache & Infisical Vault, and triggers callbacks.
        """
        key_name = secret_name.upper().replace(".", "_")

        if not new_value:
            new_value = secrets.token_urlsafe(length)

        # Compute version number
        history = self._rotation_history.get(key_name, [])
        current_version = len(history) + 1

        # Mark past versions as ROTATED
        for meta in history:
            meta.status = "ROTATED"

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        fingerprint = self._compute_fingerprint(new_value)

        new_meta = SecretMetadata(
            secret_name=key_name,
            version=current_version,
            last_rotated_at=timestamp,
            algorithm="PQC_HMAC_SHA256",
            status="ACTIVE",
            fingerprint=fingerprint,
        )

        history.append(new_meta)
        self._rotation_history[key_name] = history

        # Update local cache & env
        self._secret_cache[key_name] = new_value
        os.environ[key_name] = new_value

        # Update Infisical Vault cache if client attached
        if self.infisical_client:
            self.infisical_client.cached_secrets[key_name] = new_value

        logger.info(
            f"Successfully rotated secret '{key_name}' to version {current_version} "
            f"[fingerprint: {fingerprint}, status: ACTIVE]"
        )

        # Invoke registered rotation listeners
        callbacks = self._rotation_callbacks.get(key_name, [])
        for cb in callbacks:
            try:
                cb(key_name, new_value)
            except Exception as e:
                logger.error(f"Error invoking rotation callback for '{key_name}': {e}")

        return new_meta

    def register_rotation_callback(self, secret_name: str, callback_fn: Callable[[str, str], None]):
        """Registers callback listener triggered whenever secret_name is rotated."""
        key_name = secret_name.upper().replace(".", "_")
        if key_name not in self._rotation_callbacks:
            self._rotation_callbacks[key_name] = []
        self._rotation_callbacks[key_name].append(callback_fn)

    def get_secret_metadata(self, secret_name: str) -> Optional[SecretMetadata]:
        """Returns latest lifecycle metadata for specified secret."""
        key_name = secret_name.upper().replace(".", "_")
        history = self._rotation_history.get(key_name, [])
        return history[-1] if history else None

    def get_rotation_history(self, secret_name: str) -> List[SecretMetadata]:
        """Returns full rotation history for specified secret."""
        key_name = secret_name.upper().replace(".", "_")
        return self._rotation_history.get(key_name, [])

    def check_rotation_schedules(self, max_age_days: int = 90) -> List[str]:
        """Identifies secrets whose last rotation exceeds max_age_days."""
        due_for_rotation: List[str] = []
        now = datetime.datetime.now(datetime.timezone.utc)

        for key_name, history in self._rotation_history.items():
            if not history:
                due_for_rotation.append(key_name)
                continue
            latest = history[-1]
            try:
                rotated_dt = datetime.datetime.fromisoformat(latest.last_rotated_at)
                if (now - rotated_dt).days >= max_age_days:
                    due_for_rotation.append(key_name)
            except ValueError:
                due_for_rotation.append(key_name)

        return due_for_rotation


# --- Global Singleton Management ---

_GLOBAL_CONFIG_INSTANCE: Optional[ConfigHardeningManager] = None


def get_config(
    config_path: str = "config.yaml",
    env_file: Optional[str] = None,
    force_reload: bool = False,
) -> ConfigHardeningManager:
    """Returns or initializes global singleton ConfigHardeningManager instance."""
    global _GLOBAL_CONFIG_INSTANCE
    if _GLOBAL_CONFIG_INSTANCE is None or force_reload:
        _GLOBAL_CONFIG_INSTANCE = ConfigHardeningManager(config_path=config_path, env_file=env_file)
    return _GLOBAL_CONFIG_INSTANCE


def reload_config() -> ConfigHardeningManager:
    """Forces reloading of global configuration instance."""
    return get_config(force_reload=True)
