#!/usr/bin/env bash
# Execute Continuous DR Multi-Region Replication Runner across macmini nodes
set -e

echo "🔄 Running Continuous DR Multi-Region Replication Sync..."
python3 -c "from src.backup.disaster_recovery_replication import DRReplicationManager; mgr = DRReplicationManager(); res = mgr.run_full_dr_sync(); print(f'DR Replication Completed: {res[\"successful_syncs\"]}/{res[\"replications_count\"]} synced.')"

echo "✅ DR Replication Finished Successfully!"
