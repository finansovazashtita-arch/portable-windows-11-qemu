"""
Unit & Integration Tests for Stripe Billing Manager (M75).
"""

import pytest
from src.billing.stripe_client import (
    StripeBillingManager,
    SubscriptionTier,
    SubscriptionStatus,
    TIER_FEATURES,
)


class TestStripeBillingManager:

    @pytest.fixture
    def stripe_mgr(self):
        return StripeBillingManager(api_key="sk_test_mock_12345")

    def test_tier_features_defined(self):
        assert SubscriptionTier.FREE in TIER_FEATURES
        assert SubscriptionTier.PROFESSIONAL in TIER_FEATURES
        assert SubscriptionTier.ENTERPRISE in TIER_FEATURES

        prof = TIER_FEATURES[SubscriptionTier.PROFESSIONAL]
        assert prof["price_eur_monthly"] == 99.0
        assert prof["limits"]["processed_statements"] == 1000

    def test_create_customer_mock(self, stripe_mgr):
        customer_id = stripe_mgr.create_customer("t_test1", "Bulgarian Express Ltd", "admin@express.bg")
        assert customer_id.startswith("cus_")

    def test_create_checkout_session(self, stripe_mgr):
        session = stripe_mgr.create_checkout_session(
            tenant_id="t_test1",
            stripe_customer_id="cus_123",
            tier=SubscriptionTier.PROFESSIONAL,
        )
        assert "session_id" in session
        assert "url" in session
        assert session["tier"] == "PROFESSIONAL"

    def test_create_portal_session(self, stripe_mgr):
        portal_url = stripe_mgr.create_portal_session("cus_123")
        assert portal_url.startswith("http")

    def test_cancel_subscription(self, stripe_mgr):
        res = stripe_mgr.cancel_subscription("sub_123", at_period_end=True)
        assert res["subscription_id"] == "sub_123"
        assert res["status"] == "CANCELED"

    def test_update_subscription_plan(self, stripe_mgr):
        res = stripe_mgr.update_subscription_plan("sub_123", SubscriptionTier.ENTERPRISE)
        assert res["subscription_id"] == "sub_123"
        assert res["tier"] == "ENTERPRISE"

    def test_verify_webhook_signature_mock(self, stripe_mgr):
        payload = b'{"id": "evt_test1", "type": "invoice.paid"}'
        event = stripe_mgr.verify_webhook_signature(payload, sig_header="t=123,v1=sig")
        assert event["id"] == "evt_test1"
        assert event["type"] == "invoice.paid"
