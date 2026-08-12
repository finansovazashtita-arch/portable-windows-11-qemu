#!/usr/bin/env bash
# Nightly Backup Cron Scheduler & Execution Runner
set -e

echo "🌙 Executing Scheduled Nightly Backup Sequence..."
python3 -c "from src.backup.nightly_backup import NightlyBackupManager; mgr = NightlyBackupManager(); summary = mgr.run_full_nightly_backup(); print(f'Backup status: {summary.overall_status}')"

echo "✅ Nightly Backup Completed Successfully!"
