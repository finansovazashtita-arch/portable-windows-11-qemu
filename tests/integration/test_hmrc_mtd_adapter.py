"""
Unit tests for UK HMRC MTD VAT Adapter Engine.
"""

import unittest
from src.integration.hmrc_mtd_adapter import (
    HMRCMTDAdapter,
    HMRCVATReturn,
)


class TestHMRCMTDAdapter(unittest.TestCase):
    """Test suite for HMRCMTDAdapter."""

    def test_generate_fraud_prevention_headers(self):
        headers = HMRCMTDAdapter.generate_fraud_prevention_headers(
            client_ip="192.168.1.100",
            vendor_software_version="FinansProtect/2.5",
        )

        self.assertIn("Gov-Client-Connection-Method", headers)
        self.assertEqual(headers["Gov-Client-Connection-Method"], "DESKTOP_APP_DIRECT")
        self.assertIn("Gov-Vendor-Version", headers)

    def test_build_vat_return_payload(self):
        vat_ret = HMRCVATReturn(
            period_key="18A1",
            vat_due_sales=100.0,
            vat_due_acquisitions=0.0,
            total_vat_due=100.0,
            vat_reclaimed_input=30.0,
            net_vat_due=70.0,
            total_value_sales_ex_vat=500.0,
            total_value_purchases_ex_vat=150.0,
            total_value_goods_supplied_eu=0.0,
            total_acquisitions_eu=0.0,
            finalised=True,
        )

        payload = HMRCMTDAdapter.build_vat_return_payload(vat_ret)

        self.assertEqual(payload["periodKey"], "18A1")
        self.assertEqual(payload["vatDueSales"], 100.0)
        self.assertEqual(payload["netVatDue"], 70.0)
        self.assertTrue(payload["finalised"])

    def test_calculate_vat_return_from_transactions(self):
        transactions = [
            {"type": "SALE", "net_amount": 1000.0, "vat_amount": 200.0, "is_eu": False},
            {"type": "PURCHASE", "net_amount": 400.0, "vat_amount": 80.0, "is_eu": False},
        ]

        vat_ret = HMRCMTDAdapter.calculate_vat_return_from_transactions(transactions)

        self.assertEqual(vat_ret.vat_due_sales, 200.0)
        self.assertEqual(vat_ret.vat_reclaimed_input, 80.0)
        self.assertEqual(vat_ret.net_vat_due, 120.0)

    def test_generate_mtd_journal_entries(self):
        vat_ret = HMRCVATReturn(
            period_key="18A1",
            vat_due_sales=100.0,
            vat_due_acquisitions=0.0,
            total_vat_due=100.0,
            vat_reclaimed_input=30.0,
            net_vat_due=70.0,
            total_value_sales_ex_vat=500.0,
            total_value_purchases_ex_vat=150.0,
            total_value_goods_supplied_eu=0.0,
            total_acquisitions_eu=0.0,
            finalised=True,
        )

        entries = HMRCMTDAdapter.generate_mtd_journal_entries(vat_ret)

        self.assertGreaterEqual(len(entries), 1)
        self.assertEqual(entries[0]["debit_account"], "503")
        self.assertEqual(entries[0]["credit_account"], "4536")


if __name__ == "__main__":
    unittest.main()
