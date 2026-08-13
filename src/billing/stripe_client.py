"""
Stripe Payment & Subscription Management Integration Module (M75).

Handles:
- Subscription tier definitions (FREE, PROFESSIONAL, ENTERPRISE)
- Stripe Customer, Checkout Session, and Portal Session creation
- Subscription lifecycle updates (upgrades, downgrades, cancellations)
- Webhook signature verification
- Mock/Offline fallback for testing and air-gapped environments
"""

import enum
import json
import logging
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("stripe_billing")

try:
    import stripe
    HAS_STRIPE_SDK = True
except ImportError:
    stripe = None
    HAS_STRIPE_SDK = False


class SubscriptionTier(str, enum.Enum):
    FREE = "FREE"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class SubscriptionStatus(str, enum.Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    TRIALING = "TRIALING"
    UNPAID = "UNPAID"


TIER_FEATURES: Dict[SubscriptionTier, Dict[str, Any]] = {
    SubscriptionTier.FREE: {
        "name": "Free Tier",
        "price_eur_monthly": 0.0,
        "stripe_price_id": "price_free_tier",
        "limits": {
            "processed_statements": 50,
            "api_calls": 100,
            "ai_inference_queries": 20,
            "storage_mb": 500,
            "max_users": 1,
        },
        "features": [
            "Basic OCR statement extraction",
            "Single tenant schema",
            "Community support",
            "Standard export formats (CSV/JSON)",
        ],
    },
    SubscriptionTier.PROFESSIONAL: {
        "name": "Professional Tier",
        "price_eur_monthly": 99.0,
        "stripe_price_id": "price_prof_monthly_99",
        "limits": {
            "processed_statements": 1000,
            "api_calls": 10000,
            "ai_inference_queries": 1000,
            "storage_mb": 10000,
            "max_users": 10,
        },
        "features": [
            "Advanced multi-bank OCR engine",
            "Automated double-entry reconciliation",
            "Delta Pro & Microinvest sync",
            "Priority support (24h response)",
            "10 team accounts",
        ],
    },
    SubscriptionTier.ENTERPRISE: {
        "name": "Enterprise Tier",
        "price_eur_monthly": 499.0,
        "stripe_price_id": "price_ent_monthly_499",
        "limits": {
            "processed_statements": 1000000,
            "api_calls": 10000000,
            "ai_inference_queries": 50000,
            "storage_mb": 100000,
            "max_users": 999,
        },
        "features": [
            "Unlimited processing & statement ingestion",
            "Dedicated PostgreSQL schema & custom database",
            "PQC mesh replication & zero-trust compliance",
            "GDPR automated Art. 17 right-to-erasure",
            "Dedicated 24/7 SLA & account manager",
        ],
    },
}


class StripeBillingManager:
    """Manages interactions with Stripe API for customer accounts, subscriptions, and webhooks."""

    def __init__(self, api_key: Optional[str] = None, webhook_secret: Optional[str] = None):
        self.api_key = api_key or os.environ.get("STRIPE_SECRET_KEY") or "sk_test_finansprotect_mock_key"
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET") or "whsec_mock_secret_key"
        self.is_mock_mode = not HAS_STRIPE_SDK or self.api_key.startswith("sk_test_mock") or "mock" in self.api_key.lower()

        if HAS_STRIPE_SDK and not self.is_mock_mode:
            stripe.api_key = self.api_key
            logger.info("Stripe SDK initialized with live/test key.")
        else:
            logger.info("Stripe Manager running in offline/mock mode.")

    def create_customer(self, tenant_id: str, company_name: str, email: str) -> str:
        """Create a Stripe Customer record or mock customer ID."""
        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                customer = stripe.Customer.create(
                    email=email,
                    name=company_name,
                    metadata={"tenant_id": tenant_id, "platform": "FinansProtect"},
                )
                return customer.id
            except Exception as e:
                logger.error(f"Stripe API error creating customer: {e}")
                raise RuntimeError(f"Stripe Customer creation failed: {e}")

        # Mock fallback
        mock_id = f"cus_{secrets.token_hex(8)}"
        logger.info(f"[MOCK] Created Stripe customer '{mock_id}' for tenant '{tenant_id}' ({company_name}).")
        return mock_id

    def create_checkout_session(
        self,
        tenant_id: str,
        stripe_customer_id: str,
        tier: SubscriptionTier,
        success_url: str = "https://app.finansprotect.bg/billing/success",
        cancel_url: str = "https://app.finansprotect.bg/billing/cancel",
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session for subscription purchase."""
        price_id = TIER_FEATURES.get(tier, {}).get("stripe_price_id", "price_free_tier")

        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                session = stripe.checkout.Session.create(
                    customer=stripe_customer_id,
                    payment_method_types=["card"],
                    line_items=[{"price": price_id, "quantity": 1}],
                    mode="subscription",
                    success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=cancel_url,
                    metadata={"tenant_id": tenant_id, "tier": tier.value},
                )
                return {
                    "session_id": session.id,
                    "url": session.url,
                    "stripe_customer_id": stripe_customer_id,
                    "tier": tier.value,
                }
            except Exception as e:
                logger.error(f"Stripe API error creating checkout session: {e}")
                raise RuntimeError(f"Checkout Session creation failed: {e}")

        # Mock fallback
        session_id = f"cs_test_{secrets.token_hex(12)}"
        mock_url = f"https://checkout.stripe.com/c/pay/{session_id}"
        return {
            "session_id": session_id,
            "url": mock_url,
            "stripe_customer_id": stripe_customer_id,
            "tier": tier.value,
            "mock": True,
        }

    def create_portal_session(self, stripe_customer_id: str, return_url: str = "https://app.finansprotect.bg/billing") -> str:
        """Create a Customer Portal session URL for subscription management."""
        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                session = stripe.billing_portal.Session.create(
                    customer=stripe_customer_id,
                    return_url=return_url,
                )
                return session.url
            except Exception as e:
                logger.error(f"Stripe API error creating portal session: {e}")
                raise RuntimeError(f"Portal Session creation failed: {e}")

        # Mock fallback
        return f"https://billing.stripe.com/p/session/test_{secrets.token_hex(10)}"

    def cancel_subscription(self, stripe_subscription_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel an active subscription."""
        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                if at_period_end:
                    sub = stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
                else:
                    sub = stripe.Subscription.delete(stripe_subscription_id)
                return {"subscription_id": sub.id, "status": sub.status, "cancel_at_period_end": sub.cancel_at_period_end}
            except Exception as e:
                logger.error(f"Stripe API error canceling subscription: {e}")
                raise RuntimeError(f"Subscription cancellation failed: {e}")

        return {
            "subscription_id": stripe_subscription_id,
            "status": SubscriptionStatus.CANCELED.value,
            "cancel_at_period_end": at_period_end,
            "mock": True,
        }

    def update_subscription_plan(self, stripe_subscription_id: str, new_tier: SubscriptionTier) -> Dict[str, Any]:
        """Update subscription to a new tier (upgrade or downgrade)."""
        new_price_id = TIER_FEATURES.get(new_tier, {}).get("stripe_price_id", "price_free_tier")

        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                sub = stripe.Subscription.retrieve(stripe_subscription_id)
                updated_sub = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=False,
                    items=[{
                        "id": sub["items"]["data"][0].id,
                        "price": new_price_id,
                    }],
                    proration_behavior="always_invoice",
                )
                return {"subscription_id": updated_sub.id, "status": updated_sub.status, "tier": new_tier.value}
            except Exception as e:
                logger.error(f"Stripe API error updating subscription: {e}")
                raise RuntimeError(f"Subscription update failed: {e}")

        return {
            "subscription_id": stripe_subscription_id,
            "status": SubscriptionStatus.ACTIVE.value,
            "tier": new_tier.value,
            "mock": True,
        }

    def verify_webhook_signature(self, payload: bytes, sig_header: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """Verify Stripe webhook signature and construct event object."""
        webhook_secret = secret or self.webhook_secret

        if not self.is_mock_mode and HAS_STRIPE_SDK:
            try:
                event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
                return json.loads(json.dumps(event))
            except Exception as e:
                logger.error(f"Stripe Webhook Signature Verification Error: {e}")
                raise ValueError(f"Invalid webhook signature: {e}")

        # Mock fallback verification
        try:
            event_data = json.loads(payload.decode("utf-8"))
            if not sig_header or len(sig_header) < 5:
                raise ValueError("Missing or invalid Stripe-Signature header")
            return event_data
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON payload in webhook")
