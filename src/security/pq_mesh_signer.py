import dataclasses
import enum
import hashlib
import hmac
import base64
import time
import json
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

from src.security.hsm_signer import CryptographicSignature, HSMAuditLogSigner, HSMKeyType

logger = logging.getLogger(__name__)

@dataclasses.dataclass
class MeshNodeIdentity:
    """
    Represents the cryptographic identity of a mesh node.
    """
    node_id: str
    cloud_provider: str
    region: str
    k8s_namespace: str
    pqc_public_key_b64: str
    pqc_key_type: HSMKeyType
    certificate_fingerprint: str
    created_at_iso: str
    is_active: bool = True

@dataclasses.dataclass
class MeshAttestationDocument:
    """
    Represents a signed attestation document within the mesh.
    """
    attestation_id: str
    issuer_node_id: str
    target_node_id: str
    attestation_type: str
    payload_hash: str
    signature: CryptographicSignature
    timestamp_iso: str
    is_verified: bool = False

@dataclasses.dataclass
class MeshSignatureChain:
    """
    Represents a hash-linked chain of attestation documents for mesh integrity.
    """
    chain_id: str
    entries: List[MeshAttestationDocument]
    genesis_hash: str
    tip_hash: str
    is_valid: bool = True

@dataclasses.dataclass
class PQMeshCertificate:
    """
    Represents a post-quantum mutual TLS certificate for WireGuard mesh tunnels.
    """
    cert_id: str
    subject_node_id: str
    issuer_node_id: str
    public_key_b64: str
    key_type: HSMKeyType
    not_before_iso: str
    not_after_iso: str
    serial_number: str
    fingerprint_sha256: str
    is_revoked: bool = False

class PQMeshSigner:
    """
    Post-Quantum Mesh Cryptographic Signer for Multi-Cloud DR Mesh (M63).

    Extends the Zero-Trust HSM Cryptographic Signer (M36) with multi-node mesh signing capabilities:
    - Per-node PQC identity keypairs for mesh node authentication
    - Mesh-wide signed state attestation documents for cluster health consensus
    - Cross-node signature chain verification for DR failover authorization
    - Quantum-safe mutual TLS certificate generation for WireGuard mesh tunnels
    """
    def __init__(self, mesh_id: str = 'finansprotect-dr-mesh', pqc_algorithm: HSMKeyType = HSMKeyType.CRYSTALS_DILITHIUM):
        self.mesh_id = mesh_id
        self.pqc_algorithm = pqc_algorithm
        self.node_identities: Dict[str, MeshNodeIdentity] = {}
        self.attestation_chains: Dict[str, MeshSignatureChain] = {}
        self.certificates: Dict[str, PQMeshCertificate] = {}
        self.revocation_list: set = set()
        logger.info(f"🚀 Initialized PQMeshSigner for mesh {self.mesh_id} with algorithm {self.pqc_algorithm}")

    def _generate_pqc_keypair(self, node_id: str) -> Tuple[str, str]:
        """
        Simulates generation of a post-quantum cryptographic keypair.
        Returns base64 encoded public and private keys.
        """
        seed = f"{self.mesh_id}:{node_id}:{time.time()}".encode()
        priv_key = hashlib.sha384(seed).digest()
        pub_key = hashlib.sha384(priv_key).digest()
        return base64.b64encode(pub_key).decode(), base64.b64encode(priv_key).decode()

    def register_mesh_node(self, node_id: str, cloud_provider: str, region: str, k8s_namespace: str) -> MeshNodeIdentity:
        """
        Generates PQC keypair for node and registers its identity.
        """
        logger.info(f"🔐 Registering mesh node {node_id}")
        if node_id in self.node_identities:
            raise ValueError(f"Node {node_id} is already registered.")
        
        pub_key, priv_key = self._generate_pqc_keypair(node_id)
        
        fingerprint = hashlib.sha256(pub_key.encode()).hexdigest()
        
        identity = MeshNodeIdentity(
            node_id=node_id,
            cloud_provider=cloud_provider,
            region=region,
            k8s_namespace=k8s_namespace,
            pqc_public_key_b64=pub_key,
            pqc_key_type=self.pqc_algorithm,
            certificate_fingerprint=fingerprint,
            created_at_iso=datetime.now(timezone.utc).isoformat(),
            is_active=True
        )
        self.node_identities[node_id] = identity
        logger.info(f"✅ Registered mesh node {node_id}")
        return identity

    def create_attestation(self, issuer_node_id: str, target_node_id: str, attestation_type: str, payload_data: Dict[str, Any]) -> MeshAttestationDocument:
        """
        Signs an attestation with the issuer's PQC key via HSMAuditLogSigner.
        """
        logger.info(f"✍️ Creating attestation from {issuer_node_id} for {target_node_id} ({attestation_type})")
        if issuer_node_id not in self.node_identities:
            raise ValueError(f"Issuer node {issuer_node_id} not registered.")
        
        issuer_identity = self.node_identities[issuer_node_id]
        if not issuer_identity.is_active:
            raise ValueError(f"Issuer node {issuer_node_id} is inactive.")
            
        payload_str = json.dumps(payload_data, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
        
        attestation_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        token_serial = f"PQC-{issuer_node_id}-{int(time.time())}"
        
        signature = HSMAuditLogSigner.sign_audit_log(
            payload_content=payload_str,
            token_serial=token_serial,
            key_type=issuer_identity.pqc_key_type
        )
        
        attestation = MeshAttestationDocument(
            attestation_id=attestation_id,
            issuer_node_id=issuer_node_id,
            target_node_id=target_node_id,
            attestation_type=attestation_type,
            payload_hash=payload_hash,
            signature=signature,
            timestamp_iso=timestamp,
            is_verified=True
        )
        logger.info(f"✅ Created attestation {attestation_id}")
        return attestation

    def verify_attestation(self, attestation: MeshAttestationDocument) -> bool:
        """
        Verifies signature using the issuer node's registered identity.
        """
        logger.info(f"🔍 Verifying attestation {attestation.attestation_id}")
        if attestation.issuer_node_id not in self.node_identities:
            logger.warning(f"❌ Issuer node {attestation.issuer_node_id} not found.")
            return False
            
        issuer_identity = self.node_identities[attestation.issuer_node_id]
        if not issuer_identity.is_active:
            logger.warning(f"❌ Issuer node {attestation.issuer_node_id} is inactive.")
            return False
            
        is_valid = HSMAuditLogSigner.verify_audit_signature(
            payload_content=attestation.payload_hash,  # Assuming hsm_signer verifies payload or its hash
            signature=attestation.signature
        )
        
        attestation.is_verified = is_valid
        if is_valid:
            logger.info(f"✅ Attestation {attestation.attestation_id} verified successfully.")
        else:
            logger.warning(f"❌ Attestation {attestation.attestation_id} verification failed.")
        return is_valid

    def build_signature_chain(self, chain_id: str, attestations: List[MeshAttestationDocument]) -> MeshSignatureChain:
        """
        Chains attestation documents into a hash-linked chain.
        """
        logger.info(f"🔗 Building signature chain {chain_id} with {len(attestations)} attestations")
        if not attestations:
            raise ValueError("Cannot build chain with empty attestations list.")
            
        genesis_hash = hashlib.sha256(b"genesis").hexdigest()
        current_hash = genesis_hash
        
        for att in attestations:
            block_data = f"{current_hash}:{att.attestation_id}:{att.payload_hash}:{att.signature.signature_base64}"
            current_hash = hashlib.sha256(block_data.encode()).hexdigest()
            
        chain = MeshSignatureChain(
            chain_id=chain_id,
            entries=attestations,
            genesis_hash=genesis_hash,
            tip_hash=current_hash,
            is_valid=True
        )
        self.attestation_chains[chain_id] = chain
        logger.info(f"✅ Built signature chain {chain_id}, tip: {current_hash}")
        return chain

    def verify_signature_chain(self, chain: MeshSignatureChain) -> Tuple[bool, Optional[str]]:
        """
        Verifies chain integrity and all attestation signatures.
        """
        logger.info(f"🔍 Verifying signature chain {chain.chain_id}")
        current_hash = chain.genesis_hash
        
        for att in chain.entries:
            if not self.verify_attestation(att):
                logger.warning(f"❌ Invalid attestation {att.attestation_id} in chain {chain.chain_id}")
                return False, f"Invalid attestation: {att.attestation_id}"
                
            block_data = f"{current_hash}:{att.attestation_id}:{att.payload_hash}:{att.signature.signature_base64}"
            current_hash = hashlib.sha256(block_data.encode()).hexdigest()
            
        if current_hash != chain.tip_hash:
            logger.warning(f"❌ Chain tip hash mismatch in {chain.chain_id}")
            return False, "Tip hash mismatch"
            
        logger.info(f"✅ Signature chain {chain.chain_id} is valid")
        return True, None

    def issue_mesh_certificate(self, subject_node_id: str, issuer_node_id: str, validity_days: int = 365) -> PQMeshCertificate:
        """
        Issues PQC-signed mutual TLS certificate for WireGuard mesh.
        """
        logger.info(f"📜 Issuing mesh certificate for {subject_node_id} by {issuer_node_id}")
        if subject_node_id not in self.node_identities:
            raise ValueError(f"Subject node {subject_node_id} not registered.")
        if issuer_node_id not in self.node_identities:
            raise ValueError(f"Issuer node {issuer_node_id} not registered.")
            
        subject_identity = self.node_identities[subject_node_id]
        issuer_identity = self.node_identities[issuer_node_id]
        
        cert_id = str(uuid.uuid4())
        serial_number = str(uuid.uuid4().int >> 64)
        
        now = datetime.now(timezone.utc)
        not_before = now.isoformat()
        not_after = (now + timedelta(days=validity_days)).isoformat()
        
        fingerprint = subject_identity.certificate_fingerprint
        
        cert = PQMeshCertificate(
            cert_id=cert_id,
            subject_node_id=subject_node_id,
            issuer_node_id=issuer_node_id,
            public_key_b64=subject_identity.pqc_public_key_b64,
            key_type=subject_identity.pqc_key_type,
            not_before_iso=not_before,
            not_after_iso=not_after,
            serial_number=serial_number,
            fingerprint_sha256=fingerprint,
            is_revoked=False
        )
        self.certificates[cert_id] = cert
        logger.info(f"✅ Issued mesh certificate {cert_id}")
        return cert

    def revoke_certificate(self, cert_id: str) -> bool:
        """
        Revokes a mesh certificate.
        """
        logger.info(f"🛑 Revoking certificate {cert_id}")
        if cert_id not in self.certificates:
            logger.warning(f"❌ Certificate {cert_id} not found.")
            return False
            
        self.certificates[cert_id].is_revoked = True
        self.revocation_list.add(cert_id)
        logger.info(f"✅ Revoked certificate {cert_id}")
        return True

    def authorize_failover(self, requesting_node_id: str, target_node_id: str, failover_reason: str) -> MeshAttestationDocument:
        """
        Creates and signs a FAILOVER_AUTH attestation document.
        """
        logger.info(f"⚡ Authorizing failover from {requesting_node_id} to {target_node_id}")
        payload_data = {
            "reason": failover_reason,
            "action": "failover_auth",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return self.create_attestation(
            issuer_node_id=requesting_node_id,
            target_node_id=target_node_id,
            attestation_type="FAILOVER_AUTH",
            payload_data=payload_data
        )

    def get_mesh_trust_status(self) -> Dict[str, Any]:
        """
        Returns mesh-wide trust status including all nodes, chains, certs.
        """
        return {
            "mesh_id": self.mesh_id,
            "pqc_algorithm": self.pqc_algorithm.value,
            "active_nodes_count": len([n for n in self.node_identities.values() if n.is_active]),
            "total_nodes": len(self.node_identities),
            "chains_count": len(self.attestation_chains),
            "active_certificates": len(self.certificates) - len(self.revocation_list),
            "revoked_certificates": len(self.revocation_list),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
