"""Unit and Integration Test Suite for Audit & TRANSFER.LOG Exporter (src/audit/generate_transfer_log.py)."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.audit.generate_transfer_log import (
    reconcile_3way,
    generate_transfer_log,
    export_audit_log,
    run_audit_export,
    main,
)


def _make_21_sample_items():
    """Generates 21 sample line-item transactions for 3-way reconciliation testing."""
    ocr = []
    journal = []
    sql = []
    for i in range(1, 22):
        doc_no = f"DOC-{1000 + i}"
        amt = round(10.0 + i * 5.5, 2)
        date = "2026-01-15"
        counterparty = f"Counterparty {i}"
        
        # OCR dict (Feature 1 & 2 schema)
        ocr.append({
            "item_id": i,
            "posting_date": date,
            "document_number": doc_no,
            "counterparty_name": counterparty,
            "debit_amount": amt if i % 2 != 0 else 0.0,
            "credit_amount": 0.0 if i % 2 != 0 else amt,
            "currency": "EUR",
        })

        # Journal dict (Double-entry schema)
        dedup_hash = hashlib.sha256(f"114077876|{doc_no}|{amt:.2f}".encode("utf-8")).hexdigest()
        journal.append({
            "item_id": i,
            "posting_date": date,
            "doc_no": doc_no,
            "counterparty_name": counterparty,
            "counterparty_eik": "",  # Empty string to test EIK fallback robustness
            "debit_account": "401" if i % 2 != 0 else "503",
            "credit_account": "503" if i % 2 != 0 else "411",
            "amount": amt,
            "currency": "EUR",
            "dedup_hash": dedup_hash,
        })

        # SQL DB record dict (SQLEXPRESS schema)
        sql.append({
            "OpID": i,
            "OpDate": date,
            "DocNum": doc_no,
            "Company": counterparty,
            "EIK": "114077876",
            "DebitAcct": "401" if i % 2 != 0 else "503",
            "CreditAcct": "503" if i % 2 != 0 else "411",
            "TotalEUR": amt,
            "Hash": dedup_hash,
        })

    return ocr, journal, sql


class TestReconcile3Way(unittest.TestCase):
    """Tests for 3-way reconciliation logic across OCR, Journal, and SQL datasets."""

    def test_reconcile_3way_happy_path_21_items(self):
        """Task 4a: 3-way reconciliation happy path (all 3 sources matching 21 line items)."""
        ocr, journal, sql = _make_21_sample_items()
        res = reconcile_3way(ocr, journal, sql)

        self.assertEqual(res["reconciliation_status"], "MATCHED")
        self.assertEqual(res["reconciled_count"], 21)
        self.assertEqual(res["ocr_count"], 21)
        self.assertEqual(res["journal_count"], 21)
        self.assertEqual(res["sql_count"], 21)
        self.assertEqual(len(res["discrepancies"]), 0)
        self.assertAlmostEqual(res["ocr_total_eur"], res["journal_total_eur"], places=2)
        self.assertAlmostEqual(res["journal_total_eur"], res["sql_total_eur"], places=2)

    def test_reconcile_3way_count_mismatch(self):
        """Task 4b: Mismatched item counts across sources."""
        ocr, journal, sql = _make_21_sample_items()
        journal_mismatched = journal[:20]  # 20 items instead of 21

        res = reconcile_3way(ocr, journal_mismatched, sql)
        self.assertEqual(res["reconciliation_status"], "UNMATCHED")
        self.assertTrue(any("Record count mismatch" in d for d in res["discrepancies"]))

    def test_reconcile_3way_amount_total_mismatch(self):
        """Task 4b: Mismatched total EUR amounts across sources."""
        ocr, journal, sql = _make_21_sample_items()
        journal_tampered = [dict(item) for item in journal]
        journal_tampered[0]["amount"] += 100.0  # Alter total sum

        res = reconcile_3way(ocr, journal_tampered, sql)
        self.assertEqual(res["reconciliation_status"], "UNMATCHED")
        self.assertTrue(any("Total amount mismatch" in d for d in res["discrepancies"]))

    def test_reconcile_3way_missing_source_data(self):
        """Task 4b: Missing source data (e.g. SQL database records omitted)."""
        ocr, journal, _ = _make_21_sample_items()
        res = reconcile_3way(ocr, journal, sql_records=None)

        self.assertEqual(res["reconciliation_status"], "PARTIAL")
        self.assertTrue(any("Missing source dataset(s): SQL" in d for d in res["discrepancies"]))

    def test_reconcile_3way_line_item_doc_mismatch(self):
        """Task 4b: Line-item level document number mismatch."""
        ocr, journal, sql = _make_21_sample_items()
        sql_tampered = [dict(item) for item in sql]
        sql_tampered[2]["DocNum"] = "DOC-WRONG-999"

        res = reconcile_3way(ocr, journal, sql_tampered)
        self.assertEqual(res["reconciliation_status"], "UNMATCHED")
        self.assertTrue(any("document number mismatch" in d.lower() for d in res["discrepancies"]))

    def test_reconcile_3way_line_item_amount_mismatch(self):
        """Task 4b: Line-item level amount mismatch with same gross count and swapped total edge case."""
        ocr, journal, sql = _make_21_sample_items()
        sql_tampered = [dict(item) for item in sql]
        # Swap amounts between item 0 and item 1 (preserves total sum, but violates line-item match)
        amt0 = sql_tampered[0]["TotalEUR"]
        amt1 = sql_tampered[1]["TotalEUR"]
        sql_tampered[0]["TotalEUR"] = amt1
        sql_tampered[1]["TotalEUR"] = amt0

        res = reconcile_3way(ocr, journal, sql_tampered)
        self.assertEqual(res["reconciliation_status"], "UNMATCHED")
        self.assertTrue(any("amount mismatch" in d.lower() for d in res["discrepancies"]))

    def test_reconcile_3way_dict_wrapper_vs_list(self):
        """Task 4c: Support dict wrapper structures (e.g., {"statement_metadata": ..., "transactions": [...]})."""
        ocr_list, journal_list, sql_list = _make_21_sample_items()

        ocr_dict = {"statement_metadata": {"account_holder": "СТОРГОЗИЯ АД"}, "transactions": ocr_list}
        journal_dict = {"journal_entries": journal_list}
        sql_dict = {"records": sql_list}

        res = reconcile_3way(ocr_dict, journal_dict, sql_dict)
        self.assertEqual(res["reconciliation_status"], "MATCHED")
        self.assertEqual(res["reconciled_count"], 21)


class TestGenerateTransferLog(unittest.TestCase):
    """Tests for generate_transfer_log file creation, formatting, and path handling."""

    def setUp(self):
        """Clean up potential leftover artifact paths before each test."""
        for path in (r"C:\TRANSFER.LOG", "/tmp/TRANSFER.LOG"):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def tearDown(self):
        """Clean up temporary log files created during test execution."""
        for path in (r"C:\TRANSFER.LOG", "/tmp/TRANSFER.LOG"):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_generate_transfer_log_formatting_and_headers(self):
        """Task 4d: Pipe-delimited log format, 3 header lines, UTF-8 encoding."""
        sample_entries = [
            {
                "item_id": 1,
                "posting_date": "2026-01-05",
                "doc_no": "12101",
                "counterparty_name": "НАП",
                "counterparty_eik": "114077876",
                "debit_account": "455",
                "credit_account": "503",
                "amount": 44.05,
                "currency": "EUR",
                "dedup_hash": "21252876483e5d8e64071495ee23c5ea61f97eb875f8c0d36937ce1ed20713c1",
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "TRANSFER.LOG")
            res = generate_transfer_log(journal_entries=sample_entries, target_path=log_path)

            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["count"], 1)
            self.assertTrue(os.path.exists(res["log_path"]))

            with open(res["log_path"], "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.strip().split("\n")
            self.assertGreaterEqual(len(lines), 4)  # 3 headers + 1 data line
            self.assertEqual(lines[0], "# MICROINVEST DELTA PRO TRANSFER AUDIT LOG")
            self.assertTrue(lines[1].startswith("# Generated:"))
            self.assertEqual(lines[2], "# Format: ItemNo|Date|DocNum|Counterparty|DebitAcc|CreditAcc|Amount|Currency|DedupHash")
            self.assertEqual(
                lines[3],
                "1|2026-01-05|12101|НАП|455|503|44.05|EUR|21252876483e5d8e64071495ee23c5ea61f97eb875f8c0d36937ce1ed20713c1"
            )

    def test_dedup_hash_key_lookup_and_fallback_preservation(self):
        """Task 1 & 4d: Preserve existing dedup_hash key and generate clean fallback hash without EIK corruption."""
        sample_entries = [
            # Item 1: standard dedup_hash key
            {
                "item_id": 1,
                "doc_no": "1001",
                "counterparty_eik": "",
                "amount": 100.0,
                "dedup_hash": "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890",
            },
            # Item 2: missing dedup_hash and empty counterparty_eik (must fallback to statement EIK 114077876)
            {
                "item_id": 2,
                "doc_no": "1002",
                "counterparty_eik": "",
                "amount": 50.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "TRANSFER.LOG")
            res = generate_transfer_log(journal_entries=sample_entries, target_path=log_path)

            records = res["records"]
            self.assertEqual(records[0]["DedupHash"], "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890")

            expected_fallback_input = "114077876|1002|50.00"
            expected_fallback_hash = hashlib.sha256(expected_fallback_input.encode("utf-8")).hexdigest()
            self.assertEqual(records[1]["DedupHash"], expected_fallback_hash)

    def test_cross_platform_path_handling(self):
        r"""Task 3 & 4d: Graceful handling of Windows paths (C:\TRANSFER.LOG) on macOS/Linux."""
        sample_entries = [{"item_id": 1, "doc_no": "1001", "amount": 10.0}]

        # Call with Windows target path C:\TRANSFER.LOG
        res = generate_transfer_log(journal_entries=sample_entries, target_path=r"C:\TRANSFER.LOG")
        self.assertEqual(res["target_path"], r"C:\TRANSFER.LOG")

        if os.name != "nt":
            self.assertEqual(res["log_path"], "/tmp/TRANSFER.LOG")
            self.assertTrue(os.path.exists("/tmp/TRANSFER.LOG"))
            # Confirm no literal C:\TRANSFER.LOG was created in current working directory
            self.assertFalse(os.path.exists(r"C:\TRANSFER.LOG"))

    def test_generate_transfer_log_handles_string_and_none_amount(self):
        """Task 4d: Robust string and None amount coercions."""
        sample_entries = [
            {
                "item_id": 1,
                "posting_date": "2026-01-05",
                "doc_no": "1001",
                "counterparty_name": "Test String Amount",
                "debit_account": "503",
                "credit_account": "401",
                "amount": "123.45",
            },
            {
                "item_id": 2,
                "posting_date": "2026-01-06",
                "doc_no": "1002",
                "counterparty_name": "Test None Amount",
                "debit_account": "503",
                "credit_account": "401",
                "amount": None,
            },
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "TRANSFER.LOG")
            res = generate_transfer_log(journal_entries=sample_entries, target_path=log_path)
            self.assertEqual(res["count"], 2)
            self.assertIn("123.45", res["log_content"])
            self.assertIn("0.00", res["log_content"])

    def test_e2e_audit_log_generation_and_export(self):
        """Task 4e: End-to-end audit log generation and export logic."""
        ocr, journal, sql = _make_21_sample_items()
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "TRANSFER.LOG")
            res = generate_transfer_log(
                extracted_transactions=ocr,
                journal_entries=journal,
                sql_records=sql,
                target_path=log_path,
            )

            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(res["reconciliation_status"], "MATCHED")
            self.assertEqual(res["count"], 21)
            self.assertTrue(os.path.exists(res["log_path"]))

            with open(res["log_path"], "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            # 3 headers + 21 line items = 24 lines total
            self.assertEqual(len(lines), 24)

    def test_aliases(self):
        """Test export_audit_log and run_audit_export helper aliases."""
        sample_entries = [{"item_id": 1, "doc_no": "1001", "amount": 10.0}]
        res1 = export_audit_log(journal_entries=sample_entries)
        res2 = run_audit_export(journal_entries=sample_entries)
        self.assertEqual(res1["count"], 1)
        self.assertEqual(res2["count"], 1)

    @patch("sys.argv", ["generate_transfer_log.py", "--verbose"])
    def test_cli_main(self):
        """Test CLI main() entrypoint execution."""
        try:
            main()
        except SystemExit as e:
            self.assertEqual(e.code, 0)


if __name__ == "__main__":
    unittest.main()
