"""
Unit & Integration Tests for Usage Metering Engine & Quota Enforcement (M75).
"""

import pytest
from src.billing.metering_engine import MeteringEngine, MetricType, QuotaExceededError
from src.billing.stripe_client import SubscriptionTier


class TestMeteringEngine:

    @pytest.fixture
    def metering(self, tmp_path):
        db_file = str(tmp_path / "test_metering.db")
        return MeteringEngine(db_path=db_file)

    def test_record_usage(self, metering):
        total = metering.record_usage("t_test", MetricType.PROCESSED_STATEMENTS, count=5)
        assert total == 5

        total2 = metering.record_usage("t_test", MetricType.PROCESSED_STATEMENTS, count=10)
        assert total2 == 15

    def test_check_quota_free_tier(self, metering):
        allowed, current, limit, warning = metering.check_quota(
            tenant_id="t_free",
            metric=MetricType.PROCESSED_STATEMENTS,
            tier=SubscriptionTier.FREE,
            count=10,
        )
        assert allowed is True
        assert limit == 50
        assert warning == "NORMAL"

        metering.record_usage("t_free", MetricType.PROCESSED_STATEMENTS, count=45)
        allowed, current, limit, warning = metering.check_quota(
            tenant_id="t_free",
            metric=MetricType.PROCESSED_STATEMENTS,
            tier=SubscriptionTier.FREE,
            count=1,
        )
        assert allowed is True
        assert warning == "WARNING"

        metering.record_usage("t_free", MetricType.PROCESSED_STATEMENTS, count=5)
        allowed, current, limit, warning = metering.check_quota(
            tenant_id="t_free",
            metric=MetricType.PROCESSED_STATEMENTS,
            tier=SubscriptionTier.FREE,
            count=1,
        )
        assert allowed is False
        assert warning == "EXCEEDED"

    def test_enforce_quota_raises_error(self, metering):
        metering.record_usage("t_free2", MetricType.AI_INFERENCE_QUERIES, count=20)
        with pytest.raises(QuotaExceededError, match="Quota exceeded for tenant"):
            metering.enforce_quota(
                tenant_id="t_free2",
                metric=MetricType.AI_INFERENCE_QUERIES,
                tier=SubscriptionTier.FREE,
                count=1,
            )

    def test_get_tenant_usage_report(self, metering):
        metering.record_usage("t_report", MetricType.API_CALLS, count=50)
        report = metering.get_tenant_usage("t_report", tier=SubscriptionTier.FREE)
        assert report["tenant_id"] == "t_report"
        assert report["metrics"]["api_calls"]["current"] == 50
        assert report["metrics"]["api_calls"]["limit"] == 100
        assert report["metrics"]["api_calls"]["percentage"] == 50.0

    def test_reset_billing_cycle_usage(self, metering):
        metering.record_usage("t_reset", MetricType.PROCESSED_STATEMENTS, count=30)
        report1 = metering.get_tenant_usage("t_reset", tier=SubscriptionTier.FREE)
        assert report1["metrics"]["processed_statements"]["current"] == 30

        metering.reset_billing_cycle_usage("t_reset")
        report2 = metering.get_tenant_usage("t_reset", tier=SubscriptionTier.FREE)
        assert report2["metrics"]["processed_statements"]["current"] == 0
