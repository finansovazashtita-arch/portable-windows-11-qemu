"""
Unit & Integration Tests for Stripe Webhook Handler & Idempotency (M75).
"""

import json
import pytest
from src.billing.webhook_handler import StripeWebhookHandler
from src.billing.tenant_manager import TenantManager
from src.billing.stripe_client import SubscriptionTier, SubscriptionStatus


class TestStripeWebhookHandler:

    @pytest.fixture
    def webhook_setup(self, tmp_path):
        db_file = str(tmp_path / "webhook_test.db")
        tenant_mgr = TenantManager(db_path=db_file)
        tenant = tenant_mgr.create_tenant("Webhook Corp", "555444333", "wh@corp.bg")

        handler = StripeWebhookHandler(
            tenant_manager=tenant_mgr,
            stripe_manager=tenant_mgr.stripe_manager,
            metering_engine=tenant_mgr.metering_engine,
            db_path=db_file,
        )

        return handler, tenant, tenant_mgr

    def test_process_invoice_paid(self, webhook_setup):
        handler, tenant, tenant_mgr = webhook_setup

        payload = {
            "id": "evt_inv_paid_001",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": tenant.stripe_customer_id,
                    "amount_paid": 9900,
                }
            },
        }

        res = handler.process_webhook_payload(
            json.dumps(payload).encode("utf-8"),
            sig_header="t=123,v1=mock_sig",
        )

        assert res["status"] == "success"
        assert res["processed"] is True

        updated_tenant = tenant_mgr.get_tenant(tenant.tenant_id)
        assert updated_tenant.subscription_status == SubscriptionStatus.ACTIVE

    def test_process_invoice_payment_failed(self, webhook_setup):
        handler, tenant, tenant_mgr = webhook_setup

        payload = {
            "id": "evt_inv_failed_001",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": tenant.stripe_customer_id,
                }
            },
        }

        res = handler.process_webhook_payload(
            json.dumps(payload).encode("utf-8"),
            sig_header="t=123,v1=mock_sig",
        )

        assert res["status"] == "success"
        updated_tenant = tenant_mgr.get_tenant(tenant.tenant_id)
        assert updated_tenant.subscription_status == SubscriptionStatus.PAST_DUE

    def test_idempotency_duplicate_event(self, webhook_setup):
        handler, tenant, _ = webhook_setup

        payload = {
            "id": "evt_dup_001",
            "type": "invoice.paid",
            "data": {"object": {"customer": tenant.stripe_customer_id}},
        }

        res1 = handler.process_webhook_payload(json.dumps(payload).encode("utf-8"), sig_header="v1=sig")
        assert res1["processed"] is True

        res2 = handler.process_webhook_payload(json.dumps(payload).encode("utf-8"), sig_header="v1=sig")
        assert res2["processed"] is False
        assert res2["reason"] == "duplicate_event"
