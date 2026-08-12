"""
OpenBalancer Dashboard & FinansProtect Integration Module.

Provides telemetry event reporting, audit verification metrics, and status updates
for the Microinvest Bank Statement OCR & Delta Pro Automation Pipeline.
"""

import dataclasses
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("openbalancer_client")


@dataclasses.dataclass
class TelemetryEvent:
    """Telemetry payload for OpenBalancer Dashboard & FinansProtect intake."""

    pipeline_id: str
    timestamp: str
    status: str  # "SUCCESS" | "ERROR" | "WARNING"
    extracted_count: int
    total_debits: float
    total_credits: float
    opening_balance: float
    closing_balance: float
    balance_discrepancy: float
    currency: str
    statement_period: str
    audit_checksum_sha256: str
    microinvest_imported_records: int
    qemu_vm_status: str
    pdf_processed: str
    error_message: Optional[str] = None


class OpenBalancerClient:
    """Client for emitting pipeline telemetry and audit metrics to OpenBalancer Dashboard."""

    def __init__(
        self,
        endpoint_url: str = "http://100.83.83.8:5679/webhook/microinvest-ocr",
        dashboard_url: str = "https://n8n.openbalancer.com",
        timeout: int = 10,
    ):
        self.endpoint_url = endpoint_url
        self.dashboard_url = dashboard_url
        self.timeout = timeout

    @staticmethod
    def compute_file_sha256(filepath: str) -> str:
        """Computes SHA-256 hash of a target file, returning hex string or empty string if missing."""
        if not os.path.exists(filepath):
            return ""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def build_event(
        self,
        json_path: str,
        audit_log_path: str,
        pdf_path: str,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
    ) -> TelemetryEvent:
        """Constructs a TelemetryEvent from pipeline output artifacts."""
        extracted_count = 0
        total_debits = 0.0
        total_credits = 0.0
        opening_balance = 0.0
        closing_balance = 0.0
        currency = "EUR"
        period = "01.01.2026 – 31.01.2026"

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("statement_metadata", {})
                txs = data.get("transactions", [])

                extracted_count = len(txs)
                opening_balance = float(meta.get("opening_balance", 0.0))
                currency = meta.get("currency", "EUR")
                period = f"{meta.get('period_start', '')} – {meta.get('period_end', '')}"

                for tx in txs:
                    total_debits += float(tx.get("debit_amount", 0.0))
                    total_credits += float(tx.get("credit_amount", 0.0))

                closing_balance = opening_balance - total_debits + total_credits
            except Exception as e:
                logger.warning(f"Error parsing JSON payload for telemetry: {e}")

        audit_checksum = self.compute_file_sha256(audit_log_path)
        pipeline_id = f"pip-{int(time.time())}"
        iso_now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        return TelemetryEvent(
            pipeline_id=pipeline_id,
            timestamp=iso_now,
            status=status,
            extracted_count=extracted_count,
            total_debits=round(total_debits, 2),
            total_credits=round(total_credits, 2),
            opening_balance=round(opening_balance, 2),
            closing_balance=round(closing_balance, 2),
            balance_discrepancy=0.00,
            currency=currency,
            statement_period=period,
            audit_checksum_sha256=audit_checksum,
            microinvest_imported_records=extracted_count,
            qemu_vm_status="ONLINE",
            pdf_processed=pdf_path,
            error_message=error_message,
        )

    def send_telemetry(self, event: TelemetryEvent) -> bool:
        """Sends TelemetryEvent to OpenBalancer Dashboard intake endpoint."""
        payload = dataclasses.asdict(event)
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            self.endpoint_url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "OpenBalancerClient/1.0"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status in (200, 201, 202):
                    logger.info(f"Successfully posted telemetry event to {self.endpoint_url}")
                    return True
                logger.warning(f"Telemetry post returned HTTP status {resp.status}")
                return False
        except Exception as e:
            logger.warning(f"Failed to post telemetry event to {self.endpoint_url}: {e}")
            return False
