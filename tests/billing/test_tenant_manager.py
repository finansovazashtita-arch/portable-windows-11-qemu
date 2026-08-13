"""
Unit & Integration Tests for Multi-Tenant Manager & Schema Isolation (M75).
"""

import os
import pytest
from src.billing.tenant_manager import TenantManager
from src.billing.stripe_client import SubscriptionTier, SubscriptionStatus


class TestTenantManager:

    @pytest.fixture
    def tenant_mgr(self, tmp_path):
        db_file = str(tmp_path / "test_tenants.db")
        return TenantManager(db_path=db_file)

    def test_create_tenant_success(self, tenant_mgr):
        tenant = tenant_mgr.create_tenant(
            company_name="Булгартрансгаз ЕАД",
            eik="117541341",
            contact_email="billing@bulgartransgaz.bg",
            tier=SubscriptionTier.PROFESSIONAL,
        )
        assert tenant.tenant_id.startswith("t_117541341_")
        assert tenant.company_name == "Булгартрансгаз ЕАД"
        assert tenant.tier == SubscriptionTier.PROFESSIONAL
        assert tenant.stripe_customer_id is not None
        assert tenant.db_schema.startswith("tenant_schema_")

    def test_create_tenant_invalid_eik(self, tenant_mgr):
        with pytest.raises(ValueError, match="Invalid Bulgarian EIK/UIC number"):
            tenant_mgr.create_tenant("Invalid Corp", "123", "info@invalid.bg")

    def test_get_and_list_tenants(self, tenant_mgr):
        t1 = tenant_mgr.create_tenant("Company A", "101102103", "a@corp.bg", tier=SubscriptionTier.FREE)
        t2 = tenant_mgr.create_tenant("Company B", "201202203", "b@corp.bg", tier=SubscriptionTier.ENTERPRISE)

        fetched = tenant_mgr.get_tenant(t1.tenant_id)
        assert fetched is not None
        assert fetched.company_name == "Company A"

        tenants, total = tenant_mgr.list_tenants(tier=SubscriptionTier.ENTERPRISE)
        assert total == 1
        assert tenants[0].tenant_id == t2.tenant_id

    def test_update_tenant_and_subscription(self, tenant_mgr):
        t = tenant_mgr.create_tenant("Company C", "301302303", "c@corp.bg", tier=SubscriptionTier.FREE)
        updated = tenant_mgr.update_subscription(
            tenant_id=t.tenant_id,
            tier=SubscriptionTier.PROFESSIONAL,
            stripe_subscription_id="sub_pro_123",
            status=SubscriptionStatus.ACTIVE,
        )
        assert updated.tier == SubscriptionTier.PROFESSIONAL
        assert updated.stripe_subscription_id == "sub_pro_123"
        assert updated.subscription_status == SubscriptionStatus.ACTIVE

    def test_delete_tenant(self, tenant_mgr):
        t = tenant_mgr.create_tenant("Company D", "401402403", "d@corp.bg")
        deleted = tenant_mgr.delete_tenant(t.tenant_id, purge_data=True)
        assert deleted is True
        assert tenant_mgr.get_tenant(t.tenant_id) is None
