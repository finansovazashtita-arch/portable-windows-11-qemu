"""
Unit and Integration Tests for Multi-Bank OCR Extraction Engine.
"""

import os
import tempfile
import unittest

from src.ocr.multi_bank_extractor import (
    BankStatementFactory,
    PostbankStatementExtractor,
    UBBStatementExtractor,
    UniCreditStatementExtractor,
)


class TestMultiBankExtractors(unittest.TestCase):
    """Test suite for multi-bank statement extractors (UniCredit, UBB, Postbank, DSK)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_bank_statement_factory_unicredit_detection(self):
        pdf_path = os.path.join(self.temp_dir.name, "unicredit_test.pdf")
        # Generate dummy text content containing UniCredit header
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "УниКредит Булбанк АД\nИЗВЛЕЧЕНИЕ ПО СМЕТКА BG12UNCR80001122334455")
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "UNICREDIT")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, UniCreditStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bank_name"], "УниКредит Булбанк АД")
        self.assertEqual(dataset["statement_metadata"]["bic"], "UNCRBGSF")

    def test_bank_statement_factory_ubb_detection(self):
        pdf_path = os.path.join(self.temp_dir.name, "ubb_test.pdf")
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Обединена Българска Банка АД (ОББ)\nBG99UBBS90001234567890")
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "UBB")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, UBBStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bic"], "UBBSBGSF")

    def test_bank_statement_factory_postbank_detection(self):
        pdf_path = os.path.join(self.temp_dir.name, "postbank_test.pdf")
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Пощенска Банка / Eurobank Bulgaria\nBG55BPBI91001122334455")
        doc.save(pdf_path)
        doc.close()

        bank_code = BankStatementFactory.detect_bank_code(pdf_path)
        self.assertEqual(bank_code, "POSTBANK")

        extractor = BankStatementFactory.get_extractor(pdf_path)
        self.assertIsInstance(extractor, PostbankStatementExtractor)

        dataset = extractor.extract_and_build_dataset()
        self.assertEqual(dataset["statement_metadata"]["bic"], "BPBIBGSF")

    def test_dsk_realworld_fallback_detection(self):
        real_pdf = "/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06/1.pdf"
        if not os.path.exists(real_pdf):
            self.skipTest("Real DSK PDF not available")

        bank_code = BankStatementFactory.detect_bank_code(real_pdf)
        self.assertEqual(bank_code, "DSK")


if __name__ == "__main__":
    unittest.main()
