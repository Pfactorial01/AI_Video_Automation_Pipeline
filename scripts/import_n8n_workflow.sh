#!/usr/bin/env bash
# Remove all workflows in the local Docker n8n instance, then import the Google Sheet + mock workflow.
# Credentials in n8n are NOT deleted (stored separately).
#
# Usage: ./scripts/import_n8n_workflow.sh [container_name]
# Default container: n8n
#
# Requires: workflows/ai_video_pipeline_google_sheets.json (run: python3 scripts/build_n8n_workflow.py)
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${1:-n8n}"
SHEETS="$REPO/workflows/ai_video_pipeline_google_sheets.json"

if [[ ! -f "$SHEETS" ]]; then
  echo "Missing $SHEETS — run: python3 scripts/build_n8n_workflow.py" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Container '$CONTAINER' is not running. Start n8n first." >&2
  exit 1
fi

echo "Deleting all workflows from $CONTAINER (SQLite)..."
docker exec -w /usr/local/lib/node_modules/n8n "$CONTAINER" node -e "
const sqlite3 = require('sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.serialize(() => {
  db.run('PRAGMA foreign_keys = ON');
  db.run('DELETE FROM webhook_entity WHERE workflowId IN (SELECT id FROM workflow_entity)');
  db.run('DELETE FROM workflow_entity', function (err) {
    if (err) {
      console.error(err);
      process.exit(1);
    }
    console.log('Deleted', this.changes, 'workflow(s).');
    db.close();
  });
});
"

docker cp "$SHEETS" "$CONTAINER:/tmp/ai_video_pipeline_google_sheets.json"
docker exec "$CONTAINER" n8n import:workflow --input=/tmp/ai_video_pipeline_google_sheets.json

echo "Imported: $SHEETS"
docker exec "$CONTAINER" n8n list:workflow
