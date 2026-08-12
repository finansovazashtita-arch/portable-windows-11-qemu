#!/usr/bin/env python3
"""
Deploys Microinvest Bank Statement OCR workflow to n8n PostgreSQL database on macmini-primary (100.83.83.8).
"""

import json
import subprocess
import sys

def main():
    workflow_path = "data/n8n_microinvest_ocr_workflow.json"
    with open(workflow_path, "r", encoding="utf-8") as f:
        wf = json.load(f)

    wf_id = "MicroinvestOCR01"
    name = wf.get("name", "Microinvest Bank Statement OCR & Delta Pro Automation")
    active = True
    nodes_json = json.dumps(wf.get("nodes", []))
    connections_json = json.dumps(wf.get("connections", {}))
    settings_json = json.dumps(wf.get("settings", {}))

    import uuid
    version_id = str(uuid.uuid4())

    sql = f"""
-- 1. Upsert workflow_entity
INSERT INTO workflow_entity (id, name, active, nodes, connections, settings, "versionId", "createdAt", "updatedAt")
VALUES (
  '{wf_id}',
  '{name.replace("'", "''")}',
  {str(active).lower()},
  '{nodes_json.replace("'", "''")}'::json,
  '{connections_json.replace("'", "''")}'::json,
  '{settings_json.replace("'", "''")}'::json,
  '{version_id}',
  NOW(),
  NOW()
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  active = EXCLUDED.active,
  nodes = EXCLUDED.nodes,
  connections = EXCLUDED.connections,
  settings = EXCLUDED.settings,
  "versionId" = EXCLUDED."versionId",
  "updatedAt" = NOW();

-- 2. Upsert workflow_history
INSERT INTO workflow_history ("versionId", "workflowId", authors, nodes, connections, autosaved, "createdAt", "updatedAt")
VALUES (
  '{version_id}',
  '{wf_id}',
  '[]',
  '{nodes_json.replace("'", "''")}'::json,
  '{connections_json.replace("'", "''")}'::json,
  false,
  NOW(),
  NOW()
)
ON CONFLICT ("versionId") DO UPDATE SET
  nodes = EXCLUDED.nodes,
  connections = EXCLUDED.connections,
  "updatedAt" = NOW();

-- 3. Upsert workflow_published_version
INSERT INTO workflow_published_version ("workflowId", "publishedVersionId", "createdAt", "updatedAt")
VALUES (
  '{wf_id}',
  '{version_id}',
  NOW(),
  NOW()
)
ON CONFLICT ("workflowId") DO UPDATE SET
  "publishedVersionId" = EXCLUDED."publishedVersionId",
  "updatedAt" = NOW();

-- 4. Upsert shared_workflow
INSERT INTO shared_workflow ("workflowId", "projectId", role, "createdAt", "updatedAt")
VALUES (
  '{wf_id}',
  '8Gi8ImHMHYP2FNHl',
  'workflow:owner',
  NOW(),
  NOW()
)
ON CONFLICT ("workflowId", "projectId") DO NOTHING;

-- 5. Upsert webhook_entity
INSERT INTO webhook_entity ("webhookPath", method, node, "webhookId", "workflowId")
VALUES (
  'microinvest-ocr',
  'POST',
  'Webhook Trigger',
  'microinvest-ocr-webhook-001',
  '{wf_id}'
)
ON CONFLICT ("webhookPath", method) DO UPDATE SET
  node = EXCLUDED.node,
  "workflowId" = EXCLUDED."workflowId";
"""

    remote_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "100.83.83.8",
        "docker exec -i n8n-ob-postgres psql -U n8n -d n8n"
    ]

    res = subprocess.run(remote_cmd, input=sql, capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    if res.returncode == 0 and "ERROR:" not in res.stderr:
        print("✅ Workflow successfully deployed to n8n database on macmini-primary!")
    else:
        print("❌ Failed to deploy workflow:", res.returncode)
        sys.exit(1)

if __name__ == "__main__":
    main()
