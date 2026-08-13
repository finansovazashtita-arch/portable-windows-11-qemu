"""
Unit & Integration Test Suite for Milestone M65: Real-Time Multi-Entity Audit Compliance & WebSockets Telemetry Dashboard (m65_realtime_compliance_ui).
"""

import base64
import hashlib
import json
import os
import unittest
from src.dashboard.realtime_compliance_ui import (
    RealTimeComplianceEngine,
    EntityComplianceStatus,
    EInvoicePortalStatus,
    PQCNodeStatus,
    WebSocketFrame,
)
from src.dashboard.dashboard_server import DashboardHandler, ThreadedHTTPServer, PORT, WEB_UI_DIR


class TestRealTimeComplianceEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RealTimeComplianceEngine()

    def test_initial_multi_entity_seeding(self):
        payload = self.engine.get_telemetry_payload()
        self.assertEqual(payload["system_status"], "ONLINE")
        self.assertEqual(len(payload["entities"]), 5)
        
        # Check entities by jurisdiction
        jurisdictions = {e["jurisdiction"] for e in payload["entities"]}
        self.assertIn("BG", jurisdictions)
        self.assertIn("DE", jurisdictions)
        self.assertIn("UK", jurisdictions)
        self.assertIn("US", jurisdictions)
        self.assertIn("CH", jurisdictions)

    def test_telemetry_totals_calculation(self):
        payload = self.engine.get_telemetry_payload()
        summary = payload["summary"]
        self.assertGreater(summary["grand_total_debits_eur"], 0.0)
        self.assertGreater(summary["grand_total_credits_eur"], 0.0)
        self.assertEqual(summary["total_entities"], 5)
        self.assertIn("audit_ledger_hash_head", summary)

    def test_nra_einvoice_stream_ingestion(self):
        inv_payload = {
            "invoice_id": "INV-2026-TEST001",
            "entity_id": "BG-STORGOZIA-01",
            "counterparty_name": "Тест Спедиция ЕООД",
            "counterparty_eik": "831998877",
            "amount_bgn": 3500.00,
            "vat_bgn": 700.00,
        }
        res = self.engine.submit_nra_einvoice(inv_payload)
        self.assertTrue(res["success"])
        self.assertEqual(res["invoice"]["invoice_id"], "INV-2026-TEST001")
        self.assertEqual(res["invoice"]["status"], EInvoicePortalStatus.CAIS_EPP_ACCEPTED.value)
        self.assertTrue(res["invoice"]["qes_signed"])

        # Check telemetry update
        telemetry = self.engine.get_telemetry_payload()
        first_item = telemetry["nra_einvoice_stream"][0]
        self.assertEqual(first_item["invoice_id"], "INV-2026-TEST001")

    def test_pqc_replication_mesh_node_sync(self):
        res = self.engine.sync_pqc_mesh_node("hetzner-fsn1-dc14")
        self.assertTrue(res["success"])
        self.assertEqual(res["node"]["status"], PQCNodeStatus.HEALTHY.value)
        self.assertLess(res["node"]["replication_lag_ms"], 1.0)

    def test_interactive_audit_correction_execution(self):
        correction_payload = {
            "entry_id": "ERR-UK-401-08",
            "entity_id": "UK-LTD-03",
            "account_debit": "621",
            "account_credit": "401",
            "corrected_amount": 150.00,
            "reason": "Unit test interactive audit reconciliation",
        }
        
        # Verify initial state of UK entity
        uk_entity_before = self.engine.entities["UK-LTD-03"]
        self.assertEqual(uk_entity_before.compliance_status, EntityComplianceStatus.FLAGGED_DISCREPANCY)
        self.assertEqual(uk_entity_before.discrepancy_eur, 150.00)

        # Apply correction
        res = self.engine.submit_correction(correction_payload)
        self.assertTrue(res["success"])
        self.assertEqual(res["entity_status"], EntityComplianceStatus.COMPLIANT.value)
        self.assertEqual(res["new_discrepancy_eur"], 0.00)
        self.assertIsNotNone(res["new_audit_hash"])

        # Verify entity updated state
        uk_entity_after = self.engine.entities["UK-LTD-03"]
        self.assertEqual(uk_entity_after.compliance_status, EntityComplianceStatus.COMPLIANT)
        self.assertEqual(uk_entity_after.discrepancy_eur, 0.00)
        self.assertEqual(len(self.engine.corrections_ledger), 1)

    def test_websocket_frame_encoding_and_decoding(self):
        msg = "Hello WebSockets Telemetry"
        encoded = WebSocketFrame.encode_text_frame(msg)
        self.assertIsInstance(encoded, bytes)

        # Decode frame
        decoded_text, consumed = WebSocketFrame.decode_client_frame(encoded)
        self.assertEqual(decoded_text, msg)
        self.assertEqual(consumed, len(encoded))


class TestWebUIAssets(unittest.TestCase):
    def test_web_ui_files_exist(self):
        index_path = os.path.join(WEB_UI_DIR, "index.html")
        styles_path = os.path.join(WEB_UI_DIR, "styles.css")
        app_path = os.path.join(WEB_UI_DIR, "app.js")

        self.assertTrue(os.path.exists(index_path))
        self.assertTrue(os.path.exists(styles_path))
        self.assertTrue(os.path.exists(app_path))

        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("FinansProtect", content)
            self.assertIn("WebSockets", content)
            self.assertIn("НАП E-Invoicing", content)

        with open(app_js_path := app_path, "r", encoding="utf-8") as f:
            js_content = f.read()
            self.assertIn("connectWebSocket", js_content)
            self.assertIn("renderDashboard", js_content)


if __name__ == "__main__":
    unittest.main()
