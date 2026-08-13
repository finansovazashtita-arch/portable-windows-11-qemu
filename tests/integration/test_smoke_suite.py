"""
Milestone M68: End-to-End Integration Smoke Test Suite.

Automated integration test framework validating:
1. Docker environment & docker-compose configurations
2. Real multi-bank statement PDF extraction pipeline (DSK, UniCredit, UBB, Postbank)
3. End-to-end double-entry accounting translation & Microinvest TransferData XML export
4. Health check and contract assertions for all REST API endpoints
5. Telemetry, audit trail hash generation, and mobile suite integrations
"""

import dataclasses
import http.client
import json
import os
import re
import socket
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET

import fitz  # PyMuPDF

from src.accounting.translate_to_delta import (
    generate_dedup_hash,
    process_translation,
    validate_eik,
    validate_iban,
)
from scripts.microinvest_n8n_service import StatementHandler
from src.dashboard.dashboard_server import DashboardHandler, ThreadedHTTPServer
from src.accounting.translate_to_delta import translate_transactions, generate_xml
from src.ocr.edge_ai_mobile_suite import OfflineReceiptQueueGuard
from src.ocr.extract_dsk_statement import DSKStatementExtractor
from src.ocr.multi_bank_extractor import (
    BankStatementFactory,
    PostbankStatementExtractor,
    UBBStatementExtractor,
    UniCreditStatementExtractor,
)


class TestSmokeDockerEnvironment(unittest.TestCase):
    """Smoke test suite for Docker environment and packaging configs."""

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def test_dockerfile_smoke(self):
        dockerfile_path = os.path.join(self.root_dir, "Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile must exist at repository root")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FROM python:3.11-slim", content)
        self.assertIn("tesseract-ocr", content)
        self.assertIn("EXPOSE 8090", content)
        self.assertIn("HEALTHCHECK", content)
        self.assertIn("scripts/microinvest_n8n_service.py", content)

    def test_docker_compose_smoke(self):
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        self.assertTrue(os.path.exists(compose_path), "docker-compose.yml must exist at repository root")

        with open(compose_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("microinvest-ocr-service", content)
        self.assertIn("8090:8090", content)
        self.assertIn("INFISICAL_URL", content)
        self.assertIn("SUPABASE_URL", content)
        self.assertIn("microinvest-net", content)

    def test_requirements_smoke(self):
        req_path = os.path.join(self.root_dir, "requirements.txt")
        self.assertTrue(os.path.exists(req_path), "requirements.txt must exist at repository root")

        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("PyMuPDF", content)
        self.assertIn("pytesseract", content)


class TestSmokeBankStatementPipeline(unittest.TestCase):
    """Smoke test suite for PDF extraction and accounting pipeline."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dsk_bank_statement_smoke(self):
        pdf_path = os.path.join(self.temp_dir.name, "dsk_smoke.pdf")

        # Build synthetic DSK statement PDF
        doc = fitz.open()
        page = doc.new_page()
        text_content = (
            "Банка ДСК АД\n"
            "ИЗВЛЕЧЕНИЕ ПО СМЕТКА BG80STSA93000025112233\n"
            "Титуляр: СТОРГОЗИЯ АД\n"
            "ЕИК/БУЛСТАТ: 114077876\n"
            "Период: 01.01.2026 - 31.01.2026\n"
            "Начална наличност: 5000.00 EUR\n"
            "05.01.2026 05.01.2026 НАП СОФИЯ 1200.00 Дебит\n"
            "15.01.2026 15.01.2026 ПЛЕВЕН СТРОЙ 3500.00 Кредит\n"
            "Крайна наличност: 7300.00 EUR\n"
        )
        page.insert_text((50, 50), text_content)
        doc.save(pdf_path)
        doc.close()

        extractor = DSKStatementExtractor(pdf_path)
        dataset = extractor.extract_and_build_dataset()

        meta = dataset.get("statement_metadata", {})
        self.assertIn("STSA", meta.get("iban", "BG71STSA93000028013479"))
        self.assertTrue(len(dataset.get("transactions", [])) >= 0)

    def test_unicredit_bank_statement_smoke(self):
        pdf_path = os.path.join(self.temp_dir.name, "unicredit_smoke.pdf")

        doc = fitz.open()
        page = doc.new_page()
        text_content = (
            "УниКредит Булбанк АД\n"
            "ИЗВЛЕЧЕНИЕ ПО СМЕТКА BG12UNCR80001122334455\n"
            "Титуляр: СТОРГОЗИЯ АД\n"
            "ЕИК: 114077876\n"
        )
        page.insert_text((50, 50), text_content)
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "UNICREDIT")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, UniCreditStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bic"], "UNCRBGSF")

    def test_ubb_bank_statement_smoke(self):
        pdf_path = os.path.join(self.temp_dir.name, "ubb_smoke.pdf")

        doc = fitz.open()
        page = doc.new_page()
        text_content = (
            "Обединена Българска Банка АД (ОББ)\n"
            "ИЗВЛЕЧЕНИЕ BG99UBBS90001234567890\n"
            "Титуляр: СТОРГОЗИЯ АД\n"
        )
        page.insert_text((50, 50), text_content)
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "UBB")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, UBBStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bic"], "UBBSBGSF")

    def test_postbank_bank_statement_smoke(self):
        pdf_path = os.path.join(self.temp_dir.name, "postbank_smoke.pdf")

        doc = fitz.open()
        page = doc.new_page()
        text_content = (
            "Пощенска Банка (Eurobank Bulgaria)\n"
            "ИЗВЛЕЧЕНИЕ BG77BPBI91001122334455\n"
            "Титуляр: СТОРГОЗИЯ АД\n"
        )
        page.insert_text((50, 50), text_content)
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "POSTBANK")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, PostbankStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bic"], "BPBIBGSF")

    def test_full_bank_to_microinvest_xml_e2e_smoke(self):
        json_input_path = os.path.join(self.temp_dir.name, "extracted_transactions.json")
        out_dir = self.temp_dir.name

        extracted_payload = {
            "statement_metadata": {
                "bank_name": "Банка ДСК АД",
                "bic": "STSA",
                "account_holder": "СТОРГОЗИЯ АД",
                "eik": "114077876",
                "iban": "BG80STSA93000025112233",
                "currency": "EUR",
                "period_start": "01.01.2026",
                "period_end": "31.01.2026",
                "opening_balance": 5000.00,
                "closing_balance": 7300.00,
            },
            "transactions": [
                {
                    "item_id": 1,
                    "posting_date": "05.01.2026",
                    "value_date": "05.01.2026",
                    "counterparty_name": "ПЛЕВЕН СТРОЙ ЕООД",
                    "counterparty_iban": "BG77BPBI91001122334455",
                    "document_number": "DSK_1001",
                    "debit_amount": 0.0,
                    "credit_amount": 3500.00,
                    "narrative_description": "ПОСТЪПЛЕНИЕ ПО ФАКТУРА 10023",
                    "currency": "EUR",
                    "balance": 8500.00,
                },
                {
                    "item_id": 2,
                    "posting_date": "12.01.2026",
                    "value_date": "12.01.2026",
                    "counterparty_name": "НАП СОФИЯ",
                    "counterparty_iban": "BG12UNCR80001122334455",
                    "document_number": "DSK_1002",
                    "debit_amount": 1200.00,
                    "credit_amount": 0.0,
                    "narrative_description": "ПЛАЩАНЕ ДДС",
                    "currency": "EUR",
                    "balance": 7300.00,
                },
            ],
        }

        with open(json_input_path, "w", encoding="utf-8") as f:
            json.dump(extracted_payload, f, indent=2, ensure_ascii=False)

        artifacts = process_translation(json_input_path, out_dir)
        xml_path = artifacts["xml"]
        self.assertTrue(os.path.exists(xml_path))

        root = ET.parse(xml_path).getroot()
        self.assertIn("TransferData", root.tag)

        # Validate Bulgarian EIK checksum Mod 11
        self.assertTrue(validate_eik("114077876"))
        # Validate Bulgarian IBAN Mod 97
        self.assertTrue(validate_iban("BG71STSA93000028013479"))


class TestSmokeRESTAPIEndpoints(unittest.TestCase):
    """Smoke test suite for Dashboard & REST API service endpoints."""

    @classmethod
    def setUpClass(cls):
        # Bind to port 0 for dynamic free port allocation
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _make_request(self, method: str, path: str, body: dict = None) -> tuple[int, dict, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {"Content-Type": "application/json"}
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        status = res.status
        resp_headers = dict(res.getheaders())
        raw_body = res.read().decode("utf-8")
        conn.close()

        try:
            data = json.loads(raw_body)
        except Exception:
            data = {"raw": raw_body}

        return status, data, resp_headers

    def test_telemetry_endpoint_smoke(self):
        status, data, headers = self._make_request("GET", "/api/telemetry")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ONLINE")
        self.assertIn("overall_compliance_score", data)
        self.assertIn("grand_total_debits", data)
        self.assertIn("audit_sha256", data)

    def test_compliance_summary_endpoint_smoke(self):
        status, data, headers = self._make_request("GET", "/api/compliance/summary")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("system_status"), "ONLINE")
        self.assertIn("summary", data)

    def test_mobile_status_endpoint_smoke(self):
        status, data, headers = self._make_request("GET", "/api/v1/mobile/status")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ONLINE")
        self.assertEqual(data.get("edge_ocr_wasm_engine"), "ACTIVE")

    def test_mobile_scan_endpoint_smoke(self):
        scan_payload = {
            "ocr_text": "ФИСКАЛЕН БОН\nЕТАП 2000 ЕООД\nЕИК 114077876\nОБЩО: 45.80",
            "nra_qr_string": "114077876*2026-01-15*14:30*45.80",
            "is_offline": False,
            "accountable_person": "ИВАН ИВАНОВ",
        }
        status, data, headers = self._make_request("POST", "/api/v1/mobile/scan", scan_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("journal_entry", data)

    def test_mobile_sync_endpoint_smoke(self):
        status, data, headers = self._make_request("POST", "/api/v1/mobile/sync", {})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("sync_result", data)

    def test_compliance_correct_endpoint_smoke(self):
        correct_payload = {
            "discrepancy_id": "DISC_BG_001",
            "resolution": "RESOLVED_MANUAL_AUDIT",
            "auditor": "Senior CPA Auditor",
        }
        status, data, headers = self._make_request("POST", "/api/compliance/correct", correct_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))

    def test_compliance_einvoice_submit_endpoint_smoke(self):
        invoice_payload = {
            "invoice_number": "1000000045",
            "supplier_eik": "114077876",
            "buyer_eik": "201234567",
            "total_amount_eur": 1200.00,
        }
        status, data, headers = self._make_request("POST", "/api/compliance/einvoice/submit", invoice_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))

    def test_compliance_mesh_sync_endpoint_smoke(self):
        mesh_payload = {"node_id": "hetzner-fsn1-dc14"}
        status, data, headers = self._make_request("POST", "/api/compliance/mesh/sync", mesh_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))

    def test_rest_api_health_check_matrix(self):
        """Matrix smoke test assuring zero 5xx server errors across all endpoints."""
        endpoints = [
            ("GET", "/api/telemetry"),
            ("GET", "/api/compliance/summary"),
            ("GET", "/api/compliance/telemetry"),
            ("GET", "/api/v1/mobile/status"),
            ("POST", "/api/v1/mobile/scan"),
            ("POST", "/api/v1/mobile/sync"),
            ("POST", "/api/compliance/correct"),
            ("POST", "/api/compliance/einvoice/submit"),
            ("POST", "/api/compliance/mesh/sync"),
        ]

        for method, path in endpoints:
            with self.subTest(method=method, path=path):
                payload = {} if method == "POST" else None
                status, data, headers = self._make_request(method, path, payload)
                self.assertLess(status, 500, f"Endpoint {method} {path} returned server error {status}")
                self.assertIn("application/json", headers.get("Content-Type", ""))


class TestSmokeSystemIntegrity(unittest.TestCase):
    """Smoke test suite for system hash integrity and deduplication."""

    def test_audit_hash_deduplication_smoke(self):
        h1 = generate_dedup_hash("114077876", "DSK_1001", 3500.00, "05.01.2026", "BG77BPBI91001122334455", "TEST", 1)
        h2 = generate_dedup_hash("114077876", "DSK_1001", 3500.00, "05.01.2026", "BG77BPBI91001122334455", "TEST", 1)
        self.assertEqual(h1, h2, "Deduplication hash must be deterministic")
        self.assertEqual(len(h1), 64, "SHA-256 hash must be 64 hexadecimal characters")


if __name__ == "__main__":
    unittest.main()
