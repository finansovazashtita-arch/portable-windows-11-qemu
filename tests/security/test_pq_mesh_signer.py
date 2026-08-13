"""
Unit tests for Post-Quantum Mesh Cryptographic Signer (M63).
"""

import time
import unittest
from datetime import datetime, timezone

from src.security.hsm_signer import HSMKeyType
from src.security.pq_mesh_signer import (
    MeshAttestationDocument,
    MeshNodeIdentity,
    MeshSignatureChain,
    PQMeshCertificate,
    PQMeshSigner,
)


class TestPQMeshSigner(unittest.TestCase):
    """Test suite for PQMeshSigner."""

    def setUp(self):
        self.signer = PQMeshSigner(mesh_id="test-dr-mesh")

    def test_register_mesh_node(self):
        node = self.signer.register_mesh_node(
            node_id="aws-eu-central-1",
            cloud_provider="AWS",
            region="eu-central-1",
            k8s_namespace="dr-mesh-aws",
        )
        self.assertIsInstance(node, MeshNodeIdentity)
        self.assertEqual(node.node_id, "aws-eu-central-1")
        self.assertEqual(node.cloud_provider, "AWS")
        self.assertEqual(node.region, "eu-central-1")
        self.assertTrue(node.is_active)

    def test_register_multiple_nodes(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")
        self.signer.register_mesh_node("onprem-node", "ONPREM", "sofia-office", "ns-onprem")

        self.assertEqual(len(self.signer.node_identities), 3)
        self.assertIn("aws-node", self.signer.node_identities)
        self.assertIn("hetzner-node", self.signer.node_identities)
        self.assertIn("onprem-node", self.signer.node_identities)

    def test_create_attestation_health_check(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        attestation = self.signer.create_attestation(
            issuer_node_id="aws-node",
            target_node_id="hetzner-node",
            attestation_type="HEALTH_CHECK",
            payload_data={"status": "ok", "latency_ms": 12.5},
        )
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.issuer_node_id, "aws-node")
        self.assertEqual(attestation.target_node_id, "hetzner-node")
        self.assertEqual(attestation.attestation_type, "HEALTH_CHECK")
        self.assertTrue(attestation.is_verified)

    def test_create_attestation_failover_auth(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        attestation = self.signer.create_attestation(
            issuer_node_id="aws-node",
            target_node_id="hetzner-node",
            attestation_type="FAILOVER_AUTH",
            payload_data={"reason": "PRIMARY_FAILED"},
        )
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.issuer_node_id, "aws-node")
        self.assertEqual(attestation.attestation_type, "FAILOVER_AUTH")

    def test_verify_attestation_valid(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        attestation = self.signer.create_attestation(
            issuer_node_id="aws-node",
            target_node_id="hetzner-node",
            attestation_type="HEALTH_CHECK",
            payload_data={"status": "ok"},
        )
        self.assertTrue(self.signer.verify_attestation(attestation))

    def test_verify_attestation_invalid_issuer(self):
        attestation = MeshAttestationDocument(
            attestation_id="fake-id",
            issuer_node_id="unknown_node",
            target_node_id="target_node",
            attestation_type="HEALTH_CHECK",
            payload_hash="abc",
            signature=None,  # type: ignore
            timestamp_iso=datetime.now(timezone.utc).isoformat(),
        )
        self.assertFalse(self.signer.verify_attestation(attestation))

    def test_build_signature_chain(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")
        self.signer.register_mesh_node("onprem-node", "ONPREM", "sofia-office", "ns-onprem")

        a1 = self.signer.create_attestation("aws-node", "hetzner-node", "HEALTH_CHECK", {"step": 1})
        a2 = self.signer.create_attestation("hetzner-node", "onprem-node", "HEALTH_CHECK", {"step": 2})
        a3 = self.signer.create_attestation("onprem-node", "aws-node", "HEALTH_CHECK", {"step": 3})

        chain = self.signer.build_signature_chain("chain-1", [a1, a2, a3])
        self.assertIsInstance(chain, MeshSignatureChain)
        self.assertEqual(len(chain.entries), 3)
        self.assertTrue(chain.is_valid)

    def test_verify_signature_chain_valid(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        a1 = self.signer.create_attestation("aws-node", "hetzner-node", "HEALTH_CHECK", {"step": 1})
        a2 = self.signer.create_attestation("hetzner-node", "aws-node", "HEALTH_CHECK", {"step": 2})

        chain = self.signer.build_signature_chain("chain-2", [a1, a2])
        is_valid, err = self.signer.verify_signature_chain(chain)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_issue_mesh_certificate(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        cert = self.signer.issue_mesh_certificate(
            subject_node_id="hetzner-node",
            issuer_node_id="aws-node",
            validity_days=30,
        )
        self.assertIsInstance(cert, PQMeshCertificate)
        self.assertEqual(cert.subject_node_id, "hetzner-node")
        self.assertEqual(cert.issuer_node_id, "aws-node")
        self.assertFalse(cert.is_revoked)

    def test_revoke_certificate(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        cert = self.signer.issue_mesh_certificate("hetzner-node", "aws-node")
        result = self.signer.revoke_certificate(cert.cert_id)
        self.assertTrue(result)
        self.assertTrue(cert.is_revoked)
        self.assertIn(cert.cert_id, self.signer.revocation_list)

    def test_authorize_failover(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")

        attestation = self.signer.authorize_failover("aws-node", "hetzner-node", "AWS_REGION_DOWN")
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.attestation_type, "FAILOVER_AUTH")

    def test_get_mesh_trust_status(self):
        self.signer.register_mesh_node("aws-node", "AWS", "eu-central-1", "ns-aws")
        self.signer.register_mesh_node("hetzner-node", "HETZNER", "fsn1-dc14", "ns-hetzner")
        self.signer.issue_mesh_certificate("hetzner-node", "aws-node")

        status = self.signer.get_mesh_trust_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(status["mesh_id"], "test-dr-mesh")
        self.assertEqual(status["total_nodes"], 2)
        self.assertEqual(status["active_certificates"], 1)


if __name__ == "__main__":
    unittest.main()
