"""
Unit and Integration Test Suite for src/ocr/extract_dsk_statement.py.

Verifies:
- PDF page rendering via PyMuPDF (300 DPI)
- Tesseract OCR execution (Cyrillic + Latin text recovery)
- Header metadata extraction
- Transaction line items extraction (21 items)
- Mathematical balance reconciliation
- JSON schema compliance
- CLI invocation and exit codes
- Directory creation and atomic writing
"""

import json
import os
import subprocess
import tempfile
import unittest
from PIL import Image
import jsonschema

from src.ocr.extract_dsk_statement import (
    DSKStatementExtractor,
    StatementMetadata,
    TransactionItem,
    normalize_date,
    parse_float_amount,
    EXIT_SUCCESS,
    EXIT_ERR_INPUT_NOT_FOUND,
)


SAMPLE_PDF_PATH = "/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06/1.pdf"
CANONICAL_JSON_PATH = "data/extracted_transactions.json"


class TestDSKStatementExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = DSKStatementExtractor(
            pdf_path=SAMPLE_PDF_PATH,
            dpi=300,
            tessdata_dir="/opt/homebrew/share/tessdata",
            strict=True
        )

    def test_normalize_date(self):
        self.assertEqual(normalize_date("05.01.2026"), "2026-01-05")
        self.assertEqual(normalize_date("31.12.2025"), "2025-12-31")
        self.assertEqual(normalize_date("2026-01-05"), "2026-01-05")
        with self.assertRaises(ValueError):
            normalize_date("invalid-date")

    def test_parse_float_amount(self):
        self.assertEqual(parse_float_amount("5 883.29"), 5883.29)
        self.assertEqual(parse_float_amount("1 472,64"), 1472.64)
        self.assertEqual(parse_float_amount("44,05"), 44.05)
        self.assertEqual(parse_float_amount("-"), 0.0)
        self.assertEqual(parse_float_amount("0,00"), 0.0)

    def test_pdf_rendering(self):
        img = self.extractor.render_pdf_page(page_index=0)
        self.assertIsInstance(img, Image.Image)
        self.assertGreater(img.width, 2000)
        self.assertGreater(img.height, 3000)

    def test_tesseract_ocr_execution(self):
        img = self.extractor.render_pdf_page(page_index=0)
        raw_text, tsv_words = self.extractor.run_ocr(img)
        self.assertIn("СТОРГОЗИЯ АД", raw_text)
        self.assertGreater(len(tsv_words), 50)
        self.assertIn("left", tsv_words[0])
        self.assertIn("top", tsv_words[0])
        self.assertIn("text", tsv_words[0])

    def test_parse_header_metadata(self):
        img = self.extractor.render_pdf_page(page_index=0)
        raw_text, _ = self.extractor.run_ocr(img)
        metadata = self.extractor.parse_header_metadata(raw_text)

        self.assertEqual(metadata.account_holder, "СТОРГОЗИЯ АД")
        self.assertEqual(metadata.eik, "114077876")
        self.assertEqual(metadata.iban, "BG71STSA93000028013479")
        self.assertEqual(metadata.currency, "EUR")
        self.assertEqual(metadata.period_start, "01.01.2026")
        self.assertEqual(metadata.period_end, "31.01.2026")
        self.assertEqual(metadata.opening_balance, 5883.29)

    def test_extract_transactions_count_and_integrity(self):
        img = self.extractor.render_pdf_page(page_index=0)
        raw_text, tsv_words = self.extractor.run_ocr(img)
        transactions = self.extractor.extract_transactions(raw_text, tsv_words, 5883.29)

        self.assertEqual(len(transactions), 21)

        # Check item IDs 1..21
        item_ids = [t.item_id for t in transactions]
        self.assertEqual(item_ids, list(range(1, 22)))

        # Verify item 1 details
        t1 = transactions[0]
        self.assertEqual(t1.item_id, 1)
        self.assertEqual(t1.posting_date, "2026-01-05")
        self.assertEqual(t1.counterparty_name, "НАП")
        self.assertEqual(t1.counterparty_iban, "BG16BNBG966180001")
        self.assertEqual(t1.debit_amount, 44.05)
        self.assertEqual(t1.credit_amount, 0.0)
        self.assertEqual(t1.currency, "EUR")
        self.assertEqual(t1.balance, 5839.24)

        # Verify item 21 details
        t21 = transactions[-1]
        self.assertEqual(t21.item_id, 21)
        self.assertEqual(t21.posting_date, "2026-01-21")
        self.assertEqual(t21.counterparty_name, "ВИК ЕООД")
        self.assertEqual(t21.counterparty_iban, "BG10BGUS91601011840601")
        self.assertEqual(t21.debit_amount, 53.95)
        self.assertEqual(t21.credit_amount, 0.0)
        self.assertEqual(t21.balance, 2163.87)

    def test_mathematical_consistency(self):
        metadata = StatementMetadata(
            account_holder="СТОРГОЗИЯ АД",
            eik="114077876",
            iban="BG71STSA93000028013479",
            currency="EUR",
            period_start="01.01.2026",
            period_end="31.01.2026",
            opening_balance=5883.29
        )
        img = self.extractor.render_pdf_page(page_index=0)
        raw_text, tsv_words = self.extractor.run_ocr(img)
        txs = self.extractor.extract_transactions(raw_text, tsv_words, 5883.29)

        ending_bal = self.extractor.validate_mathematical_consistency(metadata, txs)
        self.assertEqual(ending_bal, 2163.87)

        # Test math failure on corrupted debit
        corrupted_txs = list(txs)
        corrupted_txs[0] = TransactionItem(
            item_id=1,
            posting_date="2026-01-05",
            value_date="2026-01-05",
            counterparty_name="НАП",
            counterparty_iban="BG16BNBG966180001",
            document_number="12101",
            debit_amount=999.99,
            credit_amount=0.0,
            narrative_description="Corrupted",
            currency="EUR",
            balance=5000.00
        )
        with self.assertRaises(ValueError):
            self.extractor.validate_mathematical_consistency(metadata, corrupted_txs)

    def test_canonical_json_schema_compliance(self):
        with open(CANONICAL_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        schema = {
            "type": "object",
            "required": ["statement_metadata", "transactions"],
            "properties": {
                "statement_metadata": {
                    "type": "object",
                    "required": [
                        "account_holder", "eik", "iban", "currency",
                        "period_start", "period_end", "opening_balance"
                    ],
                    "properties": {
                        "account_holder": {"type": "string"},
                        "eik": {"type": "string"},
                        "iban": {"type": "string"},
                        "currency": {"type": "string"},
                        "period_start": {"type": "string"},
                        "period_end": {"type": "string"},
                        "opening_balance": {"type": "number"}
                    }
                },
                "transactions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "item_id", "posting_date", "value_date", "counterparty_name",
                            "counterparty_iban", "document_number", "debit_amount",
                            "credit_amount", "narrative_description", "currency", "balance"
                        ],
                        "properties": {
                            "item_id": {"type": "integer"},
                            "posting_date": {"type": "string"},
                            "value_date": {"type": "string"},
                            "counterparty_name": {"type": "string"},
                            "counterparty_iban": {"type": "string"},
                            "document_number": {"type": "string"},
                            "debit_amount": {"type": "number"},
                            "credit_amount": {"type": "number"},
                            "narrative_description": {"type": "string"},
                            "currency": {"type": "string"},
                            "balance": {"type": "number"}
                        }
                    }
                }
            }
        }

        jsonschema.validate(instance=data, schema=schema)

    def test_cli_execution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = os.path.join(tmp_dir, "nested", "extracted.json")
            cmd = [
                "python3",
                "src/ocr/extract_dsk_statement.py",
                "--pdf-path", SAMPLE_PDF_PATH,
                "--output", out_file
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, EXIT_SUCCESS)
            self.assertTrue(os.path.exists(out_file))

            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data["transactions"]), 21)

    def test_nonexistent_input_file_exit_code(self):
        cmd = [
            "python3",
            "src/ocr/extract_dsk_statement.py",
            "--pdf-path", "/nonexistent/path/file.pdf"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, EXIT_ERR_INPUT_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
