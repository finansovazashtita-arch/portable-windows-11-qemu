"""
Webhook-Driven Billing Event Processor Module (M75).

Processes Stripe webhook events:
- invoice.paid: subscription renewal & usage counter reset
- invoice.payment_failed: status update to PAST_DUE & alert notification
- customer.subscription.created: binding subscription ID to tenant
- customer.subscription.updated: dynamic tier upgrades & downgrades
- customer.subscription.deleted: status update to CANCELED & fallback to FREE

Includes replay protection & idempotency verification.
"""

import json
import logging
import sqlite3
import threading
import time
from typing import Any, Dict, Optional, Tuple

from src.billing.stripe_client import (
    StripeBillingManager,
    SubscriptionStatus,
    SubscriptionTier,
    TIER_FEATURES,
)
from src.billing.tenant_manager import TenantManager
from src.billing.metering_engine import MeteringEngine

logger = logging.getLogger("webhook_handler")


class StripeWebhookHandler:
    """Handles and dispatches Stripe webhooks with signature verification and idempotency protection."""

    def __init__(
        self,
        tenant_manager: Optional[TenantManager] = None,
        stripe_manager: Optional[StripeBillingManager] = None,
        metering_engine: Optional[MeteringEngine] = None,
        db_path: str = "data/finansprotect_multitenant.db",
    ):
        self.tenant_manager = tenant_manager or TenantManager(db_path=db_path)
        self.stripe_manager = stripe_manager or StripeBillingManager()
        self.metering_engine = metering_engine or MeteringEngine(db_path=db_path)
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_webhook_events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        processed_at REAL NOT NULL,
                        payload_summary TEXT
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def is_event_processed(self, event_id: str) -> bool:
        """Check if webhook event has already been processed (idempotency check)."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM processed_webhook_events WHERE event_id = ?", (event_id,))
                return cursor.fetchone() is not None
            finally:
                conn.close()

    def mark_event_processed(self, event_id: str, event_type: str, summary: str = ""):
        """Record processed webhook event ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO processed_webhook_events (event_id, event_type, processed_at, payload_summary) VALUES (?, ?, ?, ?)",
                    (event_id, event_type, time.time(), summary),
                )
                conn.commit()
            finally:
                conn.close()

    def process_webhook_payload(
        self, payload_bytes: bytes, sig_header: str, secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify Stripe signature, check idempotency, and dispatch webhook event.
        Returns response dictionary.
        """
        # 1. Signature Verification
        event = self.stripe_manager.verify_webhook_signature(payload_bytes, sig_header, secret)

        event_id = event.get("id") or event.get("event_id") or f"evt_{hash(payload_bytes)}"
        event_type = event.get("type", "unknown")
        data_obj = event.get("data", {}).get("object", {})

        # 2. Idempotency Check
        if self.is_event_processed(event_id):
            logger.info(f"Webhook event '{event_id}' ({event_type}) already processed. Skipping.")
            return {"status": "success", "processed": False, "reason": "duplicate_event", "event_id": event_id}

        # 3. Dispatch Event Handler
        success = False
        message = ""

        if event_type == "invoice.paid":
            success, message = self._handle_invoice_paid(data_obj)

        elif event_type == "invoice.payment_failed":
            success, message = self._handle_invoice_payment_failed(data_obj)

        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            success, message = self._handle_subscription_updated(data_obj)

        elif event_type == "customer.subscription.deleted":
            success, message = self._handle_subscription_deleted(data_obj)

        else:
            message = f"Unhandled event type '{event_type}' received."
            success = True

        # 4. Mark Event as Processed
        self.mark_event_processed(event_id, event_type, message)

        return {
            "status": "success" if success else "error",
            "processed": True,
            "event_type": event_type,
            "event_id": event_id,
            "message": message,
        }

    def _handle_invoice_paid(self, invoice_obj: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle invoice.paid event: reset billing cycle usage, mark active."""
        customer_id = invoice_obj.get("customer")
        if not customer_id:
            return False, "Missing customer ID in invoice payload"

        tenant = self.tenant_manager.get_tenant_by_stripe_customer(customer_id)
        if not tenant:
            return False, f"No tenant found for Stripe customer '{customer_id}'"

        # Reset usage for new billing cycle
        self.metering_engine.reset_billing_cycle_usage(tenant.tenant_id)
        self.tenant_manager.update_tenant(tenant.tenant_id, subscription_status=SubscriptionStatus.ACTIVE)

        msg = f"Invoice paid for tenant '{tenant.tenant_id}'. Billing usage reset, status set to ACTIVE."
        logger.info(msg)
        return True, msg

    def _handle_invoice_payment_failed(self, invoice_obj: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle invoice.payment_failed event: update status to PAST_DUE."""
        customer_id = invoice_obj.get("customer")
        if not customer_id:
            return False, "Missing customer ID in invoice payload"

        tenant = self.tenant_manager.get_tenant_by_stripe_customer(customer_id)
        if not tenant:
            return False, f"No tenant found for Stripe customer '{customer_id}'"

        self.tenant_manager.update_tenant(tenant.tenant_id, subscription_status=SubscriptionStatus.PAST_DUE)
        msg = f"Payment failed for tenant '{tenant.tenant_id}'. Status set to PAST_DUE."
        logger.warning(msg)
        return True, msg

    def _handle_subscription_updated(self, sub_obj: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle subscription creation or tier updates."""
        customer_id = sub_obj.get("customer")
        sub_id = sub_obj.get("id")
        sub_status = sub_obj.get("status", "active").upper()

        if not customer_id:
            return False, "Missing customer ID in subscription payload"

        tenant = self.tenant_manager.get_tenant_by_stripe_customer(customer_id)
        if not tenant:
            return False, f"No tenant found for Stripe customer '{customer_id}'"

        # Determine target tier from metadata or price item
        tier = SubscriptionTier.FREE
        metadata = sub_obj.get("metadata", {})
        if "tier" in metadata:
            try:
                tier = SubscriptionTier(metadata["tier"])
            except ValueError:
                pass
        else:
            # Match price ID if available
            items = sub_obj.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id")
                for t, info in TIER_FEATURES.items():
                    if info.get("stripe_price_id") == price_id:
                        tier = t
                        break

        status_enum = SubscriptionStatus.ACTIVE
        if sub_status in (s.value for s in SubscriptionStatus):
            status_enum = SubscriptionStatus(sub_status)

        self.tenant_manager.update_subscription(
            tenant_id=tenant.tenant_id,
            tier=tier,
            stripe_subscription_id=sub_id,
            status=status_enum,
        )

        msg = f"Subscription updated for tenant '{tenant.tenant_id}' -> Tier: {tier.value}, Status: {status_enum.value}"
        logger.info(msg)
        return True, msg

    def _handle_subscription_deleted(self, sub_obj: Dict[str, Any]) -> Tuple[bool, str]:
        """Handle subscription cancellation event."""
        customer_id = sub_obj.get("customer")
        if not customer_id:
            return False, "Missing customer ID in subscription payload"

        tenant = self.tenant_manager.get_tenant_by_stripe_customer(customer_id)
        if not tenant:
            return False, f"No tenant found for Stripe customer '{customer_id}'"

        self.tenant_manager.update_subscription(
            tenant_id=tenant.tenant_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.CANCELED,
        )

        msg = f"Subscription deleted for tenant '{tenant.tenant_id}'. Downgraded to FREE, status CANCELED."
        logger.info(msg)
        return True, msg
