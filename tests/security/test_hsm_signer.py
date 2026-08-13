"""
Unit tests for Zero-Trust HSM Cryptographic Audit Log Signer.
"""

import unittest

from src.security.hsm_signer import HSMAuditLogSigner, HSMKeyType


class TestHSMAuditLogSigner(unittest.TestCase):
    """Test suite for HSMAuditLogSigner."""

    def setUp(self):
        self.sample_audit_payload = (
            "HEADER|C:\\TRANSFER.LOG|2026-01-31T12:00:00Z|DSK_STATEMENT_01.PDF\n"
            "TX001|2026-01-15|STORGOZIA AD|503|401|1200.50|EUR|OK\n"
        )

    def test_sign_and_verify_rsa_4096(self):
        sig = HSMAuditLogSigner.sign_audit_log(self.sample_audit_payload, key_type=HSMKeyType.RSA_4096)
        self.assertTrue(sig.is_valid)
        self.assertEqual(sig.key_type, HSMKeyType.RSA_4096)

        is_valid = HSMAuditLogSigner.verify_audit_signature(self.sample_audit_payload, sig)
        self.assertTrue(is_valid)

    def test_sign_and_verify_pqc_dilithium(self):
        sig = HSMAuditLogSigner.sign_audit_log(self.sample_audit_payload, key_type=HSMKeyType.CRYSTALS_DILITHIUM)
        self.assertTrue(sig.is_valid)
        self.assertEqual(sig.key_type, HSMKeyType.CRYSTALS_DILITHIUM)

        is_valid = HSMAuditLogSigner.verify_audit_signature(self.sample_audit_payload, sig)
        self.assertTrue(is_valid)

    def test_sign_and_verify_pqc_falcon(self):
        sig = HSMAuditLogSigner.sign_audit_log(self.sample_audit_payload, key_type=HSMKeyType.FALCON_1024)
        self.assertTrue(sig.is_valid)
        self.assertEqual(sig.key_type, HSMKeyType.FALCON_1024)

        is_valid = HSMAuditLogSigner.verify_audit_signature(self.sample_audit_payload, sig)
        self.assertTrue(is_valid)

    def test_tamper_detection(self):
        sig = HSMAuditLogSigner.sign_audit_log(self.sample_audit_payload)
        tampered_payload = self.sample_audit_payload + "TAMPERED_LINE_ITEMS\n"

        is_valid = HSMAuditLogSigner.verify_audit_signature(tampered_payload, sig)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
