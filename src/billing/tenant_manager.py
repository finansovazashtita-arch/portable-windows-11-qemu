"""
Multi-Tenant Lifecycle & Provisioning Management Module (M75).

Manages:
- Tenant onboarding & CRUD operations
- Dynamic schema provisioning via SchemaManager
- Stripe customer synchronization
- Subscription status updates
- Tenant pagination and search
"""

import dataclasses
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from src.billing.stripe_client import (
    StripeBillingManager,
    SubscriptionStatus,
    SubscriptionTier,
)
from src.billing.schema_manager import SchemaManager
from src.billing.metering_engine import MeteringEngine

logger = logging.getLogger("tenant_manager")


@dataclasses.dataclass
class TenantRecord:
    tenant_id: str
    company_name: str
    eik: str
    contact_email: str
    db_schema: str
    tier: SubscriptionTier
    subscription_status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = dataclasses.asdict(self)
        res["tier"] = self.tier.value if isinstance(self.tier, SubscriptionTier) else str(self.tier)
        res["subscription_status"] = (
            self.subscription_status.value
            if isinstance(self.subscription_status, SubscriptionStatus)
            else str(self.subscription_status)
        )
        return res


class TenantManager:
    """Thread-safe tenant manager responsible for lifecycle, database schema isolation, and billing state."""

    def __init__(
        self,
        db_path: str = "data/finansprotect_multitenant.db",
        stripe_manager: Optional[StripeBillingManager] = None,
        schema_manager: Optional[SchemaManager] = None,
        metering_engine: Optional[MeteringEngine] = None,
    ):
        self.db_path = db_path
        self.stripe_manager = stripe_manager or StripeBillingManager()
        self.schema_manager = schema_manager or SchemaManager(db_path=db_path)
        self.metering_engine = metering_engine or MeteringEngine(db_path=db_path)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tenants (
                        tenant_id TEXT PRIMARY KEY,
                        company_name TEXT NOT NULL,
                        eik TEXT NOT NULL,
                        contact_email TEXT NOT NULL,
                        db_schema TEXT UNIQUE NOT NULL,
                        tier TEXT NOT NULL,
                        subscription_status TEXT NOT NULL,
                        stripe_customer_id TEXT,
                        stripe_subscription_id TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        metadata_json TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenants_eik ON tenants(eik)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenants_stripe ON tenants(stripe_customer_id)")
                conn.commit()
            finally:
                conn.close()

    def create_tenant(
        self,
        company_name: str,
        eik: str,
        contact_email: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TenantRecord:
        """
        Provision new tenant with isolated DB schema and Stripe customer record.
        """
        # Validate EIK/BULSTAT format (9 or 13 digits)
        eik_clean = re.sub(r"\D", "", eik)
        if not eik_clean or len(eik_clean) not in (9, 10, 13):
            raise ValueError(f"Invalid Bulgarian EIK/UIC number: '{eik}'. Must be 9, 10, or 13 digits.")

        # Generate unique tenant ID
        random_suffix = secrets.token_hex(4)
        tenant_id = f"t_{eik_clean[:9]}_{random_suffix}"
        now = time.time()

        # 1. Provision isolated schema
        db_schema = self.schema_manager.provision_tenant_schema(tenant_id)

        # 2. Create Stripe customer record
        stripe_customer_id = self.stripe_manager.create_customer(tenant_id, company_name, contact_email)

        initial_status = (
            SubscriptionStatus.ACTIVE if tier == SubscriptionTier.FREE else SubscriptionStatus.TRIALING
        )

        record = TenantRecord(
            tenant_id=tenant_id,
            company_name=company_name,
            eik=eik_clean,
            contact_email=contact_email,
            db_schema=db_schema,
            tier=tier,
            subscription_status=initial_status,
            stripe_customer_id=stripe_customer_id,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO tenants (
                        tenant_id, company_name, eik, contact_email, db_schema,
                        tier, subscription_status, stripe_customer_id, stripe_subscription_id,
                        created_at, updated_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record.tenant_id,
                        record.company_name,
                        record.eik,
                        record.contact_email,
                        record.db_schema,
                        record.tier.value,
                        record.subscription_status.value,
                        record.stripe_customer_id,
                        record.stripe_subscription_id,
                        record.created_at,
                        record.updated_at,
                        json.dumps(record.metadata),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        logger.info(f"Successfully provisioned tenant '{tenant_id}' ({company_name}) on tier '{tier.value}'.")
        return record

    def get_tenant(self, tenant_id: str) -> Optional[TenantRecord]:
        """Retrieve tenant record by tenant_id."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_tenant(row)
            finally:
                conn.close()

    def get_tenant_by_stripe_customer(self, stripe_customer_id: str) -> Optional[TenantRecord]:
        """Retrieve tenant record by Stripe Customer ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tenants WHERE stripe_customer_id = ?", (stripe_customer_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self._row_to_tenant(row)
            finally:
                conn.close()

    def list_tenants(
        self,
        tier: Optional[SubscriptionTier] = None,
        status: Optional[SubscriptionStatus] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[TenantRecord], int]:
        """
        List tenants with pagination, tier filter, status filter, and search.
        Returns: (List[TenantRecord], total_count)
        """
        conditions = []
        params: List[Any] = []

        if tier:
            conditions.append("tier = ?")
            params.append(tier.value if isinstance(tier, SubscriptionTier) else str(tier))

        if status:
            conditions.append("subscription_status = ?")
            params.append(status.value if isinstance(status, SubscriptionStatus) else str(status))

        if search:
            conditions.append("(company_name LIKE ? OR eik LIKE ? OR contact_email LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                # Count total matching
                cursor.execute(f"SELECT COUNT(*) FROM tenants {where_clause}", params)
                total_count = cursor.fetchone()[0]

                # Fetch page
                query = f"SELECT * FROM tenants {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
                cursor.execute(query, params + [limit, offset])
                rows = cursor.fetchall()
                tenants = [self._row_to_tenant(r) for r in rows]
                return tenants, total_count
            finally:
                conn.close()

    def update_tenant(self, tenant_id: str, **kwargs) -> Optional[TenantRecord]:
        """Update metadata, company name, contact email, or tier."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        now = time.time()
        allowed_fields = {"company_name", "contact_email", "tier", "subscription_status", "stripe_subscription_id"}

        updates = []
        params = []
        for k, v in kwargs.items():
            if k in allowed_fields and v is not None:
                val_str = v.value if isinstance(v, (SubscriptionTier, SubscriptionStatus)) else v
                updates.append(f"{k} = ?")
                params.append(val_str)

        if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
            new_meta = {**tenant.metadata, **kwargs["metadata"]}
            updates.append("metadata_json = ?")
            params.append(json.dumps(new_meta))

        if not updates:
            return tenant

        updates.append("updated_at = ?")
        params.append(now)
        params.append(tenant_id)

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = ?", params)
                conn.commit()
            finally:
                conn.close()

        return self.get_tenant(tenant_id)

    def update_subscription(
        self,
        tenant_id: str,
        tier: SubscriptionTier,
        stripe_subscription_id: Optional[str] = None,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    ) -> Optional[TenantRecord]:
        """Update tenant subscription tier and Stripe subscription binding."""
        kwargs: Dict[str, Any] = {
            "tier": tier,
            "subscription_status": status,
        }
        if stripe_subscription_id:
            kwargs["stripe_subscription_id"] = stripe_subscription_id

        logger.info(f"Updated subscription for tenant '{tenant_id}' -> Tier: {tier.value}, Status: {status.value}")
        return self.update_tenant(tenant_id, **kwargs)

    def delete_tenant(self, tenant_id: str, purge_data: bool = True) -> bool:
        """Delete tenant record and optionally purge schema and data."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False

        if purge_data:
            from src.billing.gdpr_compliance import GDPRComplianceManager

            gdpr_mgr = GDPRComplianceManager(
                schema_manager=self.schema_manager,
                metering_engine=self.metering_engine,
                db_path=self.db_path,
            )
            gdpr_mgr.execute_right_to_erasure(tenant_id, requested_by="TENANT_MANAGER", reason="TENANT_DELETION")

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
                conn.commit()
                return True
            finally:
                conn.close()

    def _row_to_tenant(self, row: Tuple[Any, ...]) -> TenantRecord:
        meta = json.loads(row[11]) if row[11] else {}
        return TenantRecord(
            tenant_id=row[0],
            company_name=row[1],
            eik=row[2],
            contact_email=row[3],
            db_schema=row[4],
            tier=SubscriptionTier(row[5]),
            subscription_status=SubscriptionStatus(row[6]),
            stripe_customer_id=row[7],
            stripe_subscription_id=row[8],
            created_at=row[9],
            updated_at=row[10],
            metadata=meta,
        )
