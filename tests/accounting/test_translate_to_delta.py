"""Unit tests for Bulgarian Double-Entry Accounting Translation Engine."""

import json
import os
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from src.accounting.translate_to_delta import (
    determine_accounts,
    generate_csv,
    generate_dedup_hash,
    generate_json,
    generate_xml,
    main,
    process_translation,
    translate_transactions,
    validate_eik,
    validate_iban,
)
from tests.e2e.test_e2e_pipeline import AssertionHelpers


class TestEIKValidation:
    """Tests for 9-digit and 13-digit EIK/BULSTAT Modulo 11 checksum algorithm."""

    def test_valid_9digit_eik(self):
        # Known valid 9-digit EIKs
        assert validate_eik("114077876") is True  # Statement holder
        assert validate_eik("121404164") is True

    def test_invalid_9digit_eik(self):
        assert validate_eik("114077877") is False
        assert validate_eik("123456789") is False

    def test_valid_13digit_eik(self):
        # 13-digit EIK: 9-digit (114077876) + digits 9..12 (0016)
        assert validate_eik("1140778760016") is True

    def test_invalid_13digit_eik(self):
        assert validate_eik("1140778760017") is False

    def test_invalid_input_types_and_formats(self):
        assert validate_eik(None) is False
        assert validate_eik(123456789) is False
        assert validate_eik("ABCDEFGHI") is False
        assert validate_eik("12345") is False
        assert validate_eik("123456789012345") is False


class TestIBANValidation:
    """Tests for Bulgarian IBAN Modulo 97 (ISO 7064) validation."""

    def test_valid_bg_ibans(self):
        assert validate_iban("BG71STSA93000028013479") is True
        assert validate_iban("BG37UNCR76301025139612") is True
        assert validate_iban("BG08UBBS81551010343647") is True
        assert validate_iban("BG40IORT73801036825800") is True
        assert validate_iban("BG52UNCR70001500670905") is True

    def test_iban_formatting_with_spaces(self):
        assert validate_iban("BG71 STSA 9300 0028 0134 79") is True

    def test_invalid_bg_ibans(self):
        assert validate_iban("BG71STSA93000028013478") is False  # Bad checksum
        assert validate_iban("US71STSA93000028013479") is False  # Non-BG country
        assert validate_iban("BG71STSA9300002801") is False       # Too short
        assert validate_iban("0000000072911303") is False         # Internal bank ref
        assert validate_iban(None) is False


class TestDeduplicationHash:
    """Tests for SHA-256 deduplication hashing."""

    def test_hash_reproducibility(self):
        h1 = generate_dedup_hash("114077876", "12101", 44.05)
        h2 = generate_dedup_hash("114077876", "12101", 44.05)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_uniqueness(self):
        h1 = generate_dedup_hash("114077876", "12101", 44.05)
        h2 = generate_dedup_hash("114077876", "12102", 44.05)
        h3 = generate_dedup_hash("114077876", "12101", 44.06)
        assert h1 != h2
        assert h1 != h3


class TestAccountMappingRules:
    """Tests for double-entry Bulgarian Chart of Accounts mapping logic."""

    def test_supplier_payment_mapping(self):
        suppliers = [
            "ЗОРА М.М.С. ООД",
            "АУТО БОХЕМИЯ АД",
            "ТОПЛОФИКАЦИЯ ПЛЕВЕН АД",
            "ПЕТРОМАКС СЕКЮРИТИ ГРУП ООД",
            "ЕЛЕКТРОХОЛД ТРЕЙД ЕАД",
            "ФЛОКСЕР ЕООД",
            "АЙТИ ДИЗАЙН 2020 ЕООД",
            "ЕТИЕН ЕООД",
            "ВИК ЕООД",
        ]
        for name in suppliers:
            debit, credit = determine_accounts(name, "ФРА 123", 100.0, 0.0)
            assert debit == "401", f"Supplier '{name}' must map to Debit 401"
            assert credit == "503", f"Supplier '{name}' must map to Credit 503"

    def test_customer_receipt_mapping(self):
        customers = [
            "НИКОЛАЙ ВЕНКОВ ТРИФОНОВ",
            "ПОЛИХИМКОМЕРС 1 ЕООД",
            "ДИАЛ ИНТЕРГРАФИК ЕООД",
            "ЙОРДАН ИВАНОВ ЙОТОВ",
            "ГЕМА АМ ЕООД",
            "УЛТРОН СОЛАР ЕООД",
        ]
        for name in customers:
            debit, credit = determine_accounts(name, "7000000763", 0.0, 200.0)
            assert debit == "503", f"Customer '{name}' receipt must map to Debit 503"
            assert credit == "411", f"Customer '{name}' receipt must map to Credit 411"

    def test_tax_and_social_security_mapping(self):
        # ДДФЛ -> 454
        debit, credit = determine_accounts("НАП", "ДДФЛ НАП 95001", 47.48, 0.0)
        assert debit == "454" and credit == "503"

        # ДОО / ДЗПО / NCC -> 455
        debit, credit = determine_accounts("НАП", "ДЗПО НАП 11801", 27.53, 0.0)
        assert debit == "455" and credit == "503"

        debit, credit = determine_accounts("НАП", "ДОО НАП 112001", 111.24, 0.0)
        assert debit == "455" and credit == "503"

        debit, credit = determine_accounts("НАП", "NCC WITHDRAWAL 12101", 44.05, 0.0)
        assert debit == "455" and credit == "503"

    def test_bank_fees_mapping(self):
        debit, credit = determine_accounts("БАНКА ДСК ЕАД", "ОТСТЪПКА ИЗПЪЛНЕНО УСЛОВИЕ ПЛАН ДСК НАЧАЛО", 2.05, 0.0)
        assert debit == "621" and credit == "503"

    def test_rent_expense_mapping(self):
        debit, credit = determine_accounts("HAN KRUM - BG EOOD", "НАЕМ М. ФЕВРУАРИ 01.", 454.21, 0.0)
        assert debit == "602" and credit == "503"


class TestTranslationPipelineExecution:
    """Tests full translation execution against data/extracted_transactions.json."""

    @pytest.fixture
    def sample_json_data(self):
        input_path = "data/extracted_transactions.json"
        assert os.path.exists(input_path), "Input extracted_transactions.json missing"
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_translate_transactions(self, sample_json_data):
        metadata, journal_entries = translate_transactions(sample_json_data)
        assert metadata["account_holder"] == "СТОРГОЗИЯ АД"
        assert metadata["eik"] == "114077876"
        assert len(journal_entries) == 21

        # Check double-entry balance invariant via AssertionHelpers
        AssertionHelpers.assert_double_entry_balanced(journal_entries)

        # Reconcile total turnovers
        total_debit_turnover = sum(e["amount"] for e in journal_entries if e["credit_account"] == "503")
        total_credit_turnover = sum(e["amount"] for e in journal_entries if e["debit_account"] == "503")
        assert abs(total_debit_turnover - 7329.50) < 0.01
        assert abs(total_credit_turnover - 3610.08) < 0.01

    def test_generate_xml_output(self, sample_json_data):
        metadata, journal_entries = translate_transactions(sample_json_data)
        xml_content = generate_xml(metadata, journal_entries)

        # Validate with AssertionHelpers schema check
        AssertionHelpers.assert_xml_schema_valid(xml_content)

        root = ET.fromstring(xml_content)
        assert "urn:Transfer" in root.tag
        header = root.find("{urn:Transfer}Header")
        assert header is not None
        assert header.find("{urn:Transfer}CompanyEIK").text == "114077876"

    def test_generate_json_output(self, sample_json_data):
        metadata, journal_entries = translate_transactions(sample_json_data)
        json_payload = generate_json(metadata, journal_entries)

        assert "statement_metadata" in json_payload
        assert "journal_entries" in json_payload
        assert "summary" in json_payload
        assert len(json_payload["journal_entries"]) == 21
        assert json_payload["summary"]["closing_balance"] == 2163.87

    def test_generate_csv_output(self, sample_json_data):
        metadata, journal_entries = translate_transactions(sample_json_data)
        csv_content = generate_csv(journal_entries)

        lines = [line for line in csv_content.strip().split("\n") if line]
        assert len(lines) == 22  # 1 header + 21 rows
        assert "ItemNo;PostingDate;ValueDate;DocumentNumber" in lines[0]

    def test_process_translation_file_creation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            written_files = process_translation("data/extracted_transactions.json", tmp_dir)
            assert os.path.exists(written_files["xml"])
            assert os.path.exists(written_files["json"])
            assert os.path.exists(written_files["csv"])

            with open(written_files["xml"], "r", encoding="utf-8") as f:
                AssertionHelpers.assert_xml_schema_valid(f.read())

            with open(written_files["json"], "r", encoding="utf-8") as f:
                data = json.load(f)
                assert len(data["journal_entries"]) == 21

    def test_cli_main(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_args = [
                "translate_to_delta.py",
                "--input",
                "data/extracted_transactions.json",
                "--output-dir",
                tmp_dir,
            ]
            with patch("sys.argv", test_args):
                main()

            assert os.path.exists(os.path.join(tmp_dir, "microinvest_transferdata.xml"))
            assert os.path.exists(os.path.join(tmp_dir, "journal_entries.json"))
            assert os.path.exists(os.path.join(tmp_dir, "delta_bg_export.csv"))


class TestEdgeCaseRemediations:
    """Regression unit tests covering the 5 edge-case remediations."""

    def test_iban_whitespace_and_newline_stripping(self):
        """Edge case 1a: IBAN with trailing newlines and whitespace is stripped and validated without crash."""
        assert validate_iban("BG71STSA93000028013479\n") is True
        assert validate_iban("  BG71STSA93000028013479\r\n\t") is True
        assert validate_iban("BG71STSA93000028013478\n") is False  # Invalid checksum

    def test_null_narrative_and_field_handling(self):
        """Edge case 1b: Generators gracefully handle None/null for narrative, counterparty, doc_no, etc."""
        null_payload = {
            "statement_metadata": {
                "account_holder": "ТЕСТ ООД",
                "eik": "114077876",
                "opening_balance": None,
            },
            "transactions": [
                {
                    "item_id": 1,
                    "posting_date": "05.01.2026",
                    "value_date": None,
                    "document_number": None,
                    "counterparty_name": None,
                    "counterparty_iban": None,
                    "debit_amount": 10.00,
                    "credit_amount": None,
                    "narrative_description": None,
                    "currency": None,
                }
            ],
        }
        metadata, journal_entries = translate_transactions(null_payload)
        assert len(journal_entries) == 1
        entry = journal_entries[0]
        assert entry["narrative"] == ""
        assert entry["counterparty_name"] == ""
        assert entry["doc_no"] == ""
        assert entry["currency"] == "EUR"

        # Check exporters do not crash on entries containing None
        raw_null_entries = [
            {
                "item_id": 1,
                "posting_date": None,
                "value_date": None,
                "doc_no": None,
                "counterparty_name": None,
                "counterparty_iban": None,
                "debit_account": "503",
                "credit_account": "401",
                "amount": None,
                "currency": None,
                "narrative": None,
                "dedup_hash": None,
            }
        ]
        xml_out = generate_xml(None, raw_null_entries)
        assert "<TransferData" in xml_out

        json_out = generate_json(None, raw_null_entries)
        assert len(json_out["journal_entries"]) == 1

        csv_out = generate_csv(raw_null_entries)
        lines = csv_out.strip().split("\n")
        assert len(lines) == 2

    def test_csv_column_injection_escaping(self):
        """Edge case 1c: Semicolons in string fields are replaced/escaped so CSV maintains exactly 12 columns."""
        entries_with_semicolons = [
            {
                "item_id": 1,
                "posting_date": "05.01.2026",
                "value_date": "05.01.2026",
                "doc_no": "DOC#123;456",
                "counterparty_name": "ФИРМА \"ТЕСТ & КУПУВАЧ;1\" <OOD>",
                "counterparty_iban": "BG37UNCR76301025139612",
                "debit_account": "401",
                "credit_account": "503",
                "amount": 150.75,
                "currency": "EUR",
                "narrative": "ПЛАЩАНЕ; ЗА УСЛУГИ ; НАЕМ",
                "dedup_hash": "hash123",
            }
        ]
        csv_content = generate_csv(entries_with_semicolons)
        lines = csv_content.strip().split("\n")
        assert len(lines) == 2  # header + 1 row
        row_fields = lines[1].split(";")
        assert len(row_fields) == 12, f"Expected exactly 12 columns, got {len(row_fields)}"

    def test_csv_multiline_corruption_escaping(self):
        """Edge case 1d: Line breaks in narrative or counterparty name are replaced with spaces."""
        entries_with_newlines = [
            {
                "item_id": 1,
                "posting_date": "05.01.2026",
                "value_date": "05.01.2026",
                "doc_no": "DOC123",
                "counterparty_name": "ФИРМА\nООД",
                "counterparty_iban": "BG37UNCR76301025139612",
                "debit_account": "401",
                "credit_account": "503",
                "amount": 100.00,
                "currency": "EUR",
                "narrative": "ПЛАЩАНЕ\nЗА УСЛУГИ\r\nНАЕМ 2026",
                "dedup_hash": "hash123",
            }
        ]
        csv_content = generate_csv(entries_with_newlines)
        lines = csv_content.strip().split("\n")
        assert len(lines) == 2, f"Expected 2 lines (header + 1 row), got {len(lines)} lines"
        assert "\n" not in lines[1]
        assert "\r" not in lines[1]

    def test_dedup_hash_uniqueness_for_duplicate_amounts_with_empty_doc(self):
        """Edge case 1e: Duplicate amounts with empty document numbers produce distinct SHA-256 hashes."""
        h1 = generate_dedup_hash(
            statement_eik="114077876",
            doc_num="",
            amount=2.05,
            posting_date="05.01.2026",
            counterparty_iban="BG71STSA93000028013479",
            narrative="ТАКСА ОБСЛУЖВАНЕ 1",
            item_id=1,
        )
        h2 = generate_dedup_hash(
            statement_eik="114077876",
            doc_num="",
            amount=2.05,
            posting_date="06.01.2026",
            counterparty_iban="BG71STSA93000028013479",
            narrative="ТАКСА ОБСЛУЖВАНЕ 2",
            item_id=2,
        )
        assert h1 != h2, "Hashes for distinct transactions with empty doc_num and identical amount must be unique"
        assert len(h1) == 64
        assert len(h2) == 64

