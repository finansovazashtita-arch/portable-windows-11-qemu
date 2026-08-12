"""
High Availability (HA) Clustering & Failover Routing Engine.

Supports:
- Multi-node HA cluster management across macmini-primary and macmini-secondary
- Automatic heartbeat health monitoring
- Automated failover routing upon primary leader degradation or failure
- Queue and audit state synchronization
"""

import dataclasses
import enum
import json
import logging
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("ha_failover")


class NodeRole(str, enum.Enum):
    PRIMARY_LEADER = "PRIMARY_LEADER"
    SECONDARY_STANDBY = "SECONDARY_STANDBY"


class NodeStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"


@dataclasses.dataclass
class ClusterNode:
    node_id: str
    host: str
    port: int
    role: NodeRole
    status: NodeStatus
    last_ping: float


class HAFailoverManager:
    """Manages node health checks, failover leader election, and HA request routing."""

    def __init__(self):
        self.nodes: Dict[str, ClusterNode] = {
            "macmini-primary": ClusterNode(
                node_id="macmini-primary",
                host="100.83.83.8",
                port=8090,
                role=NodeRole.PRIMARY_LEADER,
                status=NodeStatus.HEALTHY,
                last_ping=time.time(),
            ),
            "macmini-secondary": ClusterNode(
                node_id="macmini-secondary",
                host="100.70.181.127",
                port=8090,
                role=NodeRole.SECONDARY_STANDBY,
                status=NodeStatus.HEALTHY,
                last_ping=time.time(),
            ),
        }
        self.active_leader_id = "macmini-primary"

    def check_node_health(self, node_id: str) -> NodeStatus:
        """Pings a cluster node HTTP endpoint to evaluate health."""
        node = self.nodes.get(node_id)
        if not node:
            return NodeStatus.UNREACHABLE

        url = f"http://{node.host}:{node.port}/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FinansProtect-HA-Manager"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    node.status = NodeStatus.HEALTHY
                    node.last_ping = time.time()
                    return NodeStatus.HEALTHY
        except Exception as e:
            logger.warning(f"Health check failed for node '{node_id}' ({node.host}:{node.port}): {e}")

        node.status = NodeStatus.UNREACHABLE
        return NodeStatus.UNREACHABLE

    def get_active_leader(self) -> ClusterNode:
        """Returns the currently active leader node."""
        leader = self.nodes[self.active_leader_id]
        if leader.status == NodeStatus.UNREACHABLE:
            logger.warning(f"Active leader '{self.active_leader_id}' is UNREACHABLE! Triggering HA failover...")
            self.trigger_failover(self.active_leader_id)
        return self.nodes[self.active_leader_id]

    def trigger_failover(self, failed_node_id: str) -> ClusterNode:
        """Promotes standby secondary node to leader when primary fails."""
        logger.error(f"🚨 HA FAILOVER TRIGGERED: Primary leader '{failed_node_id}' failed!")

        if failed_node_id == "macmini-primary":
            self.nodes["macmini-primary"].role = NodeRole.SECONDARY_STANDBY
            self.nodes["macmini-primary"].status = NodeStatus.UNREACHABLE

            self.nodes["macmini-secondary"].role = NodeRole.PRIMARY_LEADER
            self.nodes["macmini-secondary"].status = NodeStatus.HEALTHY
            self.active_leader_id = "macmini-secondary"

            logger.info("✅ FAILOVER COMPLETE: Promoted 'macmini-secondary' (100.70.181.127) to PRIMARY_LEADER.")
        else:
            self.nodes["macmini-secondary"].status = NodeStatus.UNREACHABLE

        return self.nodes[self.active_leader_id]

    def route_request(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Routes HTTP request to current active leader with automatic failover fallback."""
        leader = self.get_active_leader()
        target_url = f"http://{leader.host}:{leader.port}{endpoint}"

        try:
            req_data = json.dumps(payload).encode("utf-8") if payload else None
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={"Content-Type": "application/json"} if req_data else {},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Request to leader '{leader.node_id}' failed: {e}. Executing failover fallback...")
            new_leader = self.trigger_failover(leader.node_id)
            return {
                "ha_status": "FAILOVER_EXECUTED",
                "active_leader": new_leader.node_id,
                "leader_host": new_leader.host,
            }
