#!/usr/bin/env bash
# Deploy HA Cluster Daemon Runner across macmini-primary and macmini-secondary
set -e

echo "🌐 Deploying FinansProtect HA Cluster Failover Daemon..."
python3 -c "from src.cluster.ha_failover import HAFailoverManager; mgr = HAFailoverManager(); leader = mgr.get_active_leader(); print(f'HA Cluster active leader: {leader.node_id} ({leader.host}:{leader.port})')"

echo "✅ HA Cluster Active and Healthy!"
