"""
Unit and Integration Tests for Multi-PDF Batch Processor Module.
"""

import json
import os
import tempfile
import unittest
import zipfile

from src.ocr.batch_processor import MultiPDFBatchProcessor


class TestMultiPDFBatchProcessor(unittest.TestCase):
    """Test suite for MultiPDFBatchProcessor."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.processor = MultiPDFBatchProcessor(temp_work_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_directory_for_pdfs(self):
        sub_dir = os.path.join(self.temp_dir.name, "pdf_folder")
        os.makedirs(sub_dir, exist_ok=True)

        pdf1 = os.path.join(sub_dir, "stmt1.pdf")
        pdf2 = os.path.join(sub_dir, "stmt2.PDF")
        txt1 = os.path.join(sub_dir, "notes.txt")

        for p in [pdf1, pdf2, txt1]:
            with open(p, "w") as f:
                f.write("DUMMY_CONTENT")

        found_pdfs = self.processor.scan_directory_for_pdfs(sub_dir)
        self.assertEqual(len(found_pdfs), 2)
        self.assertIn(pdf1, found_pdfs)
        self.assertIn(pdf2, found_pdfs)

    def test_extract_zip_archive(self):
        zip_path = os.path.join(self.temp_dir.name, "statements.zip")
        extract_dir = os.path.join(self.temp_dir.name, "extracted")

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("a.pdf", "PDF_DATA_A")
            zf.writestr("b.pdf", "PDF_DATA_B")
            zf.writestr("ignore.txt", "IGNORE")

        extracted_pdfs = self.processor.extract_zip_archive(zip_path, extract_to=extract_dir)
        self.assertEqual(len(extracted_pdfs), 2)
        self.assertTrue(os.path.exists(extract_dir))

    def test_process_batch_with_missing_and_corrupt_files_fault_tolerance(self):
        missing_file = os.path.join(self.temp_dir.name, "missing.pdf")
        corrupt_file = os.path.join(self.temp_dir.name, "corrupt.pdf")

        with open(corrupt_file, "w") as f:
            f.write("NOT_A_VALID_PDF_HEADER")

        pdf_list = [missing_file, corrupt_file]
        batch_res = self.processor.process_batch(pdf_list, batch_id="test_batch_fault")

        self.assertEqual(batch_res.total_files, 2)
        self.assertEqual(batch_res.successful_files, 0)
        self.assertEqual(batch_res.failed_files, 2)
        self.assertEqual(len(batch_res.file_results), 2)
        self.assertEqual(batch_res.file_results[0].status, "ERROR")
        self.assertEqual(batch_res.file_results[1].status, "ERROR")

    def test_process_realworld_dsk_statement_if_available(self):
        real_pdf = "/Volumes/KINGSTON/Persist/Scans/Storgozia AD/DSK_01-06/1.pdf"
        if not os.path.exists(real_pdf):
            self.skipTest(f"Real PDF not found at {real_pdf}")

        batch_res = self.processor.process_batch([real_pdf], batch_id="real_batch_1")
        self.assertEqual(batch_res.successful_files, 1)
        self.assertEqual(batch_res.total_transactions, 21)
        self.assertEqual(batch_res.grand_total_debits, 7329.50)
        self.assertEqual(batch_res.grand_total_credits, 3610.08)


if __name__ == "__main__":
    unittest.main()
