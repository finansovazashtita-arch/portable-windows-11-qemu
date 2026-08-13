"""
Unit & Integration Tests for Tenant REST API & Billing Endpoints (M75).
"""

import json
import pytest
from src.billing.tenant_api import TenantAPIHandler
from src.billing.stripe_client import SubscriptionTier


class TestTenantAPIHandler:

    @pytest.fixture
    def api_handler(self, tmp_path):
        db_file = str(tmp_path / "api_test.db")
        return TenantAPIHandler(db_path=db_file)

    def test_create_and_get_tenant_api(self, api_handler):
        # 1. Create tenant via POST /api/v1/tenants
        status, res = api_handler.handle_post(
            "/api/v1/tenants",
            {
                "company_name": "API Test OOD",
                "eik": "123456789",
                "contact_email": "api@test.bg",
                "tier": "PROFESSIONAL",
            },
        )
        assert status == 201
        assert res["success"] is True
        tenant_id = res["tenant"]["tenant_id"]

        # 2. Get tenant list via GET /api/v1/tenants
        g_status, g_res = api_handler.handle_get("/api/v1/tenants")
        assert g_status == 200
        assert g_res["total"] == 1

        # 3. Get single tenant via GET /api/v1/tenants/{id}
        s_status, s_res = api_handler.handle_get(f"/api/v1/tenants/{tenant_id}")
        assert s_status == 200
        assert s_res["tenant"]["company_name"] == "API Test OOD"
        assert "usage" in s_res

    def test_checkout_session_and_portal_api(self, api_handler):
        # 1. Guest checkout session
        c_status, c_res = api_handler.handle_post(
            "/api/v1/billing/checkout-session",
            {"tenant_id": "t_guest", "tier": "PROFESSIONAL"},
        )
        assert c_status == 200
        assert "checkout_session" in c_res
        assert "url" in c_res["checkout_session"]

        # 2. Portal session for existing tenant
        _, t_res = api_handler.handle_post(
            "/api/v1/tenants",
            {"company_name": "Portal Corp", "eik": "555666777", "contact_email": "portal@corp.bg"},
        )
        tenant_id = t_res["tenant"]["tenant_id"]

        p_status, p_res = api_handler.handle_post(
            "/api/v1/billing/portal-session",
            {"tenant_id": tenant_id},
        )
        assert p_status == 200
        assert "portal_url" in p_res


    def test_gdpr_erasure_api(self, api_handler):
        # Create tenant
        _, res = api_handler.handle_post(
            "/api/v1/tenants",
            {"company_name": "GDPR Target Ltd", "eik": "987654321", "contact_email": "target@gdpr.bg"},
        )
        tenant_id = res["tenant"]["tenant_id"]

        # Trigger GDPR erasure
        e_status, e_res = api_handler.handle_post(
            f"/api/v1/tenants/{tenant_id}/gdpr-erasure",
            {"requested_by": "USER", "reason": "ACCOUNT_CLOSURE"},
        )
        assert e_status == 200
        assert "erasure_certificate" in e_res
        assert e_res["erasure_certificate"]["tenant_id"] == tenant_id

        # Verify tenant is removed
        g_status, _ = api_handler.handle_get(f"/api/v1/tenants/{tenant_id}")
        assert g_status == 404
