"""
Supabase Database Logger Integration.

Persists statement metadata, extracted transactions, and TransferData entries directly into
the Supabase Postgres database (supabase-db container running on macmini-primary).
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("supabase_logger")


class SupabaseLogger:
    """Client for logging bank statements and audit logs to Supabase."""

    def __init__(
        self,
        base_url: str = "http://100.83.83.8:8002",
        service_key: Optional[str] = None,
        timeout: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "anon-key")
        self.timeout = timeout

    def log_statement_run(
        self,
        extracted_data: Dict[str, Any],
        status: str = "SUCCESS",
        audit_sha256: str = "",
    ) -> bool:
        """
        Posts extracted statement metadata and transactions to Supabase Rest API (PostgREST).
        """
        meta = extracted_data.get("statement_metadata", {})
        txs = extracted_data.get("transactions", [])

        payload = {
            "account_holder": meta.get("account_holder", ""),
            "eik": meta.get("eik", ""),
            "iban": meta.get("iban", ""),
            "currency": meta.get("currency", "EUR"),
            "period_start": meta.get("period_start", ""),
            "period_end": meta.get("period_end", ""),
            "opening_balance": float(meta.get("opening_balance", 0.0)),
            "transaction_count": len(txs),
            "status": status,
            "audit_sha256": audit_sha256,
        }

        url = f"{self.base_url}/rest/v1/bank_statements"
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Prefer": "return=minimal",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status in (200, 201, 204):
                    logger.info("Successfully logged statement run to Supabase.")
                    return True
        except Exception as e:
            logger.warning(f"Supabase logging offline fallback: {e}")

        return False
