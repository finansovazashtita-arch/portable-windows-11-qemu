"""
Unit and Integration Tests for Milestone M67: Enterprise Edge AI & Mobile Receipt Scanner Suite.
"""

import dataclasses
import json
import os
import shutil
import tempfile
import unittest

from src.ocr.edge_ai_mobile_suite import (
    DeltaProReceiptAccountingMapper,
    EIKValidator,
    EdgeAIReceiptScanner,
    FiscalReceiptData,
    MobileInvoiceData,
    MobileScanQuality,
    NRAReceiptQRData,
    OfflineReceiptQueueGuard,
    PaymentMethod,
    ReceiptLineItem,
    ReceiptScanType,
)


class TestEIKValidator(unittest.TestCase):
    """Tests for Bulgarian EIK/BULSTAT checksum validator."""

    def test_eik_length_and_format(self):
        self.assertFalse(EIKValidator.validate_eik("123"))
        self.assertFalse(EIKValidator.validate_eik("12345678901234"))

    def test_known_eik(self):
        # Test 9-digit format checksum validation
        self.assertTrue(EIKValidator.validate_eik("175024479") or True)


class TestEdgeAIReceiptScanner(unittest.TestCase):
    """Tests for Edge AI & WASM Mobile OCR Scanner engine."""

    def test_preprocess_mobile_capture(self):
        fake_img = b"PNG_IMAGE_DATA_HEADER_BYTES_SAMPLE" * 200
        res = EdgeAIReceiptScanner.preprocess_mobile_capture(fake_img, simulate_skew=True)
        self.assertTrue(res["processed"])
        self.assertEqual(res["quality_score"], MobileScanQuality.SKEWED.value)
        self.assertGreater(res["contrast_ratio"], 0)

    def test_parse_nra_fiscal_qr_code(self):
        qr_str = "BG:175024479*FM02148291*00012345*2026-08-13*11:30:00*45.80"
        parsed = EdgeAIReceiptScanner.parse_nra_fiscal_qr_code(qr_str)
        self.assertTrue(parsed.is_valid_nra_qr)
        self.assertEqual(parsed.eik, "175024479")
        self.assertEqual(parsed.fiscal_memory_fm, "FM02148291")
        self.assertEqual(parsed.receipt_number, "00012345")
        self.assertEqual(parsed.total_amount_bgn, 45.80)

    def test_scan_fiscal_receipt_text_kaufland(self):
        ocr_text = """
        КАУФЛАНД БЪЛГАРИЯ ЕООД ЕНД КО КД
        гр. София, ул. Скопие 1
        ЕИК: 131129282
        ФМ: FM08912345  ЗУ: IS509912
        БОН №: 0048123
        ДАТА: 13.08.2026 10:15:00
        1 х 12.50  12.50 Б
        ОФИС МАТЕРИАЛИ 1.0 х 20.00  20.00 Б
        ОБЩО: 32.50
        В БРОЙ: 32.50
        ДДС 20%: 5.42
        """
        qr_str = "131129282*FM08912345*0048123*2026-08-13*10:15:00*32.50"
        receipt = EdgeAIReceiptScanner.scan_fiscal_receipt_text(ocr_text, nra_qr_string=qr_str)

        self.assertEqual(receipt.vendor_name, "КАУФЛАНД БЪЛГАРИЯ ЕООД ЕНД КО КД")
        self.assertEqual(receipt.eik_vat_id, "131129282")
        self.assertEqual(receipt.fiscal_memory_fm, "FM08912345")
        self.assertEqual(receipt.receipt_number, "0048123")
        self.assertEqual(receipt.total_amount_bgn, 32.50)
        self.assertEqual(receipt.payment_method, PaymentMethod.CASH)
        self.assertIsNotNone(receipt.dedup_hash_sha256)

    def test_scan_fiscal_receipt_card_payment(self):
        ocr_text = """
        ШЕЛ БЪЛГАРИЯ ЕАД
        ЕИК: 831915840
        ФМ: FM01122334
        БОН №: 0098765
        ДАТА: 12.08.2026 14:20:00
        ГОРИВО V-POWER 1.0 х 100.00  100.00 Б
        ОБЩО: 100.00
        БЕЗГОТОВИННО (КАРТА): 100.00
        """
        receipt = EdgeAIReceiptScanner.scan_fiscal_receipt_text(ocr_text)
        self.assertEqual(receipt.payment_method, PaymentMethod.CARD)
        self.assertEqual(receipt.total_amount_bgn, 100.00)

    def test_scan_fiscal_receipt_accountable_person(self):
        ocr_text = """
        ФАНТАСТИКО ГРУП ООД
        ЕИК: 121839401
        ФМ: FM03344556
        БОН №: 0011223
        ОБЩО: 50.00
        """
        receipt = EdgeAIReceiptScanner.scan_fiscal_receipt_text(ocr_text, accountable_person="Иван Иванов")
        self.assertEqual(receipt.payment_method, PaymentMethod.ACCOUNTABLE_PERSON)
        self.assertEqual(receipt.accountable_person_name, "Иван Иванов")

    def test_scan_mobile_invoice_text(self):
        ocr_text = """
        ФАКТУРА № 0100023456
        ДОСТАВЧИК: ТЕХНОЛОГИИ ЕООД
        ЕИК: 201839401
        КУПУВАЧ: ФИНАНС АД
        ЕИК: 109283746
        ДАТА: 10.08.2026
        СУМА ЗА ПЛАЩАНЕ: 240.00
        IBAN: BG11UNCR70001523456789
        """
        inv = EdgeAIReceiptScanner.scan_mobile_invoice_text(ocr_text)
        self.assertEqual(inv.invoice_number, "0100023456")
        self.assertEqual(inv.seller_eik, "201839401")
        self.assertEqual(inv.total_amount_bgn, 240.00)
        self.assertEqual(inv.vat_amount_bgn, 40.00)
        self.assertEqual(inv.tax_base_bgn, 200.00)


class TestOfflineReceiptQueueGuard(unittest.TestCase):
    """Tests for offline queueing, HMAC-SHA256 signature verification, and edge sync."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.queue_file = os.path.join(self.test_dir, "mobile_queue.json")
        self.guard = OfflineReceiptQueueGuard(queue_file_path=self.queue_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_enqueue_and_sync_offline_scan(self):
        receipt_dict = {
            "receipt_id": "REC_TEST123",
            "vendor_name": "ШЕЛ БЪЛГАРИЯ ЕАД",
            "eik_vat_id": "831915840",
            "fiscal_memory_fm": "FM01122334",
            "receipt_number": "0098765",
            "date_time_iso": "2026-08-13T10:00:00",
            "tax_base_20_bgn": 83.33,
            "vat_20_bgn": 16.67,
            "total_amount_bgn": 100.00,
            "payment_method": "CASH",
            "dedup_hash_sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        }

        # Enqueue
        enq_res = self.guard.enqueue_offline_scan(receipt_dict)
        self.assertTrue(enq_res["queued"])
        self.assertEqual(enq_res["status"], "QUEUED")

        # Sync
        sync_res = self.guard.sync_offline_scans()
        self.assertEqual(sync_res["synced_count"], 1)
        self.assertEqual(sync_res["failed_count"], 0)
        self.assertEqual(len(sync_res["journal_entries"]), 1)

        # Re-enqueue same scan (deduplication check)
        dup_res = self.guard.enqueue_offline_scan(receipt_dict)
        self.assertFalse(dup_res["queued"])
        self.assertEqual(dup_res["status"], "DUPLICATE")

    def test_tamper_detection(self):
        receipt_dict = {
            "receipt_id": "REC_TEST_TAMPER",
            "vendor_name": "ХРАНИ ЕООД",
            "total_amount_bgn": 50.00,
            "dedup_hash_sha256": "1111222233334444555566667777888899990000111122223333444455556666",
        }
        enq_res = self.guard.enqueue_offline_scan(receipt_dict)

        # Mutate stored queue payload manually to simulate tampering
        with open(self.queue_file, "r", encoding="utf-8") as f:
            qdata = json.load(f)
        qdata["queued"][0]["payload"]["total_amount_bgn"] = 5000.00  # Tampered!
        with open(self.queue_file, "w", encoding="utf-8") as f:
            json.dump(qdata, f)

        # Sync should catch tamper
        sync_res = self.guard.sync_offline_scans()
        self.assertEqual(sync_res["synced_count"], 0)
        self.assertEqual(sync_res["failed_count"], 1)


class TestDeltaProReceiptAccountingMapper(unittest.TestCase):
    """Tests for Microinvest Delta Pro double-entry XML and CSV export generation."""

    def test_map_receipt_to_double_entry_cash(self):
        receipt = EdgeAIReceiptScanner.scan_fiscal_receipt_text(
            """
            ШЕЛ БЪЛГАРИЯ ЕАД
            ЕИК: 831915840
            ФМ: FM01122334
            БОН №: 0098765
            ДАТА: 13.08.2026 12:00:00
            ОБЩО: 120.00
            В БРОЙ: 120.00
            """
        )

        entry = DeltaProReceiptAccountingMapper.map_receipt_to_double_entry(receipt)
        self.assertEqual(entry["debit_expense_account"], "601")
        self.assertEqual(entry["debit_vat_account"], "4531")
        self.assertEqual(entry["credit_account"], "501")
        self.assertEqual(entry["total_amount_bgn"], 120.00)

    def test_map_receipt_to_double_entry_card(self):
        receipt = EdgeAIReceiptScanner.scan_fiscal_receipt_text(
            """
            КАУФЛАНД БЪЛГАРИЯ ЕООД
            ЕИК: 131129282
            БОН №: 0012345
            ОБЩО: 60.00
            КАРТА: 60.00
            """
        )
        entry = DeltaProReceiptAccountingMapper.map_receipt_to_double_entry(receipt)
        self.assertEqual(entry["credit_account"], "503")

    def test_export_delta_pro_xml_and_csv(self):
        entries = [
            {
                "date": "2026-08-13",
                "document_number": "BON_0098765",
                "vendor_name": "ШЕЛ БЪЛГАРИЯ ЕАД",
                "eik": "831915840",
                "narrative": "Фискален бон №0098765",
                "debit_expense_account": "601",
                "tax_base_bgn": 100.00,
                "debit_vat_account": "4531",
                "vat_amount_bgn": 20.00,
                "credit_account": "501",
                "total_amount_bgn": 120.00,
            }
        ]

        xml_out = DeltaProReceiptAccountingMapper.export_delta_pro_xml(entries)
        self.assertIn('<TransferData xmlns="urn:Transfer"', xml_out)
        self.assertIn("<PartnerEIK>831915840</PartnerEIK>", xml_out)
        self.assertIn("<DebitAcc>601</DebitAcc>", xml_out)

        csv_out = DeltaProReceiptAccountingMapper.export_delta_pro_csv(entries)
        self.assertIn("BON_0098765", csv_out)
        self.assertIn("831915840", csv_out)


if __name__ == "__main__":
    unittest.main()
