# Phase 3 — n8n workflow (Google Sheet + mock vendors)

## Workflow

| Workflow file | Entry point | Use case |
|---------------|-------------|----------|
| [workflows/ai_video_pipeline_google_sheets.json](../workflows/ai_video_pipeline_google_sheets.json) | **Google Sheets Trigger** | Rows in the sheet; ends with **Update row in sheet**. |

Flow: **Pipeline config** → **Build OpenAI request** (Code) → **OpenAI Chat Completions** (HTTP Request, OpenAI credential) → **Parse + mock pipeline** (Code, mock HTTP only) → **Prepare sheet row update** → **Update row in sheet**.

## Files

| File | Purpose |
|------|---------|
| [workflows/ai_video_pipeline_google_sheets.json](../workflows/ai_video_pipeline_google_sheets.json) | Generated workflow (import into n8n) |
| [scripts/n8n_build_openai_body.js](../scripts/n8n_build_openai_body.js) | Code: builds `openaiBody` (schema injected at build time) |
| [scripts/n8n_parse_and_mock.js](../scripts/n8n_parse_and_mock.js) | Code: parses OpenAI response + mock vendor HTTP calls |
| [scripts/n8n_prepare_sheet_update.js](../scripts/n8n_prepare_sheet_update.js) | Code: maps pipeline output to sheet columns for update |
| [scripts/build_n8n_workflow.py](../scripts/build_n8n_workflow.py) | Embeds the schema and writes `ai_video_pipeline_google_sheets.json` |

After changing the schema or any of the `.js` sources, regenerate:

```bash
python3 scripts/build_n8n_workflow.py
```

## Google Sheets (beginning and end of the pipeline)

1. Create a spreadsheet whose **first row** matches [templates/google_sheet_columns.csv](../templates/google_sheet_columns.csv). You need **sheet_row** (formula `=ROW()` on each data row — see below), **topic** or **prompt**, and **status**. **Update row in sheet** matches the real column **`sheet_row`** (not n8n’s special “row_number” match, which expects a column literally named `row_number`).
2. Import **AI Video Pipeline — Google Sheet + Mock (Phase 3)** from `workflows/ai_video_pipeline_google_sheets.json`.
3. Set **Document ID** (and sheet tab) on **Google Sheets Trigger** and on **Update row in sheet** (same spreadsheet). Replace `REPLACE_SPREADSHEET_ID` in the UI if needed.
4. **Credentials:** **Google Sheets Trigger** uses **Google Sheets Trigger OAuth2 API**; **Update row in sheet** uses **Google Sheets OAuth2** (`googleSheetsOAuth2Api`). **OpenAI Chat Completions** uses **OpenAI API** (`openAiApi`).
5. **Activate** the workflow. The trigger **polls**: when you **add a new row** with **status** = `QUEUED`, the workflow runs after the next poll.
6. **Only status QUEUED** skips rows whose status is not `QUEUED` (case-insensitive).
7. **Pipeline config** maps **sheet_row** → **row_number** (internal field for Code nodes), **topic** (or **prompt**), **vendor_base_url** (default `http://172.17.0.1:8080` when generated for Docker), **max_scenes** (default `5`).
8. After the pipeline succeeds, **Update row in sheet** sets **status** = `COMPLETE`, **output_mp4_url**, **voice_url**, and clears **error_message** / **n8n_execution_url** placeholders. **Matching columns** = **`sheet_row`** (same value as the `=ROW()` cell). The rowAdded trigger does **not** expose row numbers; **`=ROW()`** in a column gives each row its number so n8n can find and update the correct row.

**`sheet_row` column (required for the default path)**

- Add a column named **`sheet_row`** (header must match).
- In the **first data row** (e.g. row 2), enter `=ROW()` and copy the fill handle down so every data row has that formula. Google Sheets will show `2`, `3`, `4`, … — that value is what n8n uses to find the row to update.

**Example row**

| sheet_row | topic | status | … |
|-----------|--------|--------|---|
| `=ROW()` (shows as e.g. `5`) | How a taxi driver… | QUEUED | … |

Optional columns: `vendor_base_url`, `max_scenes` (override defaults).

## Prerequisites

1. **n8n** running at `http://localhost:5678` (or your URL).
2. **Mock API** on port **8080**: from the repo root, `docker compose up -d` (see [docker-compose.yml](../docker-compose.yml)). Media URLs in JSON use `BASE_URL` (see [.env.example](../.env.example)); static files are served at `/static/<filename>` with CORS enabled. If **n8n runs inside Docker**, it cannot reach the mock at `http://127.0.0.1:8080` (that is the n8n container itself). Use **`http://172.17.0.1:8080`** as `vendor_base_url` / pipeline default (Docker bridge to host), or **`http://host.docker.internal:8080`** on Docker Desktop; on Linux you may need `extra_hosts: ["host.docker.internal:host-gateway"]` on the n8n service. Put **mock-api and n8n on the same Docker network** and use `http://mock-api:8080` if you prefer.
3. **OpenAI API key** — create an **OpenAI API** credential in n8n and attach it to **OpenAI Chat Completions** (not the Code nodes).

## Import

### Option A — Docker CLI (same machine as container)

If n8n runs in Docker (container name `n8n` by default):

```bash
python3 scripts/build_n8n_workflow.py
./scripts/import_n8n_workflow.sh
```

`import_n8n_workflow.sh` **deletes all workflows** in that n8n instance, then imports `ai_video_pipeline_google_sheets.json` (so you get a single clean workflow). Re-attach credentials on the nodes after import if needed.

The exported file must include a top-level workflow `id` (the repo generator adds one); otherwise SQLite may return `NOT NULL constraint failed: workflow_entity.id`.

### Option B — n8n UI

1. **Workflows** → **Import from File** → choose `workflows/ai_video_pipeline_google_sheets.json`.
2. Open **AI Video Pipeline — Google Sheet + Mock (Phase 3)**.
3. Attach **OpenAI API** on **OpenAI Chat Completions**; Google credentials on **Google Sheets Trigger** and **Update row in sheet**. Code nodes do **not** use OpenAI credentials.
4. Save the workflow.

## Output

The last node returns JSON including:

- `title`, `voice_url`, `suno_tracks`, `scene_results` (image + video URL per scene)
- `final_mp4_url` — mock Creatomate output (`/static/final.mp4` on the mock server)
- `manifest` — combined object for later Drive/Creatomate integration

## Verification (smoke checks)

These can be run without executing the full n8n workflow:

| Check | Command / expectation |
|-------|------------------------|
| Mock API | `curl -s http://127.0.0.1:8080/health` → `{"status":"ok"}` |
| Static file | `curl -sI http://127.0.0.1:8080/static/vo.mp3` → `200` |
| n8n UI | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5678/` → `200` |
| OpenAI + schema | `python3 scripts/test_openai_script.py "your topic"` with `OPENAI_API_KEY` set (see [.env.example](../.env.example)) |

**Note:** `n8n execute --id=…` from the CLI while the n8n **server** is already running often fails (second process wants the same port). Prefer running from the UI after attaching credentials.

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| OpenAI errors | Credential on **OpenAI Chat Completions**; billing/limits on the OpenAI account. |
| Connection refused to `:8080` | `docker compose ps`; firewall; mock not started. |
| Empty or invalid JSON from OpenAI | Model must support `json_schema` (e.g. `gpt-4o-mini` in code). |
| `this.getCredentials is not a function` | Do **not** attach OpenAI credentials to Code nodes. Use **OpenAI Chat Completions** (HTTP Request). |
| Prepare sheet row update error | Add **`sheet_row`** with `=ROW()` on each data row and fill down. The **Update row** node must match on **`sheet_row`** (header spelling must match the CSV). |
| Sheet shows success but cells don’t change | Often **matching column** was **`row_number`** while the sheet has **`sheet_row`** only — re-import the generated workflow or set **Column to match on** to **`sheet_row`**. |
| Google Sheets Trigger never fires | Workflow must be **Active**; trigger is **polling**; spreadsheet shared with the Google account used for OAuth. |
| `REPLACE_SPREADSHEET_ID` | Open the trigger and **Update row** nodes in the UI and pick the document so the ID is filled in. |
| `ECONNREFUSED 127.0.0.1:8080` | n8n is in Docker: `127.0.0.1` is the container. Set **vendor_base_url** / sheet column to `http://172.17.0.1:8080` (or `host.docker.internal:8080`). Optionally set mock `BASE_URL` the same way so returned media URLs work from n8n. |
