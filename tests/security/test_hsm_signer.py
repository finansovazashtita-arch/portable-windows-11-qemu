"""
Unit tests for Zero-Trust HSM Cryptographic Audit Log Signer.
"""

import unittest

from src.security.hsm_signer import CryptographicSignature, HSMAuditLogSigner, HSMKeyType


class TestHSMAuditLogSigner(unittest.TestCase):
    """Test suite for HSMAuditLogSigner."""

    def test_sign_audit_log_success(self):
        payload = "AUDIT_LOG_ENTRY_2026_01_31_SHA256_VERIFIED"
        sig = HSMAuditLogSigner.sign_audit_log(payload, token_serial="YUBI_8812", key_type=HSMKeyType.RSA_4096)

        self.assertTrue(len(sig.payload_sha256) == 64)
        self.assertTrue(len(sig.signature_base64) > 0)
        self.assertEqual(sig.hsm_token_serial, "YUBI_8812")

    def test_verify_audit_signature_valid(self):
        payload = "PERSISTENT_TRANSFER_LOG_DATA"
        sig = HSMAuditLogSigner.sign_audit_log(payload)

        is_valid = HSMAuditLogSigner.verify_audit_signature(payload, sig)
        self.assertTrue(is_valid)

    def test_verify_audit_signature_tampered_payload_rejected(self):
        payload = "ORIGINAL_UNMUTATED_LOG"
        tampered_payload = "TAMPERED_MUTATED_LOG"
        sig = HSMAuditLogSigner.sign_audit_log(payload)

        is_valid = HSMAuditLogSigner.verify_audit_signature(tampered_payload, sig)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
