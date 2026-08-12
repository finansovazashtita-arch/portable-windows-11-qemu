"""
Multi-Tenant Isolation & Role-Based Access Control (RBAC) Module.

Supports:
- Multi-company database & statement queue isolation
- Role-based permissions (ADMIN, SENIOR_ACCOUNTANT, JUNIOR_ACCOUNTANT, AUDITOR)
- Cryptographic JWT Token generation & verification
- Strict cross-tenant access enforcement
"""

import base64
import dataclasses
import enum
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("tenant_rbac")


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SENIOR_ACCOUNTANT = "SENIOR_ACCOUNTANT"
    JUNIOR_ACCOUNTANT = "JUNIOR_ACCOUNTANT"
    AUDITOR = "AUDITOR"


class Permission(str, enum.Enum):
    READ_STATEMENTS = "READ_STATEMENTS"
    PROCESS_OCR = "PROCESS_OCR"
    IMPORT_DELTA_PRO = "IMPORT_DELTA_PRO"
    EXPORT_AUDIT_LOG = "EXPORT_AUDIT_LOG"
    MANAGE_USERS = "MANAGE_USERS"


ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.READ_STATEMENTS,
        Permission.PROCESS_OCR,
        Permission.IMPORT_DELTA_PRO,
        Permission.EXPORT_AUDIT_LOG,
        Permission.MANAGE_USERS,
    },
    UserRole.SENIOR_ACCOUNTANT: {
        Permission.READ_STATEMENTS,
        Permission.PROCESS_OCR,
        Permission.IMPORT_DELTA_PRO,
        Permission.EXPORT_AUDIT_LOG,
    },
    UserRole.JUNIOR_ACCOUNTANT: {
        Permission.READ_STATEMENTS,
        Permission.PROCESS_OCR,
    },
    UserRole.AUDITOR: {
        Permission.READ_STATEMENTS,
        Permission.EXPORT_AUDIT_LOG,
    },
}


@dataclasses.dataclass
class Tenant:
    tenant_id: str
    company_name: str
    eik: str
    db_schema: str


@dataclasses.dataclass
class User:
    user_id: str
    tenant_id: str
    username: str
    role: UserRole


class JWTSecurityManager:
    """Manages JWT generation, signature validation, and RBAC permission checks."""

    DEFAULT_SECRET = "finansprotect_secret_key_2026_jwt_token"

    @classmethod
    def _base64url_encode(cls, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @classmethod
    def _base64url_decode(cls, payload: str) -> bytes:
        padding = "=" * (4 - (len(payload) % 4))
        return base64.urlsafe_b64decode(payload + padding)

    @classmethod
    def generate_token(cls, user: User, secret_key: Optional[str] = None, expires_in_sec: int = 3600) -> str:
        secret = secret_key or cls.DEFAULT_SECRET
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())

        payload = {
            "user_id": user.user_id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "role": user.role.value,
            "iat": now,
            "exp": now + expires_in_sec,
        }

        h_bytes = json.dumps(header).encode("utf-8")
        p_bytes = json.dumps(payload).encode("utf-8")

        encoded_h = cls._base64url_encode(h_bytes)
        encoded_p = cls._base64url_encode(p_bytes)

        signature_input = f"{encoded_h}.{encoded_p}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signature_input, hashlib.sha256).digest()
        encoded_s = cls._base64url_encode(signature)

        return f"{encoded_h}.{encoded_p}.{encoded_s}"

    @classmethod
    def validate_token(cls, token_str: str, secret_key: Optional[str] = None) -> Dict[str, Any]:
        secret = secret_key or cls.DEFAULT_SECRET
        parts = token_str.split(".")
        if len(parts) != 3:
            raise ValueError("Malformed JWT token format")

        encoded_h, encoded_p, encoded_s = parts

        signature_input = f"{encoded_h}.{encoded_p}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signature_input, hashlib.sha256).digest()
        actual_sig = cls._base64url_decode(encoded_s)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid JWT signature")

        payload_json = cls._base64url_decode(encoded_p).decode("utf-8")
        payload = json.loads(payload_json)

        now = int(time.time())
        if payload.get("exp", 0) < now:
            raise ValueError("JWT token has expired")

        return payload

    @staticmethod
    def check_permission(user_role: UserRole, required_permission: Permission) -> bool:
        allowed = ROLE_PERMISSIONS.get(user_role, set())
        return required_permission in allowed

    @staticmethod
    def enforce_tenant_isolation(request_tenant_id: str, resource_tenant_id: str) -> bool:
        if request_tenant_id != resource_tenant_id:
            logger.warning(
                f"🚨 ACCESS DENIED: Tenant '{request_tenant_id}' attempted cross-tenant access to resource of Tenant '{resource_tenant_id}'"
            )
            return False
        return True
