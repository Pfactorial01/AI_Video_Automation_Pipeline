#!/usr/bin/env python3
"""Generate the Google Sheet + mock n8n workflow JSON for import."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO / "schemas" / "script_and_scenes.schema.json"
BUILD_OPENAI_TEMPLATE = Path(__file__).resolve().parent / "n8n_build_openai_body.js"
PARSE_MOCK_TEMPLATE = Path(__file__).resolve().parent / "n8n_parse_and_mock.js"
PREPARE_SHEET_TEMPLATE = Path(__file__).resolve().parent / "n8n_prepare_sheet_update.js"
OUT_SHEETS = REPO / "workflows" / "ai_video_pipeline_google_sheets.json"

# When n8n runs in Docker, 127.0.0.1 is the container — mock on the host must be reached via the
# default bridge gateway (Linux) or host.docker.internal (Docker Desktop; add extra_hosts on Linux).
DEFAULT_VENDOR_BASE_URL = "http://172.17.0.1:8080"

GATE_JS = """// Only continue when status is QUEUED (case-insensitive)
const row = $input.first().json;
const st = String(row.status ?? '').trim().toUpperCase();
if (st !== 'QUEUED') return [];
return $input.all();
"""


def inject_schema(template: Path) -> str:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    schema.pop("$id", None)
    injected = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    raw = template.read_text(encoding="utf-8")
    if "__INJECT_SCHEMA__" not in raw:
        raise SystemExit(f"{template.name} must contain __INJECT_SCHEMA__ placeholder")
    return raw.replace("__INJECT_SCHEMA__", injected)


def read_js(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def nid() -> str:
    return str(uuid.uuid4())


def doc_sheet_rl() -> tuple[dict, dict]:
    document_id = {
        "__rl": True,
        "value": "REPLACE_SPREADSHEET_ID",
        "mode": "id",
        "cachedResultName": "Set spreadsheet ID in n8n after import",
    }
    sheet_name = {
        "__rl": True,
        "value": "Sheet1",
        "mode": "name",
        "cachedResultName": "Sheet1",
    }
    return document_id, sheet_name


def base_workflow(name: str, nodes: list, connections: dict) -> dict:
    return {
        "id": nid(),
        "name": name,
        "active": False,
        "nodes": nodes,
        "connections": connections,
        "settings": {"executionOrder": "v1"},
        "staticData": None,
        "meta": {"templateCredsSetupCompleted": False},
        "pinData": {},
        "tags": [],
    }


def build_google_sheets_workflow(build_js: str, parse_js: str, prepare_sheet_js: str) -> dict:
    gst_id = nid()
    gate_id = nid()
    norm_id = nid()
    build_id = nid()
    http_id = nid()
    parse_id = nid()
    prepare_id = nid()
    gsu_id = nid()
    note_id = nid()
    document_id, sheet_name = doc_sheet_rl()

    nodes = [
        {
            "parameters": {
                "authentication": "triggerOAuth2",
                "documentId": document_id,
                "sheetName": sheet_name,
                "event": "rowAdded",
                "options": {},
            },
            "id": gst_id,
            "name": "Google Sheets Trigger",
            "type": "n8n-nodes-base.googleSheetsTrigger",
            "typeVersion": 1,
            "position": [0, 0],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "jsCode": GATE_JS},
            "id": gate_id,
            "name": "Only status QUEUED",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [240, 0],
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {
                            "id": nid(),
                            "name": "row_number",
                            "value": "={{ Number($json.sheet_row ?? $json.row_number) || 0 }}",
                            "type": "number",
                        },
                        {
                            "id": nid(),
                            "name": "topic",
                            "value": "={{ $json.topic || $json.prompt || '' }}",
                            "type": "string",
                        },
                        {
                            "id": nid(),
                            "name": "vendor_base_url",
                            "value": f"={{{{ $json.vendor_base_url || '{DEFAULT_VENDOR_BASE_URL}' }}}}",
                            "type": "string",
                        },
                        {
                            "id": nid(),
                            "name": "max_scenes",
                            "value": "={{ $json.max_scenes || 5 }}",
                            "type": "string",
                        },
                    ]
                },
                "options": {},
            },
            "id": norm_id,
            "name": "Pipeline config",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [480, 0],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "jsCode": build_js},
            "id": build_id,
            "name": "Build OpenAI request",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [720, 0],
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://api.openai.com/v1/chat/completions",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "openAiApi",
                "sendBody": True,
                "contentType": "json",
                "specifyBody": "json",
                "jsonBody": "={{ $json.openaiBody }}",
                "options": {},
            },
            "id": http_id,
            "name": "OpenAI Chat Completions",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [960, 0],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "jsCode": parse_js},
            "id": parse_id,
            "name": "Parse + mock pipeline",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1200, 0],
        },
        {
            "parameters": {"mode": "runOnceForAllItems", "jsCode": prepare_sheet_js},
            "id": prepare_id,
            "name": "Prepare sheet row update",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1440, 0],
        },
        {
            "parameters": {
                "authentication": "oAuth2",
                "resource": "sheet",
                "operation": "update",
                "documentId": document_id,
                "sheetName": sheet_name,
                "columns": {
                    "mappingMode": "autoMapInputData",
                    "matchingColumns": ["sheet_row"],
                    "value": None,
                    "schema": [],
                },
                "options": {
                    "handlingExtraData": "ignoreIt",
                    "locationDefine": {
                        "values": {
                            "rangeDefinition": "specifyRange",
                            "headerRow": 1,
                            "firstDataRow": 2,
                        }
                    },
                },
            },
            "id": gsu_id,
            "name": "Update row in sheet",
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4.7,
            "position": [1680, 0],
        },
        {
            "parameters": {
                "content": "## Google Sheet = start here\n\n"
                "**Sheet columns** (header row): use [templates/google_sheet_columns.csv](../templates/google_sheet_columns.csv).\n\n"
                "1. Create a spreadsheet; paste headers. Set **document ID** in **Google Sheets Trigger** and **Update row in sheet** (from URL between `/d/` and `/edit`).\n"
                "2. Headers: include **sheet_row** — in row 2 put `=ROW()` and fill down so each row has its sheet row number (used to update the row; no manual id needed). Add **topic** (or **prompt**), **status**=`QUEUED`, optional **vendor_base_url**, **max_scenes**.\n"
                "3. **Credentials:** trigger + **Update row in sheet** use **Google Sheets OAuth2**; **OpenAI Chat Completions** uses **OpenAI API**.\n"
                "4. **Activate** the workflow; new rows with `QUEUED` run after the next poll.\n\n"
                "**Mock URL:** if **n8n runs in Docker**, set **vendor_base_url** to `http://172.17.0.1:8080` (or put that in the sheet column) — `127.0.0.1` points at the n8n container, not your host.\n\n"
                "**Update row** matches column **sheet_row** (=ROW value). Headers must match [templates/google_sheet_columns.csv](../templates/google_sheet_columns.csv) exactly (case-sensitive).",
                "height": 520,
                "width": 460,
            },
            "id": note_id,
            "name": "Sticky Note",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [1200, -380],
        },
    ]
    connections = {
        "Google Sheets Trigger": {
            "main": [[{"node": "Only status QUEUED", "type": "main", "index": 0}]]
        },
        "Only status QUEUED": {
            "main": [[{"node": "Pipeline config", "type": "main", "index": 0}]]
        },
        "Pipeline config": {
            "main": [[{"node": "Build OpenAI request", "type": "main", "index": 0}]]
        },
        "Build OpenAI request": {
            "main": [[{"node": "OpenAI Chat Completions", "type": "main", "index": 0}]]
        },
        "OpenAI Chat Completions": {
            "main": [[{"node": "Parse + mock pipeline", "type": "main", "index": 0}]]
        },
        "Parse + mock pipeline": {
            "main": [[{"node": "Prepare sheet row update", "type": "main", "index": 0}]]
        },
        "Prepare sheet row update": {
            "main": [[{"node": "Update row in sheet", "type": "main", "index": 0}]]
        },
    }
    return base_workflow("AI Video Pipeline — Google Sheet + Mock (Phase 3)", nodes, connections)


def main() -> None:
    build_js = inject_schema(BUILD_OPENAI_TEMPLATE)
    parse_js = read_js(PARSE_MOCK_TEMPLATE)
    prepare_sheet_js = read_js(PREPARE_SHEET_TEMPLATE)
    OUT_SHEETS.parent.mkdir(parents=True, exist_ok=True)

    w = build_google_sheets_workflow(build_js, parse_js, prepare_sheet_js)

    OUT_SHEETS.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_SHEETS}")


if __name__ == "__main__":
    main()
