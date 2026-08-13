"""
Unit tests for Autonomous Regulatory Compliance & E-Archiving Audit Vault (eIDAS 2.0 LTV, QES, RFC 3161, ZK Proofs).
"""

import os
import tempfile
import unittest

from src.security.e_archiving_compliance_vault import (
    EArchivingComplianceVault,
    EIDASQESValidator,
    QESProvider,
    RFC3161TimeStampEngine,
    SignatureValidationProfile,
    ZeroKnowledgeTaxAuditEngine,
    ZKProofType,
)


class TestEArchivingComplianceVault(unittest.TestCase):
    """Test suite for EArchivingComplianceVault, QES LTV, RFC 3161, and ZK Proofs."""

    def setUp(self):
        self.sample_payload = (
            "HEADER|NRA_DECLARATION|2026-08-13T10:00:00Z|EIK:202688991\n"
            "INV1001|2026-08-01|BULGARIA TELECOM EAD|503|401|1200.00|BGN|VAT:240.00\n"
            "INV1002|2026-08-05|TECHNOPOLIZ EOD|503|401|3600.00|BGN|VAT:720.00\n"
            "INV1003|2026-08-10|LUKOIL BULGARIA|503|401|450.00|BGN|VAT:90.00\n"
        )
        self.vault = EArchivingComplianceVault(nra_tax_code="BG-NRA-AUDIT-VAULT-2026")

    def test_qes_validation_and_ltv_bundle(self):
        payload_bytes = self.sample_payload.encode("utf-8")
        val_res = EIDASQESValidator.validate_qes_signature(
            signature_data=payload_bytes,
            payload_bytes=payload_bytes,
            provider=QESProvider.STAMP_IT,
            profile=SignatureValidationProfile.CAdES_A_LTV,
        )
        self.assertTrue(val_res.is_valid)
        self.assertTrue(val_res.ltv_compliant)
        self.assertEqual(val_res.provider, QESProvider.STAMP_IT)
        self.assertEqual(val_res.cert_info.eik_vat_id, "BG202688991")

        ltv_bundle = EIDASQESValidator.generate_ltv_preservation_bundle(val_res)
        self.assertEqual(ltv_bundle["eidas_version"], "eIDAS 2.0 (EU 2024/1183)")
        self.assertEqual(ltv_bundle["ltv_status"], "VALID_LONG_TERM_PRESERVED")

    def test_rfc3161_timestamp_engine(self):
        payload_hash = "a" * 64
        tok = RFC3161TimeStampEngine.request_timestamp(payload_hash, tsa_name="InfoNotary Qualified TSA")
        self.assertTrue(tok.is_valid)
        self.assertEqual(tok.hashed_message_sha256, payload_hash)

        # Verify valid timestamp
        self.assertTrue(RFC3161TimeStampEngine.verify_timestamp(tok, payload_hash))

        # Tampered payload hash verify
        self.assertFalse(RFC3161TimeStampEngine.verify_timestamp(tok, "b" * 64))

        # LTV Timestamp Renewal
        renewed_tok = RFC3161TimeStampEngine.renew_timestamp_for_ltv(tok, payload_hash)
        self.assertTrue(renewed_tok.is_valid)
        self.assertIn("LTV Renewal", renewed_tok.tsa_name)

    def test_zk_turnover_range_proof(self):
        zk_proof = ZeroKnowledgeTaxAuditEngine.create_turnover_range_proof(
            actual_turnover=150000.0, min_turnover=100000.0, max_turnover=200000.0
        )
        self.assertTrue(zk_proof.verified)
        self.assertEqual(zk_proof.proof_type, ZKProofType.ZK_TURNOVER_RANGE)

        # Verification pass
        self.assertTrue(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_proof))

        # Out-of-range turnover proof failure
        zk_bad = ZeroKnowledgeTaxAuditEngine.create_turnover_range_proof(
            actual_turnover=50000.0, min_turnover=100000.0, max_turnover=200000.0
        )
        self.assertFalse(zk_bad.verified)
        self.assertFalse(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_bad))

    def test_zk_vat_invariant_proof(self):
        zk_vat = ZeroKnowledgeTaxAuditEngine.create_vat_invariant_proof(
            sales_vat=30000.0, purchases_vat=12000.0, claimed_net_vat=18000.0
        )
        self.assertTrue(zk_vat.verified)
        self.assertTrue(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_vat))

        # Invalid mismatch
        zk_vat_bad = ZeroKnowledgeTaxAuditEngine.create_vat_invariant_proof(
            sales_vat=30000.0, purchases_vat=12000.0, claimed_net_vat=99999.0
        )
        self.assertFalse(zk_vat_bad.verified)
        self.assertFalse(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_vat_bad))

    def test_zk_sequence_continuity_proof(self):
        inv_nums = [1001, 1002, 1003, 1004, 1005]
        zk_seq = ZeroKnowledgeTaxAuditEngine.create_sequence_continuity_proof(
            invoice_numbers=inv_nums, start_num=1001, end_num=1005
        )
        self.assertTrue(zk_seq.verified)
        self.assertTrue(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_seq))

        # Missing invoice gap
        inv_nums_gap = [1001, 1002, 1004, 1005]
        zk_seq_gap = ZeroKnowledgeTaxAuditEngine.create_sequence_continuity_proof(
            invoice_numbers=inv_nums_gap, start_num=1001, end_num=1005
        )
        self.assertFalse(zk_seq_gap.verified)

    def test_zk_merkle_inclusion_proof(self):
        chain_hashes = ["hash_0", "hash_1", "hash_2", "target_block_hash", "hash_4"]
        zk_merkle = ZeroKnowledgeTaxAuditEngine.create_merkle_inclusion_proof(
            block_hash="target_block_hash", ledger_chain_hashes=chain_hashes
        )
        self.assertTrue(zk_merkle.verified)
        self.assertTrue(ZeroKnowledgeTaxAuditEngine.verify_zk_proof(zk_merkle))

        # Missing block hash
        zk_merkle_missing = ZeroKnowledgeTaxAuditEngine.create_merkle_inclusion_proof(
            block_hash="unknown_hash", ledger_chain_hashes=chain_hashes
        )
        self.assertFalse(zk_merkle_missing.verified)

    def test_create_and_verify_compliance_archive(self):
        audit_ctx = {
            "total_turnover": 5250.0,
            "sales_vat": 1050.0,
            "purchases_vat": 300.0,
            "net_vat": 750.0,
            "invoice_numbers": [1001, 1002, 1003],
        }
        archive = self.vault.create_compliance_archive(
            payload_content=self.sample_payload,
            qes_provider=QESProvider.B_TRUST,
            audit_context=audit_ctx,
            generate_zk_proofs=True,
        )

        self.assertIsNotNone(archive.archive_id)
        self.assertEqual(archive.eidas_version, "eIDAS 2.0 (EU Regulation 2024/1183)")
        self.assertEqual(archive.retention_years, 10)
        self.assertEqual(len(archive.zk_audit_proofs), 3)

        # Full verification check
        report = self.vault.verify_compliance_archive(archive, expected_payload=self.sample_payload)
        self.assertTrue(report["is_compliant"])
        self.assertTrue(report["qes_ltv_valid"])
        self.assertTrue(report["rfc3161_timestamp_valid"])
        self.assertTrue(report["hsm_pqc_signature_valid"])
        self.assertEqual(report["zk_proof_count"], 3)
        self.assertTrue(report["zk_proofs_valid"])
        self.assertEqual(len(report["errors"]), 0)

    def test_export_and_import_vault_file(self):
        archive = self.vault.create_compliance_archive(
            payload_content=self.sample_payload, qes_provider=QESProvider.EVROTRUST
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "audit_vault_test.eidas-vault")
            EArchivingComplianceVault.export_vault_to_file(archive, file_path)
            self.assertTrue(os.path.exists(file_path))
            self.assertGreater(os.path.getsize(file_path), 500)

            imported_archive = EArchivingComplianceVault.import_vault_from_file(file_path)
            self.assertEqual(imported_archive.archive_id, archive.archive_id)
            self.assertEqual(imported_archive.payload_sha256, archive.payload_sha256)

            report = self.vault.verify_compliance_archive(imported_archive, expected_payload=self.sample_payload)
            self.assertTrue(report["is_compliant"])


if __name__ == "__main__":
    unittest.main()
