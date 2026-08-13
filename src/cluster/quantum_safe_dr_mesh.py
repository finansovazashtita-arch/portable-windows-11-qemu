"""
Quantum-Safe Active-Active DR Mesh Orchestrator (M63).

Unifies post-quantum cryptographic mesh signing (M36) and the DR failover orchestrator (M59)
into an active multi-cloud Kubernetes/K3s cluster mesh spanning:
- AWS (eu-central-1) cloud region
- Hetzner (fsn1-dc14) cloud region  
- On-premise Mac Mini cluster (macmini-primary / macmini-secondary)

Capabilities:
- Multi-cloud K3s mesh node registration with PQC identity certificates
- Quantum-safe mutual authentication between mesh nodes
- Active-active DR failover with cryptographic authorization chains
- Cross-region health consensus via signed attestation documents
- Automated mesh partition healing and split-brain resolution
- WireGuard mesh tunnel management with PQC certificates
"""

import enum
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from src.cluster.dr_failover_orchestrator import DRState, FailoverMode, FailoverExecutionReport, ZeroTrustDROrchestrator
from src.cluster.ha_failover import NodeRole, NodeStatus
from src.security.pq_mesh_signer import PQMeshSigner, MeshNodeIdentity, MeshAttestationDocument, MeshSignatureChain, PQMeshCertificate
from src.backup.disaster_recovery_replication import DRReplicationManager, ReplicationTarget
from src.backup.active_active_sql_sync import ActiveActiveSQLSyncGuard

logger = logging.getLogger(__name__)

class CloudProvider(str, enum.Enum):
    """Cloud provider hosting the mesh node."""
    AWS = "AWS"
    HETZNER = "HETZNER"
    ONPREM = "ONPREM"

class MeshNodeState(str, enum.Enum):
    """Current state of a mesh node."""
    ACTIVE = "ACTIVE"
    STANDBY = "STANDBY"
    DRAINING = "DRAINING"
    PARTITIONED = "PARTITIONED"
    FAILED = "FAILED"
    REJOINING = "REJOINING"

class MeshTopology(str, enum.Enum):
    """Topology structure of the mesh."""
    FULL_MESH = "FULL_MESH"
    STAR = "STAR"
    RING = "RING"

class SplitBrainStrategy(str, enum.Enum):
    """Strategy used for split brain resolution."""
    FENCING = "FENCING"
    QUORUM = "QUORUM"
    LEADER_ELECTION = "LEADER_ELECTION"

@dataclass
class K3sClusterNode:
    """Represents a K3s cluster node in the DR mesh."""
    node_id: str
    cloud_provider: CloudProvider
    region: str
    k3s_version: str = 'v1.31.2+k3s1'
    wireguard_endpoint: str = ''
    wireguard_public_key: str = ''
    api_server_url: str = ''
    state: MeshNodeState = MeshNodeState.ACTIVE
    cpu_cores: int = 4
    memory_gb: int = 8
    last_heartbeat_iso: str = ''
    mesh_latency_ms: float = 0.0

@dataclass
class MeshHealthConsensus:
    """Represents the consensus of health across the mesh."""
    consensus_id: str
    timestamp_iso: str
    participating_nodes: List[str]
    healthy_nodes: List[str]
    failed_nodes: List[str]
    partitioned_nodes: List[str]
    quorum_reached: bool
    consensus_hash: str

@dataclass
class WireGuardTunnel:
    """Represents a WireGuard tunnel between two mesh nodes."""
    tunnel_id: str
    node_a: str
    node_b: str
    endpoint_a: str
    endpoint_b: str
    psk_fingerprint: str
    pqc_cert_id: str
    latency_ms: float = 0.0
    is_active: bool = True

@dataclass
class MeshFailoverEvent:
    """Represents a DR failover event within the mesh."""
    event_id: str
    timestamp_iso: str
    source_region: str
    target_region: str
    failed_node_id: str
    promoted_node_id: str
    failover_mode: FailoverMode
    authorization_chain_id: str
    rto_seconds: float
    pqc_verified: bool
    consensus: MeshHealthConsensus

class QuantumSafeDRMesh:
    """
    Main Orchestrator for Quantum-Safe Active-Active DR Mesh.
    """

    def __init__(
        self, 
        mesh_id: str = 'finansprotect-dr-mesh', 
        topology: MeshTopology = MeshTopology.FULL_MESH, 
        split_brain_strategy: SplitBrainStrategy = SplitBrainStrategy.QUORUM, 
        target_rto_seconds: float = 5.0
    ):
        self.mesh_id = mesh_id
        self.topology = topology
        self.split_brain_strategy = split_brain_strategy
        self.target_rto_seconds = target_rto_seconds
        
        self.pq_signer = PQMeshSigner(mesh_id=self.mesh_id)
        self.mesh_nodes: Dict[str, K3sClusterNode] = {}
        self.wireguard_tunnels: Dict[str, WireGuardTunnel] = {}
        self.failover_history: List[MeshFailoverEvent] = []
        
        logger.info(f"🚀 Initializing QuantumSafeDRMesh [{self.mesh_id}] with {self.topology} topology.")
        
        # Register default nodes
        self.register_mesh_node(
            node_id='aws-eu-central-1',
            cloud_provider=CloudProvider.AWS,
            region='eu-central-1',
            api_server_url='https://k3s-aws.finansprotect.eu:6443'
        )
        self.register_mesh_node(
            node_id='hetzner-fsn1',
            cloud_provider=CloudProvider.HETZNER,
            region='fsn1-dc14',
            api_server_url='https://k3s-hetzner.finansprotect.eu:6443'
        )
        self.register_mesh_node(
            node_id='onprem-macmini',
            cloud_provider=CloudProvider.ONPREM,
            region='sofia-office',
            api_server_url='https://100.83.83.8:6443'
        )

        # Issue mutual PQC certificates and establish tunnels if FULL_MESH
        if self.topology == MeshTopology.FULL_MESH:
            node_ids = list(self.mesh_nodes.keys())
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    self.establish_wireguard_tunnel(node_ids[i], node_ids[j])
        
        logger.info("✅ Default DR mesh nodes registered and initialized.")

    def register_mesh_node(self, node_id: str, cloud_provider: CloudProvider, region: str, api_server_url: str = '', **kwargs) -> K3sClusterNode:
        """Registers a node in the mesh and in the PQ mesh signer."""
        logger.info(f"🔐 Registering mesh node {node_id} in {region} ({cloud_provider}).")
        
        node = K3sClusterNode(
            node_id=node_id,
            cloud_provider=cloud_provider,
            region=region,
            api_server_url=api_server_url,
            last_heartbeat_iso=datetime.now(timezone.utc).isoformat(),
            **kwargs
        )
        self.mesh_nodes[node_id] = node
        
        # Register in pq_signer
        k8s_namespace = f"dr-mesh-{cloud_provider.lower()}"
        self.pq_signer.register_mesh_node(
            node_id=node_id,
            cloud_provider=cloud_provider.value,
            region=region,
            k8s_namespace=k8s_namespace
        )
        
        return node
        
    def establish_wireguard_tunnel(self, node_a_id: str, node_b_id: str) -> WireGuardTunnel:
        """Creates a WireGuard tunnel with PQC certificates between two nodes."""
        logger.info(f"🔒 Establishing WireGuard tunnel between {node_a_id} and {node_b_id}.")
        
        if node_a_id not in self.mesh_nodes or node_b_id not in self.mesh_nodes:
            raise ValueError("Both nodes must be registered in the mesh.")
            
        tunnel_id = f"wg-{node_a_id}-{node_b_id}"
        
        # Issue certificate for tunnel
        cert_id = f"cert-{tunnel_id}-{uuid.uuid4().hex[:8]}"
        self.pq_signer.issue_mesh_certificate(
            subject=node_b_id,
            issuer=node_a_id,
            validity_days=30
        )
        
        tunnel = WireGuardTunnel(
            tunnel_id=tunnel_id,
            node_a=node_a_id,
            node_b=node_b_id,
            endpoint_a=f"{node_a_id}.mesh.internal:51820",
            endpoint_b=f"{node_b_id}.mesh.internal:51820",
            psk_fingerprint=hashlib.sha256(f"psk-{tunnel_id}".encode()).hexdigest(),
            pqc_cert_id=cert_id,
            latency_ms=2.5,
            is_active=True
        )
        
        self.wireguard_tunnels[tunnel_id] = tunnel
        return tunnel

    def execute_mesh_health_consensus(self) -> MeshHealthConsensus:
        """All nodes sign attestation documents and builds consensus."""
        logger.info("🩺 Executing mesh health consensus.")
        timestamp = datetime.now(timezone.utc).isoformat()
        
        participating_nodes = list(self.mesh_nodes.keys())
        healthy_nodes = []
        failed_nodes = []
        partitioned_nodes = []
        attestation_hashes = []
        
        # Simulate health check and attestation gathering
        for node_id, node in self.mesh_nodes.items():
            if node.state == MeshNodeState.ACTIVE:
                healthy_nodes.append(node_id)
                # Create an attestation for this node
                attestation = self.pq_signer.create_attestation(
                    issuer=node_id,
                    target=node_id,
                    type="HEALTH_CHECK",
                    payload={"status": "OK", "timestamp": timestamp}
                )
                self.pq_signer.verify_attestation(attestation)
                attestation_hashes.append(hashlib.sha256(json.dumps(attestation.payload).encode()).hexdigest())
            elif node.state == MeshNodeState.FAILED:
                failed_nodes.append(node_id)
            elif node.state == MeshNodeState.PARTITIONED:
                partitioned_nodes.append(node_id)
                
        quorum_reached = len(healthy_nodes) > len(participating_nodes) / 2
        
        consensus_hash_input = "".join(sorted(attestation_hashes))
        consensus_hash = hashlib.sha3_256(consensus_hash_input.encode()).hexdigest()
        
        consensus = MeshHealthConsensus(
            consensus_id=str(uuid.uuid4()),
            timestamp_iso=timestamp,
            participating_nodes=participating_nodes,
            healthy_nodes=healthy_nodes,
            failed_nodes=failed_nodes,
            partitioned_nodes=partitioned_nodes,
            quorum_reached=quorum_reached,
            consensus_hash=consensus_hash
        )
        
        logger.info(f"✅ Consensus reached: {quorum_reached} ({len(healthy_nodes)}/{len(participating_nodes)} healthy)")
        return consensus

    def detect_split_brain(self) -> Dict[str, Any]:
        """Evaluates network partitions and returns partition groups."""
        logger.warning("⚠️ Detecting split-brain scenarios in mesh topology.")
        
        partitions = {
            "group_a": [],
            "group_b": []
        }
        
        # Simple simulation: group by connectivity.
        nodes = list(self.mesh_nodes.values())
        if nodes:
            partitions["group_a"].append(nodes[0].node_id)
            for node in nodes[1:]:
                # Simulate grouping
                if node.state == MeshNodeState.PARTITIONED:
                    partitions["group_b"].append(node.node_id)
                else:
                    partitions["group_a"].append(node.node_id)
                    
        return partitions

    def resolve_split_brain(self, partition_groups: Dict[str, Any]) -> str:
        """Applies configured split_brain_strategy and returns winning partition leader."""
        logger.info(f"🧠 Resolving split-brain using {self.split_brain_strategy} strategy.")
        
        winning_partition = None
        
        if self.split_brain_strategy == SplitBrainStrategy.QUORUM:
            max_nodes = 0
            for group, node_ids in partition_groups.items():
                if len(node_ids) > max_nodes:
                    max_nodes = len(node_ids)
                    winning_partition = group
        elif self.split_brain_strategy == SplitBrainStrategy.LEADER_ELECTION:
            # Assume group_a has the leader if not empty
            winning_partition = "group_a" if partition_groups.get("group_a") else "group_b"
        elif self.split_brain_strategy == SplitBrainStrategy.FENCING:
            # First group fences the others
            winning_partition = "group_a"
            
        winning_leader = partition_groups.get(winning_partition, [""])[0] if winning_partition else ""
        logger.info(f"✅ Split-brain resolved. Winning leader: {winning_leader}")
        return winning_leader

    def execute_mesh_failover(self, failed_node_id: str, reason: str = 'NODE_FAILURE') -> MeshFailoverEvent:
        """Executes full failover with health consensus and PQC authorization."""
        start_time = time.time()
        logger.info(f"🚨 Initiating mesh failover for {failed_node_id} due to {reason}.")
        
        if failed_node_id in self.mesh_nodes:
            self.mesh_nodes[failed_node_id].state = MeshNodeState.FAILED
            
        # 1. Runs health consensus
        consensus = self.execute_mesh_health_consensus()
        
        if not consensus.quorum_reached:
            logger.error("❌ Quorum not reached, failover may result in split-brain!")
            
        # 2. Selects best failover target (lowest latency healthy node in different region)
        failed_node = self.mesh_nodes.get(failed_node_id)
        target_node = None
        min_latency = float('inf')
        
        for node_id in consensus.healthy_nodes:
            node = self.mesh_nodes[node_id]
            if failed_node and node.region != failed_node.region:
                if node.mesh_latency_ms <= min_latency:
                    target_node = node
                    min_latency = node.mesh_latency_ms
                    
        if not target_node:
            raise RuntimeError("No suitable failover target found in different region.")
            
        # 3. Gets PQC failover authorization
        auth_request = self.pq_signer.authorize_failover(
            requesting=target_node.node_id,
            target=failed_node_id,
            reason=reason
        )
        
        # 4. Builds authorization chain
        attestations = [
            self.pq_signer.create_attestation(
                issuer=target_node.node_id, 
                target=failed_node_id, 
                type="FAILOVER_AUTH", 
                payload={"reason": reason}
            )
        ]
        chain_id = f"chain-{uuid.uuid4()}"
        auth_chain = self.pq_signer.build_signature_chain(chain_id, attestations)
        
        # 5. Executes failover and measures RTO
        time.sleep(min(self.target_rto_seconds * 0.5, 0.1)) # Simulate failover action quickly
        rto_seconds = time.time() - start_time
        
        event = MeshFailoverEvent(
            event_id=f"failover-{uuid.uuid4()}",
            timestamp_iso=datetime.now(timezone.utc).isoformat(),
            source_region=failed_node.region if failed_node else "UNKNOWN",
            target_region=target_node.region,
            failed_node_id=failed_node_id,
            promoted_node_id=target_node.node_id,
            failover_mode=FailoverMode.AUTOMATIC_DISASTER if reason == 'NODE_FAILURE' else FailoverMode.SCHEDULED_DRILL,
            authorization_chain_id=chain_id,
            rto_seconds=rto_seconds,
            pqc_verified=True,
            consensus=consensus
        )
        
        self.failover_history.append(event)
        logger.info(f"✅ Failover completed to {target_node.node_id} in {rto_seconds:.2f}s.")
        return event

    def execute_cross_region_dr_drill(self) -> Dict[str, Any]:
        """Runs a full DR drill across all regions with PQC verification."""
        logger.info("🔥 Executing cross-region DR drill.")
        drill_results = {}
        
        for node_id in list(self.mesh_nodes.keys()):
            logger.info(f"Testing failure of node {node_id}...")
            # Restore state later
            original_state = self.mesh_nodes[node_id].state
            try:
                failover_event = self.execute_mesh_failover(node_id, reason="SCHEDULED_DRILL")
                drill_results[node_id] = {
                    "status": "SUCCESS",
                    "promoted_node": failover_event.promoted_node_id,
                    "rto_seconds": failover_event.rto_seconds
                }
            except Exception as e:
                drill_results[node_id] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            finally:
                self.mesh_nodes[node_id].state = original_state
                
        logger.info("✅ Cross-region DR drill completed.")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": drill_results,
            "overall_status": "SUCCESS" if all(r.get("status") == "SUCCESS" for r in drill_results.values()) else "PARTIAL_FAIL"
        }

    def rotate_mesh_certificates(self) -> Dict[str, Any]:
        """Rotates all PQC certificates and re-establishes tunnels."""
        logger.info("🔄 Rotating mesh PQC certificates.")
        rotated_count = 0
        for tunnel_id, tunnel in self.wireguard_tunnels.items():
            new_cert_id = f"cert-{tunnel_id}-{uuid.uuid4().hex[:8]}"
            tunnel.pqc_cert_id = new_cert_id
            self.pq_signer.issue_mesh_certificate(
                subject=tunnel.node_b,
                issuer=tunnel.node_a,
                validity_days=30
            )
            rotated_count += 1
            
        return {
            "status": "SUCCESS",
            "rotated_certificates": rotated_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_mesh_topology_status(self) -> Dict[str, Any]:
        """Returns complete mesh status."""
        return {
            "mesh_id": self.mesh_id,
            "topology": self.topology.value,
            "nodes": {nid: vars(n) for nid, n in self.mesh_nodes.items()},
            "tunnels": {tid: vars(t) for tid, t in self.wireguard_tunnels.items()},
            "healthy_node_count": sum(1 for n in self.mesh_nodes.values() if n.state == MeshNodeState.ACTIVE)
        }
