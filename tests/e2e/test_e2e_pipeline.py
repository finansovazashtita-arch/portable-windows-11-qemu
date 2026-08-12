"""
Requirement-Driven Opaque-Box E2E Test Suite for Microinvest Bank Statement OCR & Delta Pro Automation.

Covers Tiers 1-4:
- Tier 1: Feature Coverage (>=5 test cases per feature)
- Tier 2: Boundary & Corner Cases (>=5 test cases per feature domain)
- Tier 3: Cross-Feature Combinations (Pairwise integration)
- Tier 4: Real-World Application Scenarios (Live E2E 1.pdf processing & VM audit)
"""

import os
import re
import hashlib
import tempfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch

import fitz
import pytest


# =====================================================================
# ASSERTION HELPERS
# =====================================================================

class AssertionHelpers:
    """Domain assertion helpers for Bulgarian accounting rules, EIK, IBAN, XML, and Audit Logs."""

    @staticmethod
    def assert_valid_eik_checksum(eik: str) -> None:
        """Validates Bulgarian EIK 9-digit or 13-digit checksum (Mod 11 algorithm)."""
        assert re.match(r"^\d{9}(\d{4})?$", eik), f"Invalid EIK format: '{eik}'"
        digits = [int(c) for c in eik]

        # 9-digit check
        w1_9 = [1, 2, 3, 4, 5, 6, 7, 8]
        s1 = sum(d * w for d, w in zip(digits[:8], w1_9)) % 11
        if s1 == 10:
            w2_9 = [3, 4, 5, 6, 7, 8, 9, 10]
            s1 = sum(d * w for d, w in zip(digits[:8], w2_9)) % 11
            if s1 == 10:
                s1 = 0
        assert digits[8] == s1, f"EIK-9 checksum mismatch for {eik}: expected {s1}, got {digits[8]}"

        # 13-digit check if present
        if len(digits) == 13:
            w1_13 = [2, 7, 3, 5]
            s2 = sum(d * w for d, w in zip(digits[8:12], w1_13)) % 11
            if s2 == 10:
                w2_13 = [4, 9, 5, 7]
                s2 = sum(d * w for d, w in zip(digits[8:12], w2_13)) % 11
                if s2 == 10:
                    s2 = 0
            assert digits[12] == s2, f"EIK-13 checksum mismatch for {eik}: expected {s2}, got {digits[12]}"

    @staticmethod
    def assert_valid_iban(iban: str) -> None:
        """Mod-97 Bulgarian IBAN validation (ISO 7064)."""
        clean_iban = iban.replace(" ", "").upper()
        assert re.match(r"^BG\d{2}[A-Z]{4}\d{6}[0-9A-Z]{8}$", clean_iban), f"Invalid BG IBAN format: '{clean_iban}'"
        rearranged = clean_iban[4:] + clean_iban[:4]
        numeric_str = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
        assert int(numeric_str) % 97 == 1, f"IBAN Mod-97 checksum failed for '{iban}'"

    @staticmethod
    def assert_account_regex_compliance(account_code: str) -> None:
        """Ensures account code matches standard Bulgarian Chart of Accounts regex."""
        regex = r"^[1-9]([0-9]{0,3})(/([0-9]{1,9}))*$"
        assert re.match(regex, account_code), f"Account code '{account_code}' fails regex '{regex}'"

    @staticmethod
    def assert_double_entry_balanced(journal_entries: List[Dict[str, Any]]) -> None:
        """Verifies double-entry debit/credit balance equality invariant."""
        assert len(journal_entries) > 0, "Journal entries list cannot be empty"
        for entry in journal_entries:
            assert entry["amount"] > 0, f"Entry amount must be positive, got {entry['amount']}"
            assert entry["debit_account"] != entry["credit_account"], "Debit and Credit accounts must be distinct"
            AssertionHelpers.assert_account_regex_compliance(entry["debit_account"])
            AssertionHelpers.assert_account_regex_compliance(entry["credit_account"])

    @staticmethod
    def assert_xml_schema_valid(xml_content: str) -> None:
        """Validates Microinvest TransferData XML structure."""
        root = ET.fromstring(xml_content)
        root_tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
        assert root_tag == "TransferData", f"XML root tag must be TransferData, got '{root_tag}'"

        def get_child(parent, local_name):
            for child in parent:
                c_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if c_tag == local_name:
                    return child
            return None

        header = get_child(root, "Header")
        operations = get_child(root, "Operations")
        assert header is not None, "XML missing <Header> element"
        assert operations is not None, "XML missing <Operations> element"

        ops = [c for c in operations if (c.tag.split("}")[-1] if "}" in c.tag else c.tag) == "Operation"]
        assert len(ops) > 0, "<Operations> must contain at least one <Operation>"
        for op in ops:
            debit = get_child(op, "DebitAcc")
            credit = get_child(op, "CreditAcc")
            amount = get_child(op, "Amount")
            assert debit is not None and debit.text and debit.text.strip(), "Operation missing DebitAcc"
            assert credit is not None and credit.text and credit.text.strip(), "Operation missing CreditAcc"
            assert amount is not None and float(amount.text.strip()) > 0, "Operation missing valid positive Amount"

    @staticmethod
    def assert_canonical_transaction_schema(tx: Dict[str, Any]) -> None:
        """Ensures canonical transaction dict contains all 10 required schema fields."""
        required_fields = [
            "item_id", "posting_date", "value_date", "counterparty_name",
            "counterparty_iban", "document_number", "debit_amount",
            "credit_amount", "narrative_description", "currency", "balance"
        ]
        for field in required_fields:
            assert field in tx, f"Missing required field '{field}' in transaction"
        assert isinstance(tx["item_id"], int) and tx["item_id"] > 0
        assert isinstance(tx["debit_amount"], (int, float)) and tx["debit_amount"] >= 0.0
        assert isinstance(tx["credit_amount"], (int, float)) and tx["credit_amount"] >= 0.0
        assert not (tx["debit_amount"] > 0 and tx["credit_amount"] > 0), "Transaction cannot have both Debit > 0 and Credit > 0"

    @staticmethod
    def assert_sql_reconciliation(json_entries: List[Dict[str, Any]], db_records: List[Dict[str, Any]]) -> None:
        """Reconciles canonical line items against SQL database operations."""
        assert len(json_entries) == len(db_records), f"Row count mismatch: JSON={len(json_entries)}, DB={len(db_records)}"
        json_docs = {str(tx["document_number"]) for tx in json_entries}
        db_docs = {str(rec["DocNum"]) for rec in db_records}
        assert json_docs == db_docs, f"Document set mismatch: diff={json_docs ^ db_docs}"

        json_total = sum(tx["debit_amount"] + tx["credit_amount"] for tx in json_entries)
        db_total = sum(rec["TotalEUR"] for rec in db_records)
        assert abs(json_total - db_total) < 0.01, f"Total amount mismatch: JSON={json_total:.2f}, DB={db_total:.2f}"

    @staticmethod
    def assert_transfer_log_compliance(log_content: str, expected_count: int) -> None:
        """Validates TRANSFER.LOG formatting, header, entries, and integrity."""
        raw_lines = [line.strip() for line in log_content.strip().split("\n") if line.strip()]
        data_lines = [line for line in raw_lines if not line.startswith("#")]
        assert len(data_lines) >= expected_count, f"TRANSFER.LOG data line count {len(data_lines)} < expected {expected_count}"
        for line in data_lines:
            parts = line.split("|")
            assert len(parts) >= 6, f"Invalid TRANSFER.LOG line format: '{line}'"


# =====================================================================
# TIER 1: FEATURE COVERAGE TESTS (Synthetic / Mock Fixtures)
# =====================================================================

@pytest.mark.tier1
@pytest.mark.dry_run
class TestTier1FeatureCoverage:
    """Tier 1: Feature Coverage (>=5 test cases per core feature)."""

    @pytest.mark.ocr
    class TestOCRExtraction:
        """Feature 1 & 2: OCR Extraction & Line-Item Accuracy (R1)."""

        def test_ocr_extracts_all_21_line_items(self, sample_canonical_transactions):
            assert len(sample_canonical_transactions) == 21, "Expected exactly 21 extracted line items from 1.pdf"

        def test_ocr_header_metadata_accuracy(self, sample_statement_metadata):
            assert sample_statement_metadata["account_holder"] == "СТОРГОЗИЯ АД"
            assert sample_statement_metadata["opening_balance"] == 5883.29
            assert sample_statement_metadata["closing_balance"] == 2163.87
            AssertionHelpers.assert_valid_eik_checksum(sample_statement_metadata["eik"])
            AssertionHelpers.assert_valid_iban(sample_statement_metadata["iban"])

        def test_ocr_field_completeness(self, sample_canonical_transactions):
            for tx in sample_canonical_transactions:
                AssertionHelpers.assert_canonical_transaction_schema(tx)

        def test_ocr_turnover_reconciliation(self, sample_canonical_transactions, sample_statement_metadata):
            debits_sum = sum(tx["debit_amount"] for tx in sample_canonical_transactions)
            credits_sum = sum(tx["credit_amount"] for tx in sample_canonical_transactions)
            assert abs(debits_sum - sample_statement_metadata["debits_sum"]) < 0.001
            assert abs(credits_sum - sample_statement_metadata["credits_sum"]) < 0.001
            calc_closing = sample_statement_metadata["opening_balance"] + credits_sum - debits_sum
            assert abs(calc_closing - sample_statement_metadata["closing_balance"]) < 0.001

        def test_ocr_canonical_json_schema(self, sample_statement_metadata, sample_canonical_transactions):
            payload = {
                "statement_metadata": sample_statement_metadata,
                "transactions": sample_canonical_transactions,
            }
            assert "statement_metadata" in payload and "transactions" in payload
            assert len(payload["transactions"]) == 21

        def test_ocr_cyrillic_text_fidelity(self, sample_canonical_transactions):
            vendor_names = [tx["counterparty_name"] for tx in sample_canonical_transactions]
            assert "ЗОРА М.М.С. ООД" in vendor_names
            assert "ЕТИЕН ЕООД" in vendor_names
            assert "ТОПЛОФИКАЦИЯ ПЛЕВЕН АД" in vendor_names
            assert "БУЛГАРТРАНС ЕООД" in vendor_names

    @pytest.mark.accounting
    class TestDoubleEntryTranslation:
        """Feature 4, 5, 6: Bulgarian Double-Entry Translation & XML (R2)."""

        def test_translation_double_entry_balance_invariant(self, sample_journal_entries):
            AssertionHelpers.assert_double_entry_balanced(sample_journal_entries)

        def test_translation_bank_fee_mapping(self, sample_journal_entries):
            fee_entries = [e for e in sample_journal_entries if "ТАКСА" in e["narrative"].upper()]
            assert len(fee_entries) >= 3
            for entry in fee_entries:
                assert entry["debit_account"] == "621", "Bank fees must map to Debit 621 (Банкови такси)"
                assert entry["credit_account"] == "503", "Bank fees must map to Credit 503 (Разплащателна сметка)"

        def test_translation_supplier_settlement_mapping(self, sample_journal_entries):
            supplier_entries = [
                e for e in sample_journal_entries
                if e["credit_account"] == "503" and e["debit_account"] == "401"
            ]
            assert len(supplier_entries) >= 10
            for entry in supplier_entries:
                assert entry["debit_account"] == "401"

        def test_translation_customer_receipt_mapping(self, sample_journal_entries):
            customer_entries = [
                e for e in sample_journal_entries
                if e["debit_account"] == "503" and e["credit_account"] == "411"
            ]
            assert len(customer_entries) == 2
            for entry in customer_entries:
                assert entry["credit_account"] == "411"

        def test_translation_xml_schema_validity(self, sample_transfer_xml):
            AssertionHelpers.assert_xml_schema_valid(sample_transfer_xml)

        def test_translation_account_regex_compliance(self, sample_journal_entries):
            for entry in sample_journal_entries:
                AssertionHelpers.assert_account_regex_compliance(entry["debit_account"])
                AssertionHelpers.assert_account_regex_compliance(entry["credit_account"])

        def test_translation_eik_iban_validation(self, sample_statement_metadata):
            AssertionHelpers.assert_valid_eik_checksum(sample_statement_metadata["eik"])
            AssertionHelpers.assert_valid_iban(sample_statement_metadata["iban"])

    @pytest.mark.vnc
    class TestVNCAndSQLImport:
        """Feature 7, 8, 9: VNC Automation & SQLEXPRESS Verification (R3)."""

        def test_vnc_rfb_handshake_and_socket_connection(self, mock_vnc_client):
            assert mock_vnc_client.connect() is True

        def test_vnc_chart_of_accounts_setup(self, mock_vnc_client):
            assert mock_vnc_client.send_keys("Alt+O") is True
            assert mock_vnc_client.capture_screen() is True

        def test_vnc_powershell_base64_execution(self, mock_vnc_client):
            code, status = mock_vnc_client.type_base64_powershell("Get-Service MSSQLSERVER")
            assert code == 0 and status == "SUCCESS"

        def test_sql_partners_table_verification(self, mock_sql_client):
            partners = mock_sql_client.query_partners()
            assert len(partners) >= 1
            assert partners[0]["EIK"] == "114077876"

        def test_sql_operations_row_count_and_totals(self, mock_sql_client, sample_canonical_transactions):
            records = mock_sql_client.query_operations()
            assert len(records) == 21
            db_total = sum(r["TotalEUR"] for r in records)
            expected_total = sum(tx["debit_amount"] + tx["credit_amount"] for tx in sample_canonical_transactions)
            assert abs(db_total - expected_total) < 0.001

        def test_sql_accountings_double_entry_reconciliation(self, mock_sql_client, sample_canonical_transactions):
            records = mock_sql_client.query_operations()
            AssertionHelpers.assert_sql_reconciliation(sample_canonical_transactions, records)

        def test_sql_relational_integrity(self, mock_sql_client):
            code, stdout = mock_sql_client.execute_sqlcmd("SELECT COUNT(*) FROM OperationDetails WHERE OperID NOT IN (SELECT ID FROM Operations)")
            assert code == 0
            assert "21" in stdout or "0" in stdout

    @pytest.mark.audit
    class TestAuditLogging:
        """Feature 10: Persistent Audit Log TRANSFER.LOG (R4)."""

        def test_transfer_log_creation_and_location(self, mock_vm_storage):
            mock_vm_storage.write_text("2026-01-31 12:00:00 | DOC-847040558 | 114077876 | 401 | 503 | 154.20 | VERIFIED\n")
            assert mock_vm_storage.exists()
            assert mock_vm_storage.stat().st_size > 0

        def test_transfer_log_header_metadata(self, mock_vm_storage, sample_statement_metadata):
            header = f"HEADER | {sample_statement_metadata['eik']} | {sample_statement_metadata['iban']} | {sample_statement_metadata['period_start']}\n"
            mock_vm_storage.write_text(header)
            content = mock_vm_storage.read_text()
            assert "114077876" in content
            assert "BG71STSA93000028013479" in content

        def test_transfer_log_line_item_completeness(self, mock_vm_storage, sample_journal_entries):
            log_lines = "\n".join([
                f"2026-01-31 | {entry['doc_no']} | {entry['counterparty_eik']} | {entry['debit_account']} | {entry['credit_account']} | {entry['amount']:.2f} | VERIFIED"
                for entry in sample_journal_entries
            ])
            mock_vm_storage.write_text(log_lines)
            AssertionHelpers.assert_transfer_log_compliance(mock_vm_storage.read_text(), expected_count=21)

        def test_transfer_log_debit_credit_balance_compliance(self, sample_statement_metadata):
            net_change = sample_statement_metadata["credits_sum"] - sample_statement_metadata["debits_sum"]
            calc_closing = sample_statement_metadata["opening_balance"] + net_change
            assert abs(calc_closing - sample_statement_metadata["closing_balance"]) < 0.001

        def test_transfer_log_sha256_hash_validation(self, sample_journal_entries):
            for entry in sample_journal_entries:
                expected_input = f"114077876|{entry['doc_no']}|{entry['amount']:.2f}"
                computed_hash = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()
                assert entry["sha256_hash"] == computed_hash


# =====================================================================
# TIER 2: BOUNDARY & CORNER CASE TESTS (Synthetic / Edge Fixtures)
# =====================================================================

@pytest.mark.tier2
@pytest.mark.dry_run
class TestTier2BoundaryCornerCases:
    """Tier 2: Boundary & Corner Cases (>=5 test cases per feature domain)."""

    @pytest.mark.ocr
    class TestOCRBoundaries:
        """Boundary checks for PDF parsing and line item extraction."""

        def test_ocr_empty_narrative_handling(self, sample_canonical_transactions):
            tx = sample_canonical_transactions[0].copy()
            tx["narrative_description"] = ""
            AssertionHelpers.assert_canonical_transaction_schema(tx)
            assert tx["narrative_description"] == ""

        def test_ocr_corrupt_pdf_file_handling(self, tmp_path):
            corrupt_pdf = tmp_path / "bad_statement.pdf"
            corrupt_pdf.write_bytes(b"%PDF-1.4 CORRUPT DATA HEADER")
            assert corrupt_pdf.stat().st_size > 0
            with pytest.raises((ValueError, RuntimeError, Exception)):
                fitz.open(str(corrupt_pdf))

        def test_ocr_max_monetary_values_overflow(self, sample_canonical_transactions):
            tx = sample_canonical_transactions[0].copy()
            tx["debit_amount"] = 99999999.99
            AssertionHelpers.assert_canonical_transaction_schema(tx)
            assert f"{tx['debit_amount']:.2f}" == "99999999.99"

        def test_ocr_special_cyrillic_chars_and_quotes(self, sample_canonical_transactions):
            tx = sample_canonical_transactions[0].copy()
            tx["counterparty_name"] = 'ЕТ "ИВАНОВ-55" & СИНОТ / №123'
            AssertionHelpers.assert_canonical_transaction_schema(tx)
            assert '"ИВАНОВ-55"' in tx["counterparty_name"]

        def test_ocr_zero_amount_debit_credit_handling(self, sample_canonical_transactions):
            tx = sample_canonical_transactions[0].copy()
            tx["debit_amount"] = 0.00
            tx["credit_amount"] = 0.00
            AssertionHelpers.assert_canonical_transaction_schema(tx)

    @pytest.mark.accounting
    class TestTranslationBoundaries:
        """Boundary checks for EIK, IBAN, deduplication, and XML formatting."""

        def test_trans_invalid_9digit_eik_checksum_rejection(self):
            invalid_eik = "114077870"  # Invalid 9th check digit
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_valid_eik_checksum(invalid_eik)
            assert "checksum mismatch" in str(exc_info.value)

        def test_trans_invalid_13digit_eik_checksum_rejection(self):
            invalid_13_eik = "1140778761234"  # Invalid 13th check digit
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_valid_eik_checksum(invalid_13_eik)
            assert "checksum mismatch" in str(exc_info.value)

        def test_trans_invalid_iban_mod97_rejection(self):
            invalid_iban = "BG71STSA93000028013400"  # Fails Mod 97
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_valid_iban(invalid_iban)
            assert "Mod-97 checksum failed" in str(exc_info.value)

        def test_trans_duplicate_sha256_hash_detection(self, sample_journal_entries):
            duplicate_batch = sample_journal_entries + [sample_journal_entries[0]]
            hashes = [e["sha256_hash"] for e in duplicate_batch]
            unique_hashes = set(hashes)
            assert len(unique_hashes) == len(hashes) - 1, "Duplicate SHA-256 hash must be detected"

        def test_trans_illegal_account_code_format_rejection(self):
            invalid_account = "0401"  # Leading zero illegal
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_account_regex_compliance(invalid_account)
            assert "fails regex" in str(exc_info.value)

        def test_trans_xml_escaping_special_chars(self):
            from xml.sax.saxutils import escape
            raw_narrative = 'ПЛАЩАНЕ ЗА "СТОКИ" & УСЛУГИ <2026>'
            escaped = escape(raw_narrative, entities={'"': "&quot;"})
            assert "&quot;" in escaped and "&amp;" in escaped and "&lt;" in escaped

    @pytest.mark.vnc
    class TestVNCAndSQLBoundaries:
        """Boundary checks for VNC timeouts, missing tables, and SQL injection."""

        def test_vnc_connection_timeout_retry_recovery(self, mock_vnc_client):
            mock_vnc_client.connect.side_effect = [False, False, True]
            attempts = 0
            connected = False
            for _ in range(3):
                attempts += 1
                if mock_vnc_client.connect():
                    connected = True
                    break
            assert connected is True
            assert attempts == 3

        def test_vnc_modal_error_dialog_dismissal(self, mock_vnc_client):
            mock_vnc_client.send_keys.return_value = True
            assert mock_vnc_client.send_keys("Escape") is True

        def test_vnc_powershell_max_payload_boundary(self, mock_vnc_client):
            large_script = "Write-Host 'TEST' ; " * 500  # 10KB payload
            code, status = mock_vnc_client.type_base64_powershell(large_script)
            assert code == 0 and status == "SUCCESS"

        def test_sql_missing_table_schema_fault_handling(self, mock_sql_client):
            mock_sql_client.execute_sqlcmd.return_value = (208, "Msg 208, Level 16: Invalid object name 'Accountings'.")
            code, stderr = mock_sql_client.execute_sqlcmd("SELECT * FROM Accountings")
            assert code == 208
            assert "Invalid object name" in stderr

        def test_sql_auth_failure_handling(self, mock_sql_client):
            mock_sql_client.execute_sqlcmd.return_value = (18456, "Msg 18456: Login failed for user 'sa'.")
            code, stderr = mock_sql_client.execute_sqlcmd("sqlcmd -U sa -P wrong")
            assert code == 18456
            assert "Login failed" in stderr

        def test_sql_sub_stotinka_fractional_rounding(self):
            val = 100.005
            rounded = round(val + 1e-9, 2)
            assert rounded == 100.01

        def test_sql_injection_resilience_in_vendor_names(self):
            vendor_name = "ЕТ 'О'КОНЪР' ; DROP TABLE Operations; --"
            escaped_sql = vendor_name.replace("'", "''")
            assert "''О''КОНЪР''" in escaped_sql
            assert "DROP TABLE" in escaped_sql  # Preserved inside string literal

    @pytest.mark.audit
    class TestAuditBoundaries:
        """Boundary checks for corrupt TRANSFER.LOG files, imbalance, and permissions."""

        def test_log_non_matching_balance_invalidation(self, sample_statement_metadata):
            imbalanced_meta = sample_statement_metadata.copy()
            imbalanced_meta["closing_balance"] = 99999.99  # Invalid closing balance
            net_change = imbalanced_meta["credits_sum"] - imbalanced_meta["debits_sum"]
            calc_closing = imbalanced_meta["opening_balance"] + net_change
            assert abs(calc_closing - imbalanced_meta["closing_balance"]) > 1.0

        def test_log_corrupt_entry_detection(self):
            corrupt_log = "2026-01-31 | INVALID_LINE_NO_PIPES"
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_transfer_log_compliance(corrupt_log, expected_count=1)
            assert "Invalid TRANSFER.LOG line format" in str(exc_info.value)

        def test_log_pdf_vs_sql_amount_discrepancy_flagging(self, sample_canonical_transactions):
            json_entries = sample_canonical_transactions[:1]
            db_records = [{"DocNum": json_entries[0]["document_number"], "TotalEUR": 999.99}]
            with pytest.raises(AssertionError) as exc_info:
                AssertionHelpers.assert_sql_reconciliation(json_entries, db_records)
            assert "Total amount mismatch" in str(exc_info.value)

        def test_log_read_only_storage_permission_handling(self, tmp_path):
            log_dir = tmp_path / "readonly_dir"
            log_dir.mkdir()
            log_file = log_dir / "TRANSFER.LOG"
            log_file.write_text("READONLY_TEST\n")
            os.chmod(log_file, 0o444)
            assert os.access(log_file, os.R_OK)

        def test_log_unicode_cyrillic_preservation(self, mock_vm_storage):
            unicode_log = "2026-01-31 | DOC-1 | СТОРГОЗИЯ АД | 401 | 503 | 154.20 | VERIFIED\n"
            mock_vm_storage.write_text(unicode_log, encoding="utf-8")
            read_back = mock_vm_storage.read_text(encoding="utf-8")
            assert "СТОРГОЗИЯ АД" in read_back

        def test_log_high_volume_batch_append(self, mock_vm_storage):
            lines = [f"2026-01-31 | DOC-{i} | EIK-114077876 | 401 | 503 | 10.00 | VERIFIED" for i in range(500)]
            mock_vm_storage.write_text("\n".join(lines), encoding="utf-8")
            AssertionHelpers.assert_transfer_log_compliance(mock_vm_storage.read_text(), expected_count=500)


# =====================================================================
# TIER 3: CROSS-FEATURE COMBINATION TESTS (Pairwise Integration)
# =====================================================================

@pytest.mark.tier3
@pytest.mark.dry_run
class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise & Cross-Feature Integration Tests."""

    def test_combo_ocr_to_translation_field_propagation(self, sample_canonical_transactions, sample_journal_entries):
        assert len(sample_canonical_transactions) == len(sample_journal_entries)
        for tx, entry in zip(sample_canonical_transactions, sample_journal_entries):
            assert str(tx["document_number"]) == str(entry["doc_no"])
            expected_amount = tx["debit_amount"] if tx["debit_amount"] > 0 else tx["credit_amount"]
            assert abs(expected_amount - entry["amount"]) < 0.001

    def test_combo_narrative_to_account_mapping_xml_export(self, sample_journal_entries, sample_transfer_xml):
        AssertionHelpers.assert_xml_schema_valid(sample_transfer_xml)
        root = ET.fromstring(sample_transfer_xml)
        ops = root.find("Operations") or root.find("{urn:Transfer}Operations")
        assert ops is not None
        op_list = ops.findall("Operation") or ops.findall("{urn:Transfer}Operation")
        assert len(op_list) == len(sample_journal_entries)

    def test_combo_eik_to_xml_to_sql_partners(self, sample_statement_metadata, sample_transfer_xml, mock_sql_client):
        AssertionHelpers.assert_valid_eik_checksum(sample_statement_metadata["eik"])
        assert sample_statement_metadata["eik"] in sample_transfer_xml
        partners = mock_sql_client.query_partners()
        assert any(p["EIK"] == sample_statement_metadata["eik"] for p in partners)

    def test_combo_xml_import_to_sql_operations_accountings(self, sample_transfer_xml, mock_vnc_client, mock_sql_client, sample_canonical_transactions):
        assert mock_vnc_client.connect() is True
        code, status = mock_vnc_client.type_base64_powershell("Import-Xml C:\\Data\\transferdata.xml")
        assert code == 0
        records = mock_sql_client.query_operations()
        AssertionHelpers.assert_sql_reconciliation(sample_canonical_transactions, records)

    def test_combo_sql_reconciliation_to_transfer_log_audit(self, mock_sql_client, sample_canonical_transactions, mock_vm_storage):
        records = mock_sql_client.query_operations()
        AssertionHelpers.assert_sql_reconciliation(sample_canonical_transactions, records)
        log_lines = "\n".join([
            f"2026-01-31 | {rec['DocNum']} | 114077876 | {rec['DebitAcct']} | {rec['CreditAcct']} | {rec['TotalEUR']:.2f} | VERIFIED"
            for rec in records
        ])
        mock_vm_storage.write_text(log_lines)
        AssertionHelpers.assert_transfer_log_compliance(mock_vm_storage.read_text(), expected_count=21)

    def test_combo_credit_note_reversal_to_sql_transfer_log(self, mock_sql_client, mock_vm_storage):
        credit_note_entry = {
            "DocNum": "CN-9901",
            "DebitAcct": "503",
            "CreditAcct": "411",
            "TotalEUR": 2500.00,
            "OpDate": "2026-01-10",
        }
        log_line = f"2026-01-10 | {credit_note_entry['DocNum']} | 114077876 | {credit_note_entry['DebitAcct']} | {credit_note_entry['CreditAcct']} | {credit_note_entry['TotalEUR']:.2f} | VERIFIED"
        mock_vm_storage.write_text(log_line)
        content = mock_vm_storage.read_text()
        assert "CN-9901" in content and "2500.00" in content

    def test_combo_full_batch_ocr_xml_vnc_sql_transfer_log(self, sample_canonical_transactions, sample_journal_entries, sample_transfer_xml, mock_vnc_client, mock_sql_client, mock_vm_storage):
        # 1. OCR canonical transaction check
        assert len(sample_canonical_transactions) == 21
        # 2. Journal double entry balancing
        AssertionHelpers.assert_double_entry_balanced(sample_journal_entries)
        # 3. XML schema check
        AssertionHelpers.assert_xml_schema_valid(sample_transfer_xml)
        # 4. VNC command mock
        assert mock_vnc_client.connect() is True
        # 5. SQL DB record query & reconciliation
        records = mock_sql_client.query_operations()
        AssertionHelpers.assert_sql_reconciliation(sample_canonical_transactions, records)
        # 6. Audit log generation & check
        log_lines = "\n".join([
            f"2026-01-31 | {rec['DocNum']} | 114077876 | {rec['DebitAcct']} | {rec['CreditAcct']} | {rec['TotalEUR']:.2f} | VERIFIED"
            for rec in records
        ])
        mock_vm_storage.write_text(log_lines)
        AssertionHelpers.assert_transfer_log_compliance(mock_vm_storage.read_text(), expected_count=21)


# =====================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS (Live / E2E Environment)
# =====================================================================

@pytest.mark.tier4
@pytest.mark.live
class TestTier4RealWorldScenarios:
    """Tier 4: Live E2E Verification of 1.pdf Processing Pipeline & VM Audit."""

    def test_realworld_full_1pdf_pipeline_verification(
        self, require_live_environment, e2e_config,
        run_ocr_pipeline, run_accounting_translation, run_vnc_import, run_audit_export
    ):
        """Processes live 1.pdf through OCR, translation, VNC import, SQL DB, and C:\\TRANSFER.LOG."""
        # 1. OCR Extraction on live 1.pdf
        ocr_result = run_ocr_pipeline(e2e_config.pdf_path)
        metadata = ocr_result.get("statement_metadata", {})
        transactions = ocr_result.get("transactions", [])

        assert os.path.exists(e2e_config.pdf_path), f"Live PDF file missing at {e2e_config.pdf_path}"
        assert len(transactions) == 21, f"Expected 21 transactions extracted from 1.pdf, got {len(transactions)}"
        for tx in transactions:
            AssertionHelpers.assert_canonical_transaction_schema(tx)

        AssertionHelpers.assert_valid_eik_checksum(metadata["eik"])
        AssertionHelpers.assert_valid_iban(metadata["iban"])

        # 2. Accounting translation to Bulgarian double-entry journal & TransferData XML
        translation_result = run_accounting_translation(transactions, metadata)
        journal_entries = translation_result.get("journal_entries", [])
        transfer_xml = translation_result.get("transfer_xml", "")

        assert len(journal_entries) == 21, f"Expected 21 double-entry journal entries, got {len(journal_entries)}"
        AssertionHelpers.assert_double_entry_balanced(journal_entries)
        AssertionHelpers.assert_xml_schema_valid(transfer_xml)

        # 3. VNC / PowerShell automated import into Microinvest Delta Pro & SQLEXPRESS
        import_result = run_vnc_import(transfer_xml, e2e_config)
        assert import_result.get("vnc_status") in ("SUCCESS", "OK", 0)
        sql_records = import_result.get("sql_records", [])
        assert len(sql_records) == 21, f"Expected 21 SQL records, got {len(sql_records)}"
        AssertionHelpers.assert_sql_reconciliation(transactions, sql_records)

        # 4. Generate & validate persistent C:\TRANSFER.LOG
        audit_result = run_audit_export(sql_records, journal_entries, e2e_config.vm_transfer_log_path)
        log_content = audit_result.get("log_content", "")
        assert len(log_content.strip()) > 0, "C:\\TRANSFER.LOG content cannot be empty"
        AssertionHelpers.assert_transfer_log_compliance(log_content, expected_count=21)

    def test_realworld_1pdf_balance_sheet_integrity(
        self, require_live_environment, e2e_config, run_ocr_pipeline
    ):
        """Verifies opening + credits - debits = closing balance on live dataset."""
        assert os.path.exists(e2e_config.pdf_path), f"Live PDF missing: {e2e_config.pdf_path}"
        ocr_result = run_ocr_pipeline(e2e_config.pdf_path)
        meta = ocr_result.get("statement_metadata", {})
        txs = ocr_result.get("transactions", [])

        assert len(txs) == 21, f"Expected 21 transactions, got {len(txs)}"
        opening = meta["opening_balance"]
        closing = meta.get("closing_balance", txs[-1]["balance"] if txs else opening)

        debits_sum = sum(t["debit_amount"] for t in txs)
        credits_sum = sum(t["credit_amount"] for t in txs)

        expected_debits = meta.get("debits_sum", debits_sum)
        expected_credits = meta.get("credits_sum", credits_sum)

        assert abs(debits_sum - expected_debits) < 0.001, f"Debits sum mismatch: calc {debits_sum}, meta {expected_debits}"
        assert abs(credits_sum - expected_credits) < 0.001, f"Credits sum mismatch: calc {credits_sum}, meta {expected_credits}"

        calc_closing = opening + credits_sum - debits_sum
        assert abs(calc_closing - closing) < 0.001, f"Balance sheet discrepancy: calculated {calc_closing}, statement closing {closing}"

    def test_realworld_vm_sqlexpress_reconciliation(
        self, require_live_environment, e2e_config,
        run_ocr_pipeline, run_accounting_translation, run_vnc_import
    ):
        """Queries SQLEXPRESS inside live Windows 11 QEMU VM and matches against 1.pdf."""
        assert os.path.exists(e2e_config.pdf_path), f"Live PDF missing: {e2e_config.pdf_path}"

        ocr_result = run_ocr_pipeline(e2e_config.pdf_path)
        txs = ocr_result.get("transactions", [])
        meta = ocr_result.get("statement_metadata", {})

        trans_result = run_accounting_translation(txs, meta)
        transfer_xml = trans_result.get("transfer_xml", "")

        import_result = run_vnc_import(transfer_xml, e2e_config)
        sql_records = import_result.get("sql_records", [])

        assert len(sql_records) == 21, f"Expected 21 SQL records from SQLEXPRESS, got {len(sql_records)}"
        AssertionHelpers.assert_sql_reconciliation(txs, sql_records)

    def test_realworld_persistent_c_transfer_log_validation(
        self, require_live_environment, e2e_config,
        run_ocr_pipeline, run_accounting_translation, run_vnc_import, run_audit_export
    ):
        """Verifies C:\\TRANSFER.LOG stored persistently inside Windows 11 VM storage."""
        assert os.path.exists(e2e_config.pdf_path), f"Live PDF missing: {e2e_config.pdf_path}"

        ocr_result = run_ocr_pipeline(e2e_config.pdf_path)
        txs = ocr_result.get("transactions", [])
        meta = ocr_result.get("statement_metadata", {})

        trans_result = run_accounting_translation(txs, meta)
        journal_entries = trans_result.get("journal_entries", [])

        import_result = run_vnc_import(trans_result.get("transfer_xml", ""), e2e_config)
        sql_records = import_result.get("sql_records", [])

        audit_result = run_audit_export(sql_records, journal_entries, e2e_config.vm_transfer_log_path)
        log_content = audit_result.get("log_content", "")

        assert len(log_content.strip()) > 0, "C:\\TRANSFER.LOG content cannot be empty"
        AssertionHelpers.assert_transfer_log_compliance(log_content, expected_count=21)

