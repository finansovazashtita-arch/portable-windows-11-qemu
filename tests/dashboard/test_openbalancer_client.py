"""
Unit & Integration Tests for OpenBalancer Dashboard Client.
"""

import dataclasses
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.dashboard.openbalancer_client import OpenBalancerClient, TelemetryEvent


class TestOpenBalancerClient(unittest.TestCase):
    """Test suite for OpenBalancerClient."""

    def setUp(self):
        self.client = OpenBalancerClient(
            endpoint_url="http://127.0.0.1:8090/telemetry",
            dashboard_url="https://n8n.openbalancer.com",
            timeout=2
        )
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compute_file_sha256(self):
        test_file = os.path.join(self.temp_dir.name, "test_sha.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("OpenBalancer Telemetry Test String")

        sha_result = self.client.compute_file_sha256(test_file)
        self.assertEqual(len(sha_result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha_result))

    def test_compute_file_sha256_missing_file(self):
        missing_file = os.path.join(self.temp_dir.name, "non_existent.txt")
        sha_result = self.client.compute_file_sha256(missing_file)
        self.assertEqual(sha_result, "")

    def test_build_event_from_valid_artifacts(self):
        json_path = os.path.join(self.temp_dir.name, "extracted.json")
        audit_path = os.path.join(self.temp_dir.name, "TRANSFER.LOG")
        pdf_path = os.path.join(self.temp_dir.name, "1.pdf")

        sample_data = {
            "statement_metadata": {
                "account_holder": "СТОРГОЗИЯ АД",
                "eik": "114077876",
                "iban": "BG71STSA93000028013479",
                "currency": "EUR",
                "period_start": "01.01.2026",
                "period_end": "31.01.2026",
                "opening_balance": 5883.29
            },
            "transactions": [
                {"item_id": 1, "debit_amount": 100.00, "credit_amount": 0.00},
                {"item_id": 2, "debit_amount": 0.00, "credit_amount": 50.00}
            ]
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        with open(audit_path, "w", encoding="utf-8") as f:
            f.write("TRANSFER_LOG_LINE_ITEM_OK")

        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write("PDF_BYTES")

        event = self.client.build_event(json_path, audit_path, pdf_path, status="SUCCESS")

        self.assertEqual(event.status, "SUCCESS")
        self.assertEqual(event.extracted_count, 2)
        self.assertEqual(event.opening_balance, 5883.29)
        self.assertEqual(event.total_debits, 100.00)
        self.assertEqual(event.total_credits, 50.00)
        self.assertEqual(event.closing_balance, 5833.29)
        self.assertEqual(event.balance_discrepancy, 0.00)
        self.assertEqual(event.currency, "EUR")
        self.assertEqual(event.qemu_vm_status, "ONLINE")
        self.assertTrue(len(event.audit_checksum_sha256) == 64)

    @patch("urllib.request.urlopen")
    def test_send_telemetry_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        event = TelemetryEvent(
            pipeline_id="pip-12345",
            timestamp="2026-08-12T19:00:00Z",
            status="SUCCESS",
            extracted_count=21,
            total_debits=7329.50,
            total_credits=3610.08,
            opening_balance=5883.29,
            closing_balance=2163.87,
            balance_discrepancy=0.00,
            currency="EUR",
            statement_period="01.01.2026 – 31.01.2026",
            audit_checksum_sha256="abc123sha256",
            microinvest_imported_records=21,
            qemu_vm_status="ONLINE",
            pdf_processed="/tmp/1.pdf"
        )

        success = self.client.send_telemetry(event)
        self.assertTrue(success)

    @patch("urllib.request.urlopen")
    def test_send_telemetry_offline_fallback(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")

        event = TelemetryEvent(
            pipeline_id="pip-99999",
            timestamp="2026-08-12T19:00:00Z",
            status="ERROR",
            extracted_count=0,
            total_debits=0.0,
            total_credits=0.0,
            opening_balance=0.0,
            closing_balance=0.0,
            balance_discrepancy=0.0,
            currency="EUR",
            statement_period="",
            audit_checksum_sha256="",
            microinvest_imported_records=0,
            qemu_vm_status="OFFLINE",
            pdf_processed="/tmp/missing.pdf",
            error_message="Connection failed"
        )

        success = self.client.send_telemetry(event)
        self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()
