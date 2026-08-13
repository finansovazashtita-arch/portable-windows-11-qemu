import time
import unittest
from datetime import datetime

from src.security.pq_mesh_signer import (
    PQMeshSigner,
    MeshNodeIdentity,
    MeshAttestationDocument,
    MeshSignatureChain,
    PQMeshCertificate
)
from src.security.hsm_signer import HSMKeyType

class TestPQMeshSigner(unittest.TestCase):
    def setUp(self):
        self.signer = PQMeshSigner()

    def test_register_mesh_node(self):
        node = self.signer.register_mesh_node("node_1", "aws")
        self.assertIsInstance(node, MeshNodeIdentity)
        self.assertEqual(node.node_id, "node_1")
        self.assertEqual(node.provider, "aws")

    def test_register_multiple_nodes(self):
        self.signer.register_mesh_node("node_aws", "aws")
        self.signer.register_mesh_node("node_hetzner", "hetzner")
        self.signer.register_mesh_node("node_onprem", "onprem")
        
        self.assertEqual(len(self.signer.nodes), 3)
        self.assertIn("node_aws", self.signer.nodes)
        self.assertIn("node_hetzner", self.signer.nodes)
        self.assertIn("node_onprem", self.signer.nodes)

    def test_create_attestation_health_check(self):
        self.signer.register_mesh_node("node_aws", "aws")
        attestation = self.signer.create_attestation("node_aws", "HEALTH_CHECK", {"status": "ok"})
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.issuer_id, "node_aws")
        self.assertEqual(attestation.attestation_type, "HEALTH_CHECK")
        self.assertEqual(attestation.payload, {"status": "ok"})

    def test_create_attestation_failover_auth(self):
        self.signer.register_mesh_node("node_aws", "aws")
        attestation = self.signer.create_attestation("node_aws", "FAILOVER_AUTH", {"target": "node_hetzner"})
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.issuer_id, "node_aws")
        self.assertEqual(attestation.attestation_type, "FAILOVER_AUTH")
        self.assertEqual(attestation.payload, {"target": "node_hetzner"})

    def test_verify_attestation_valid(self):
        self.signer.register_mesh_node("node_aws", "aws")
        attestation = self.signer.create_attestation("node_aws", "HEALTH_CHECK", {"status": "ok"})
        self.assertTrue(self.signer.verify_attestation(attestation))

    def test_verify_attestation_invalid_issuer(self):
        attestation = MeshAttestationDocument(
            issuer_id="unknown_node",
            attestation_type="HEALTH_CHECK",
            payload={"status": "ok"},
            timestamp=datetime.now(),
            signature=b"fake_sig"
        )
        self.assertFalse(self.signer.verify_attestation(attestation))

    def test_build_signature_chain(self):
        self.signer.register_mesh_node("node_aws", "aws")
        self.signer.register_mesh_node("node_hetzner", "hetzner")
        self.signer.register_mesh_node("node_onprem", "onprem")
        
        a1 = self.signer.create_attestation("node_aws", "HEALTH_CHECK", {})
        a2 = self.signer.create_attestation("node_hetzner", "HEALTH_CHECK", {})
        a3 = self.signer.create_attestation("node_onprem", "HEALTH_CHECK", {})
        
        chain = self.signer.build_signature_chain([a1, a2, a3])
        self.assertIsInstance(chain, MeshSignatureChain)
        self.assertEqual(len(chain.attestations), 3)

    def test_verify_signature_chain_valid(self):
        self.signer.register_mesh_node("node_aws", "aws")
        self.signer.register_mesh_node("node_hetzner", "hetzner")
        self.signer.register_mesh_node("node_onprem", "onprem")
        
        a1 = self.signer.create_attestation("node_aws", "HEALTH_CHECK", {})
        a2 = self.signer.create_attestation("node_hetzner", "HEALTH_CHECK", {})
        a3 = self.signer.create_attestation("node_onprem", "HEALTH_CHECK", {})
        
        chain = self.signer.build_signature_chain([a1, a2, a3])
        self.assertTrue(self.signer.verify_signature_chain(chain))

    def test_issue_mesh_certificate(self):
        self.signer.register_mesh_node("node_aws", "aws")
        cert = self.signer.issue_mesh_certificate("node_aws")
        self.assertIsInstance(cert, PQMeshCertificate)
        self.assertEqual(cert.node_id, "node_aws")

    def test_revoke_certificate(self):
        self.signer.register_mesh_node("node_aws", "aws")
        cert = self.signer.issue_mesh_certificate("node_aws")
        self.signer.revoke_certificate(cert.cert_id)
        self.assertTrue(cert.is_revoked())

    def test_authorize_failover(self):
        self.signer.register_mesh_node("node_aws", "aws")
        attestation = self.signer.authorize_failover("node_aws", "node_hetzner")
        self.assertIsInstance(attestation, MeshAttestationDocument)
        self.assertEqual(attestation.attestation_type, "FAILOVER_AUTH")

    def test_get_mesh_trust_status(self):
        self.signer.register_mesh_node("node_aws", "aws")
        self.signer.issue_mesh_certificate("node_aws")
        status = self.signer.get_mesh_trust_status()
        self.assertIsInstance(status, dict)
        self.assertIn("node_aws", status)

if __name__ == "__main__":
    unittest.main()
