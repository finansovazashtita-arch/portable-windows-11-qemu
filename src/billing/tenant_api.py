"""
Multi-Tenant REST API & Billing Endpoint Handler Module (M75).

Provides HTTP request routing and JSON payload processing for:
- Tenant CRUD & Provisioning (/api/v1/tenants)
- Usage & Quota Monitoring (/api/v1/tenants/{id}/usage)
- Stripe Checkout & Customer Portal (/api/v1/billing/checkout-session, /portal-session)
- Stripe Webhook Execution (/api/v1/billing/webhooks/stripe)
- GDPR Article 17 Erasure Requests (/api/v1/tenants/{id}/gdpr-erasure)
"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from src.billing.stripe_client import (
    StripeBillingManager,
    SubscriptionStatus,
    SubscriptionTier,
    TIER_FEATURES,
)
from src.billing.tenant_manager import TenantManager
from src.billing.metering_engine import MeteringEngine, MetricType
from src.billing.gdpr_compliance import GDPRComplianceManager
from src.billing.webhook_handler import StripeWebhookHandler

logger = logging.getLogger("tenant_api")


class TenantAPIHandler:
    """Dispatches HTTP requests for tenant provisioning, usage metering, and Stripe billing."""

    def __init__(self, db_path: str = "data/finansprotect_multitenant.db"):
        self.db_path = db_path
        self.stripe_manager = StripeBillingManager()
        self.tenant_manager = TenantManager(db_path=db_path, stripe_manager=self.stripe_manager)
        self.metering_engine = MeteringEngine(db_path=db_path)
        self.gdpr_manager = GDPRComplianceManager(
            schema_manager=self.tenant_manager.schema_manager,
            metering_engine=self.metering_engine,
            db_path=db_path,
        )
        self.webhook_handler = StripeWebhookHandler(
            tenant_manager=self.tenant_manager,
            stripe_manager=self.stripe_manager,
            metering_engine=self.metering_engine,
            db_path=db_path,
        )

    def handle_get(self, path: str, query_params: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
        """Handle GET requests for tenant management and usage endpoints."""
        query_params = query_params or {}

        # 1. GET /api/v1/tenants
        if path in ("/api/v1/tenants", "/api/tenants"):
            tier_filter = query_params.get("tier")
            status_filter = query_params.get("status")
            search = query_params.get("search")
            limit = int(query_params.get("limit", "50"))
            offset = int(query_params.get("offset", "0"))

            tier_enum = SubscriptionTier(tier_filter) if tier_filter and tier_filter in SubscriptionTier.__members__ else None
            status_enum = SubscriptionStatus(status_filter) if status_filter and status_filter in SubscriptionStatus.__members__ else None

            tenants, total = self.tenant_manager.list_tenants(
                tier=tier_enum, status=status_enum, search=search, limit=limit, offset=offset
            )

            return 200, {
                "success": True,
                "total": total,
                "limit": limit,
                "offset": offset,
                "tenants": [t.to_dict() for t in tenants],
            }

        # 2. GET /api/v1/tenants/tiers
        elif path in ("/api/v1/tenants/tiers", "/api/tenants/tiers", "/api/v1/billing/tiers"):
            tiers_data = {}
            for t, info in TIER_FEATURES.items():
                tiers_data[t.value] = info
            return 200, {"success": True, "tiers": tiers_data}

        # 3. GET /api/v1/tenants/{tenant_id}
        elif path.startswith("/api/v1/tenants/") and not path.endswith("/usage"):
            tenant_id = path.split("/")[-1]
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}

            schema_info = self.tenant_manager.schema_manager.get_schema_info(tenant_id)
            usage_report = self.metering_engine.get_tenant_usage(tenant_id, tenant.tier)

            return 200, {
                "success": True,
                "tenant": tenant.to_dict(),
                "schema": schema_info,
                "usage": usage_report,
            }

        # 4. GET /api/v1/tenants/{tenant_id}/usage
        elif path.startswith("/api/v1/tenants/") and path.endswith("/usage"):
            parts = path.split("/")
            tenant_id = parts[-2]
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}

            usage_report = self.metering_engine.get_tenant_usage(tenant_id, tenant.tier)
            return 200, {"success": True, "usage": usage_report}

        return 404, {"error": "NOT_FOUND", "message": f"Endpoint GET {path} not found."}

    def handle_post(
        self, path: str, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """Handle POST requests for tenant provisioning, billing, and webhooks."""
        headers = headers or {}

        # 1. POST /api/v1/tenants -> Provision new tenant
        if path in ("/api/v1/tenants", "/api/tenants"):
            company_name = body.get("company_name")
            eik = body.get("eik")
            email = body.get("contact_email")
            tier_str = body.get("tier", "FREE")

            if not company_name or not eik or not email:
                return 400, {
                    "error": "BAD_REQUEST",
                    "message": "Missing required fields: company_name, eik, contact_email.",
                }

            try:
                tier = SubscriptionTier(tier_str)
            except ValueError:
                tier = SubscriptionTier.FREE

            try:
                tenant = self.tenant_manager.create_tenant(
                    company_name=company_name,
                    eik=eik,
                    contact_email=email,
                    tier=tier,
                    metadata=body.get("metadata"),
                )
                return 201, {"success": True, "tenant": tenant.to_dict()}
            except ValueError as ve:
                return 400, {"error": "INVALID_EIK", "message": str(ve)}
            except Exception as e:
                logger.error(f"Tenant creation failed: {e}")
                return 500, {"error": "INTERNAL_ERROR", "message": str(e)}

        # 2. POST /api/v1/tenants/{tenant_id}/subscription -> Update subscription
        elif path.startswith("/api/v1/tenants/") and path.endswith("/subscription"):
            parts = path.split("/")
            tenant_id = parts[-2]
            tier_str = body.get("tier")
            status_str = body.get("status", "ACTIVE")

            if not tier_str:
                return 400, {"error": "BAD_REQUEST", "message": "Missing required field: tier."}

            try:
                tier = SubscriptionTier(tier_str)
                status = SubscriptionStatus(status_str)
            except ValueError:
                return 400, {"error": "BAD_REQUEST", "message": "Invalid tier or status enum value."}

            updated = self.tenant_manager.update_subscription(
                tenant_id=tenant_id,
                tier=tier,
                stripe_subscription_id=body.get("stripe_subscription_id"),
                status=status,
            )
            if not updated:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}

            return 200, {"success": True, "tenant": updated.to_dict()}

        # 3. POST /api/v1/tenants/{tenant_id}/gdpr-erasure -> Trigger Art. 17 data erasure
        elif path.startswith("/api/v1/tenants/") and path.endswith("/gdpr-erasure"):
            parts = path.split("/")
            tenant_id = parts[-2]
            requested_by = body.get("requested_by", "ADMIN")
            reason = body.get("reason", "GDPR_ART17_REQUEST")

            tenant = self.tenant_manager.get_tenant(tenant_id)
            if not tenant:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}

            cert = self.gdpr_manager.execute_right_to_erasure(tenant_id, requested_by=requested_by, reason=reason)
            self.tenant_manager.delete_tenant(tenant_id, purge_data=False)

            return 200, {"success": True, "erasure_certificate": cert.to_dict()}

        # 4. POST /api/v1/billing/checkout-session
        elif path in ("/api/v1/billing/checkout-session", "/api/billing/checkout-session"):
            tenant_id = body.get("tenant_id")
            tier_str = body.get("tier", "PROFESSIONAL")
            success_url = body.get("success_url", "https://app.finansprotect.bg/billing/success")
            cancel_url = body.get("cancel_url", "https://app.finansprotect.bg/billing/cancel")

            tenant = self.tenant_manager.get_tenant(tenant_id) if tenant_id else None
            customer_id = tenant.stripe_customer_id if (tenant and tenant.stripe_customer_id) else "cus_guest"


            try:
                tier = SubscriptionTier(tier_str)
            except ValueError:
                tier = SubscriptionTier.PROFESSIONAL

            customer_id = tenant.stripe_customer_id if tenant else "cus_guest"
            session_info = self.stripe_manager.create_checkout_session(
                tenant_id=tenant_id or "guest",
                stripe_customer_id=customer_id,
                tier=tier,
                success_url=success_url,
                cancel_url=cancel_url,
            )

            return 200, {"success": True, "checkout_session": session_info}

        # 5. POST /api/v1/billing/portal-session
        elif path in ("/api/v1/billing/portal-session", "/api/billing/portal-session"):
            tenant_id = body.get("tenant_id")
            tenant = self.tenant_manager.get_tenant(tenant_id) if tenant_id else None

            if not tenant or not tenant.stripe_customer_id:
                return 400, {"error": "BAD_REQUEST", "message": "Tenant not found or has no Stripe Customer record."}

            portal_url = self.stripe_manager.create_portal_session(tenant.stripe_customer_id)
            return 200, {"success": True, "portal_url": portal_url}

        # 6. POST /api/v1/billing/webhooks/stripe
        elif path in ("/api/v1/billing/webhooks/stripe", "/api/billing/webhooks/stripe"):
            raw_payload = body.get("_raw_bytes")
            if not raw_payload:
                raw_payload = json.dumps(body).encode("utf-8")

            sig_header = headers.get("Stripe-Signature", headers.get("stripe-signature", "mock_sig_123"))

            try:
                result = self.webhook_handler.process_webhook_payload(raw_payload, sig_header)
                return 200, result
            except ValueError as ve:
                return 400, {"error": "INVALID_SIGNATURE", "message": str(ve)}
            except Exception as e:
                logger.error(f"Webhook processing error: {e}")
                return 500, {"error": "INTERNAL_ERROR", "message": str(e)}

        return 404, {"error": "NOT_FOUND", "message": f"Endpoint POST {path} not found."}

    def handle_put(self, path: str, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Handle PUT requests for updating tenant details."""
        if path.startswith("/api/v1/tenants/"):
            tenant_id = path.split("/")[-1]
            updated = self.tenant_manager.update_tenant(tenant_id, **body)
            if not updated:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}
            return 200, {"success": True, "tenant": updated.to_dict()}

        return 404, {"error": "NOT_FOUND", "message": f"Endpoint PUT {path} not found."}

    def handle_delete(self, path: str, query_params: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any]]:
        """Handle DELETE requests for tenant termination."""
        query_params = query_params or {}
        if path.startswith("/api/v1/tenants/"):
            tenant_id = path.split("/")[-1]
            purge = query_params.get("purge", "true").lower() == "true"
            success = self.tenant_manager.delete_tenant(tenant_id, purge_data=purge)
            if not success:
                return 404, {"error": "NOT_FOUND", "message": f"Tenant '{tenant_id}' not found."}
            return 200, {"success": True, "message": f"Tenant '{tenant_id}' deleted.", "purged_data": purge}

        return 404, {"error": "NOT_FOUND", "message": f"Endpoint DELETE {path} not found."}
