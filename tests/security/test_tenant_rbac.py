"""
Unit tests for Multi-Tenant Isolation & Role-Based Access Control (RBAC) Module.
"""

import time
import unittest

from src.security.tenant_rbac import JWTSecurityManager, Permission, User, UserRole


class TestTenantRBAC(unittest.TestCase):
    """Test suite for JWTSecurityManager and RBAC isolation."""

    def setUp(self):
        self.user_admin = User(user_id="u1", tenant_id="storgozia", username="admin_user", role=UserRole.ADMIN)
        self.user_senior = User(user_id="u2", tenant_id="storgozia", username="senior_acc", role=UserRole.SENIOR_ACCOUNTANT)
        self.user_junior = User(user_id="u3", tenant_id="plevenstroy", username="junior_acc", role=UserRole.JUNIOR_ACCOUNTANT)
        self.user_auditor = User(user_id="u4", tenant_id="storgozia", username="auditor_user", role=UserRole.AUDITOR)

    def test_generate_and_validate_jwt_token(self):
        token = JWTSecurityManager.generate_token(self.user_admin, expires_in_sec=300)
        self.assertIsNotNone(token)

        payload = JWTSecurityManager.validate_token(token)
        self.assertEqual(payload["user_id"], "u1")
        self.assertEqual(payload["tenant_id"], "storgozia")
        self.assertEqual(payload["role"], "ADMIN")

    def test_invalid_signature_rejection(self):
        token = JWTSecurityManager.generate_token(self.user_admin, secret_key="key1")
        with self.assertRaises(ValueError):
            JWTSecurityManager.validate_token(token, secret_key="key2")

    def test_expired_token_rejection(self):
        token = JWTSecurityManager.generate_token(self.user_admin, expires_in_sec=-10)
        with self.assertRaises(ValueError):
            JWTSecurityManager.validate_token(token)

    def test_role_based_permissions(self):
        self.assertTrue(JWTSecurityManager.check_permission(UserRole.ADMIN, Permission.MANAGE_USERS))
        self.assertFalse(JWTSecurityManager.check_permission(UserRole.SENIOR_ACCOUNTANT, Permission.MANAGE_USERS))
        self.assertTrue(JWTSecurityManager.check_permission(UserRole.SENIOR_ACCOUNTANT, Permission.IMPORT_DELTA_PRO))
        self.assertFalse(JWTSecurityManager.check_permission(UserRole.JUNIOR_ACCOUNTANT, Permission.IMPORT_DELTA_PRO))
        self.assertTrue(JWTSecurityManager.check_permission(UserRole.AUDITOR, Permission.EXPORT_AUDIT_LOG))

    def test_tenant_isolation_enforcement(self):
        self.assertTrue(JWTSecurityManager.enforce_tenant_isolation("storgozia", "storgozia"))
        self.assertFalse(JWTSecurityManager.enforce_tenant_isolation("storgozia", "plevenstroy"))


if __name__ == "__main__":
    unittest.main()
