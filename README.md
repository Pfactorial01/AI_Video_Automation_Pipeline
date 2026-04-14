# AI Video Automation Pipeline

Production goal: **turn a Google Sheet row into a finished MP4** — script and scene plan from an LLM, then real media APIs for voice, images, motion, music, and final assembly.

## Production architecture

1. **Google Sheets** — Queue of jobs (topic, status, optional limits). Operators add rows; automation updates the same row with URLs and status when done.
2. **n8n** — Orchestrates the flow: read row → call OpenAI → call vendors → write results back to the sheet (and optionally **Google Drive** for assets under a job folder).
3. **OpenAI (GPT-4o family)** — Structured JSON matching [schemas/script_and_scenes.schema.json](schemas/script_and_scenes.schema.json): title, full narration script, per-scene narration, still prompts, durations.
4. **TTS (e.g. GenAIPro)** — Full script → one continuous voiceover file for the timeline.
5. **Image generation (e.g. RunPod + ComfyUI)** — Still frames per scene from `visual_prompt` (batch / GPU worker).
6. **Image-to-video (e.g. Runway)** — Each still → short clip aligned to the scene model.
7. **Music (e.g. Suno)** — Background tracks; pick or license per your release policy.
8. **Render (e.g. Creatomate)** — Assemble VO + scene clips + BGM into a single **MP4** from a template (template ID and modifications from the pipeline manifest).

v1 timing: one VO file plus per-scene narration and approximate durations; the Creatomate template defines how clips and audio line up (not word-level alignment unless you add it later).

## Repository contents

| Area | Role |
|------|------|
| [workflows/](workflows/) | Generated n8n workflow JSON |
| [scripts/](scripts/) | Build workflow, OpenAI test utilities |
| [schemas/](schemas/) | Script + scenes JSON schema |
| [templates/google_sheet_columns.csv](templates/google_sheet_columns.csv) | Sheet column headers |
| [docs/phase1_accounts_and_apis.md](docs/phase1_accounts_and_apis.md) | Vendor accounts, OAuth, env vars |
| [docs/phase3_n8n.md](docs/phase3_n8n.md) | Import workflow, credentials, troubleshooting |

## Prerequisites

- **Python 3.12+** — Regenerate workflows and run script tests
- **n8n** — Host or cloud instance for the automation
- **Accounts** — OpenAI; Google (Sheets API, Drive if you store assets); each production vendor you enable (TTS, image GPU, I2V, music, Creatomate)

## Quick start (repository)

```bash
git clone <your-fork-url>
cd AI_Video_Automation_Pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r mock_api/requirements.txt
pip install -r scripts/requirements.txt
cp .env.example .env   # set OPENAI_API_KEY and future vendor keys
python3 scripts/build_n8n_workflow.py
```

Import `workflows/ai_video_pipeline_google_sheets.json` into n8n and attach credentials as described in [docs/phase3_n8n.md](docs/phase3_n8n.md).

## Local development (optional)

The repo includes a **Dockerfile** and **docker-compose** stack used for integration testing without production keys. For a placeholder API and static assets during development, see [docs/phase1_accounts_and_apis.md](docs/phase1_accounts_and_apis.md) and [docs/phase3_n8n.md](docs/phase3_n8n.md).
