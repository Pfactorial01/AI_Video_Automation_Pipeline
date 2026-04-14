# Phase 1 — Accounts, APIs, and risk checks

This document locks **v1 decisions**, lists **official references** for each vendor, documents **Google OAuth** for Sheets and Drive, and explains how the **mock API** fits before production keys exist.

## v1 product decision: voiceover timing

**Chosen for v1:** one continuous **voiceover file** from the full script (GenAIPro or equivalent TTS), plus **per-scene narration_text** used for ordering and for optional equal-time or script-weighted cuts in Creatomate. **Word-level timestamps** are out of scope unless GenAIPro (or a later alignment step) exposes them; if they appear later, the same manifest can be extended.

**Implication:** Creatomate timeline is driven by **template logic** (fixed scene durations from `approx_duration_sec`, or equal split of total VO duration), not forced alignment.

---

## Mock vendor API (already running)

Use for n8n HTTP nodes and integration tests **without** GenAIPro / Runway / Suno / RunPod / Creatomate keys.

| Item | Value |
|------|--------|
| Compose | [docker-compose.yml](../docker-compose.yml) |
| Default URL | `http://127.0.0.1:8080` |
| OpenAPI | `http://127.0.0.1:8080/docs` |
| Base URL in JSON | Set `BASE_URL` in Compose so returned `*_url` fields are reachable from n8n (see below) |

**n8n on the same host as Docker:** use `http://127.0.0.1:8080`.

**n8n inside Docker, mock on host (Linux):** use `http://172.17.0.1:8080` or the host’s LAN IP. On macOS/Windows Docker Desktop, `http://host.docker.internal:8080` often works.

**Verification:** run [scripts/verify_mock_vendors.sh](../scripts/verify_mock_vendors.sh) with the stack up.

---

## OpenAI (GPT-4o)

**Role:** Script writing + structured **scenes[]** with `narration_text`, `visual_prompt`, `negative_prompt`, `approx_duration_sec`.

**Schema file:** [schemas/script_and_scenes.schema.json](../schemas/script_and_scenes.schema.json)

**Docs:** [OpenAI API — Structured outputs](https://platform.openai.com/docs/guides/structured-outputs), [Chat Completions](https://platform.openai.com/docs/api-reference/chat)

**Risk / mitigation:** Rate limits and cost scale with tokens; cap scene count in dev (e.g. Sheet `max_scenes`). Use a recent **`gpt-4o`** or **`gpt-4o-mini`** snapshot that supports `json_schema` / structured outputs.

**Local check:** [scripts/test_openai_script.py](../scripts/test_openai_script.py) (requires `OPENAI_API_KEY`).

---

## GenAIPro (TTS)

**Role:** Full script → VO MP3 (or equivalent).

**Phase 1 action:** In your GenAIPro dashboard, confirm **API base URL**, **auth header** (e.g. Bearer), **character limits**, and **whether SSML or timestamps** exist. Map the real response to the same fields the mock returns: `audio_url` or binary body, `duration_sec` if available.

**Mock parity:** `POST /v1/genaipro/tts` → `audio_url` pointing at `/static/vo.mp3`.

---

## Runway (Gen-3 image-to-video)

**Role:** Still image → short cinematic clip.

**Docs:** [Runway API](https://docs.dev.runwayml.com/) (pricing and async patterns are documented there).

**Phase 1 action:** Confirm **API vs app credits**, **async polling or webhooks**, **max duration per clip**, and **resolution** for Gen-3 Alpha.

**Mock parity:** `POST /v1/runway/video` then `GET /v1/runway/video/{task_id}` → `video_url`.

---

## Suno (music)

**Role:** Background music (e.g. four variants per job).

**Phase 1 action:** Confirm whether you use **official Suno** or a **third-party API**, and **commercial licensing** for YouTube. Define how “4 tracks” maps to API calls.

**Mock parity:** `POST /v1/suno/generate` → four `audio_url` entries (`bgm_1.mp3` … `bgm_4.mp3`).

---

## Creatomate (final render)

**Role:** Assemble VO + scene clips + BGM → one MP4.

**Docs:** [Creatomate API](https://creatomate.com/docs/api/reference/introduction), [How pricing works](https://creatomate.com/docs/account/how-does-the-pricing-work)

**Phase 1 action:** Create a **template** in the dashboard; note **template ID** and how **modifications** (JSON) map to elements. Confirm **render job** create + poll (or webhook).

**Mock parity:** `POST /v1/creatomate/renders` then `GET /v1/creatomate/renders/{render_id}` → `url` for `final.mp4`.

---

## RunPod (ComfyUI)

**Role:** GPU **serverless or pod** running ComfyUI workflows for batch stills.

**Docs:** [RunPod Docs](https://docs.runpod.io/)

**Phase 1 action:** Choose **serverless Comfy** vs **pod**; note **endpoint**, **queue behavior**, and **output** shape (image URLs or base64). See Phase 4 in the main plan for SDXL + LoRA.

**Mock parity:** `POST /v1/runpod/comfy` then `GET /v1/runpod/comfy/{job_id}` → PNG `url`.

---

## Google Cloud — Sheets + Drive

**Goal:** n8n reads a **Sheet** (topic, status, …) and writes **Drive** paths or URLs for assets.

### APIs to enable

In Google Cloud Console → **APIs & Services** → **Library**, enable:

- Google Sheets API  
- Google Drive API  

### OAuth consent screen

Configure **External** (or Internal for Workspace-only) and add scopes below (or broader scopes if you intentionally need full Drive).

### OAuth scopes (typical)

| Scope | Use |
|-------|-----|
| `https://www.googleapis.com/auth/spreadsheets` | Read/write the control sheet |
| `https://www.googleapis.com/auth/drive.file` | Create/upload files the app opens (per-file) |
| `https://www.googleapis.com/auth/drive` | Broader Drive access (only if needed) |

Prefer **least privilege**; many automations use **spreadsheets** + **drive.file** if the app only uploads to folders it creates.

### Credentials

- **OAuth 2.0 Client ID** (Desktop or Web application) for **n8n’s Google OAuth2 credential** (user authorizes once, tokens refresh).

Alternatively **Service account** + share Sheet and Drive folder with the SA email — good for headless servers, worse for “user’s own Drive” unless you use domain-wide delegation.

### n8n

Use **Google Sheets** and **Google Drive** nodes with **OAuth2 API** credentials pointing at your client ID/secret. **Redirect URI** must match what you register in Google Cloud (n8n shows the callback URL in the credential UI).

### Sheet template (Phase 1 stub)

Import column headers from [templates/google_sheet_columns.csv](../templates/google_sheet_columns.csv). Add rows with `status=QUEUED` when you are ready to trigger the workflow (Phase 3).

### Drive folder layout (target convention)

Use a single parent folder ID in n8n env (e.g. `GOOGLE_DRIVE_PARENT_FOLDER_ID`):

`/AI_Video_Jobs/{job_id}/` with subfolders `images/`, `videos/`, `audio/`, `manifests/`, `final/`.

The workflow will create these via Drive API or you pre-create the parent and let automation create job subfolders.

---

## Environment variables (see [.env.example](../.env.example))

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Script generation (required for real runs) |
| `MOCK_VENDOR_BASE_URL` | `http://127.0.0.1:8080` for n8n HTTP nodes in dev |
| (later) `GENAIPRO_*`, `RUNWAY_*`, etc. | Production vendor URLs and keys |

---

## Phase 1 checklist

- [ ] Mock API: `docker compose up` and [scripts/verify_mock_vendors.sh](../scripts/verify_mock_vendors.sh) passes  
- [ ] OpenAI: `OPENAI_API_KEY` set; [scripts/test_openai_script.py](../scripts/test_openai_script.py) returns valid JSON matching `script_and_scenes.schema.json`  
- [ ] Google Cloud: OAuth client created; Sheets + Drive APIs enabled; scopes chosen  
- [ ] GenAIPro / Runway / Suno / Creatomate / RunPod: dashboard or docs reviewed; async pattern and limits noted (live calls optional when keys exist)  
- [ ] v1 VO timing decision accepted (this doc)
