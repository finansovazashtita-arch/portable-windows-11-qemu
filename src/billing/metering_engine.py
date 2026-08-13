"""
Usage Metering & Quota Enforcement Engine Module (M75).

Tracks real-time consumption across metered dimensions:
- Processed Bank/Tax Statements
- REST API Calls
- AI Inference Queries (OCR/LLM)
- Storage Space (MB)

Enforces subscription tier limits and provides quota alert triggers.
"""

import dataclasses
import enum
import logging
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.billing.stripe_client import SubscriptionTier, TIER_FEATURES

logger = logging.getLogger("metering_engine")


class MetricType(str, enum.Enum):
    PROCESSED_STATEMENTS = "processed_statements"
    API_CALLS = "api_calls"
    AI_INFERENCE_QUERIES = "ai_inference_queries"
    STORAGE_MB = "storage_mb"


@dataclasses.dataclass
class UsageRecord:
    tenant_id: str
    metric: MetricType
    count: int
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = dataclasses.asdict(self)
        res["metric"] = self.metric.value if isinstance(self.metric, MetricType) else str(self.metric)
        return res



class QuotaExceededError(Exception):
    """Raised when tenant attempts to consume resources beyond their subscription tier quota."""

    def __init__(self, tenant_id: str, metric: str, current: int, limit: int):
        self.tenant_id = tenant_id
        self.metric = metric
        self.current = current
        self.limit = limit
        super().__init__(
            f"Quota exceeded for tenant '{tenant_id}' on metric '{metric}': current usage {current}/{limit}."
        )


class MeteringEngine:
    """Thread-safe usage metering engine for recording usage and enforcing tier quotas."""

    def __init__(self, db_path: str = "data/finansprotect_multitenant.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS usage_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        count INTEGER NOT NULL,
                        timestamp REAL NOT NULL,
                        metadata TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS billing_cycle_usage (
                        tenant_id TEXT NOT NULL,
                        metric TEXT NOT NULL,
                        current_count INTEGER NOT NULL DEFAULT 0,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (tenant_id, metric)
                    )
                """)
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_records(tenant_id, metric, timestamp)"
                )
                conn.commit()
            finally:
                conn.close()

    def record_usage(
        self,
        tenant_id: str,
        metric: MetricType,
        count: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record resource consumption event for a tenant.
        Returns the updated cumulative count for the current billing cycle.
        """
        import json

        metric_name = metric.value if isinstance(metric, MetricType) else str(metric)
        now = time.time()
        meta_str = json.dumps(metadata) if metadata else None

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                # 1. Append log record
                cursor.execute(
                    "INSERT INTO usage_records (tenant_id, metric, count, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                    (tenant_id, metric_name, count, now, meta_str),
                )

                # 2. Update cumulative billing cycle counter
                cursor.execute(
                    """
                    INSERT INTO billing_cycle_usage (tenant_id, metric, current_count, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(tenant_id, metric) DO UPDATE SET
                        current_count = current_count + excluded.current_count,
                        updated_at = excluded.updated_at
                """,
                    (tenant_id, metric_name, count, now),
                )

                cursor.execute(
                    "SELECT current_count FROM billing_cycle_usage WHERE tenant_id = ? AND metric = ?",
                    (tenant_id, metric_name),
                )
                row = cursor.fetchone()
                total = row[0] if row else count
                conn.commit()
                return total
            finally:
                conn.close()

    def check_quota(
        self,
        tenant_id: str,
        metric: MetricType,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        count: int = 1,
    ) -> Tuple[bool, int, int, str]:
        """
        Check if an operation incrementing `metric` by `count` is permitted under `tier` limits.
        Returns: (allowed: bool, current_count: int, quota_limit: int, warning_level: str)
        warning_level: 'NORMAL', 'WARNING' (>=80%), 'EXCEEDED' (>=100%)
        """
        metric_name = metric.value if isinstance(metric, MetricType) else str(metric)
        limits = TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])["limits"]
        quota_limit = limits.get(metric_name, 100)

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT current_count FROM billing_cycle_usage WHERE tenant_id = ? AND metric = ?",
                    (tenant_id, metric_name),
                )
                row = cursor.fetchone()
                current = row[0] if row else 0
            finally:
                conn.close()

        projected = current + count
        allowed = projected <= quota_limit

        percentage = (current / quota_limit) * 100.0 if quota_limit > 0 else 0.0
        if percentage >= 100.0 or not allowed:
            warning_level = "EXCEEDED"
        elif percentage >= 80.0:
            warning_level = "WARNING"
        else:
            warning_level = "NORMAL"

        return allowed, current, quota_limit, warning_level

    def enforce_quota(
        self,
        tenant_id: str,
        metric: MetricType,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        count: int = 1,
    ):
        """Enforces quota check, raising QuotaExceededError if limit is breached."""
        allowed, current, limit, warning = self.check_quota(tenant_id, metric, tier, count)
        if not allowed:
            logger.warning(
                f"🚨 QUOTA BLOCKED: Tenant '{tenant_id}' reached limit for {metric.value} ({current}/{limit})."
            )
            raise QuotaExceededError(tenant_id, metric.value, current, limit)

    def get_tenant_usage(
        self,
        tenant_id: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
    ) -> Dict[str, Any]:
        """Get complete usage report vs limits for all metrics."""
        tier_info = TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.FREE])
        limits = tier_info["limits"]

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT metric, current_count FROM billing_cycle_usage WHERE tenant_id = ?",
                    (tenant_id,),
                )
                rows = cursor.fetchall()
                usage_map = {r[0]: r[1] for r in rows}
            finally:
                conn.close()

        metrics_report = {}
        for m in MetricType:
            m_key = m.value
            current = usage_map.get(m_key, 0)
            limit = limits.get(m_key, 100)
            pct = round((current / limit) * 100.0, 1) if limit > 0 else 0.0
            status = "EXCEEDED" if current >= limit else ("WARNING" if pct >= 80.0 else "OK")

            metrics_report[m_key] = {
                "current": current,
                "limit": limit,
                "percentage": pct,
                "status": status,
            }

        return {
            "tenant_id": tenant_id,
            "tier": tier.value,
            "tier_name": tier_info["name"],
            "metrics": metrics_report,
            "timestamp": time.time(),
        }

    def reset_billing_cycle_usage(self, tenant_id: str) -> bool:
        """Reset billing cycle usage counters (e.g., upon monthly subscription renewal)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM billing_cycle_usage WHERE tenant_id = ?", (tenant_id,))
                conn.commit()
                logger.info(f"Reset billing cycle usage for tenant '{tenant_id}'.")
                return True
            finally:
                conn.close()
