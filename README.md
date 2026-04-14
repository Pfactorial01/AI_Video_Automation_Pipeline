# AI Video Automation Pipeline

Mock vendor APIs, n8n workflow generation, and a Google Sheets–driven pipeline for scripted video experiments.

## Prerequisites

- Python 3.12+
- Docker (for the mock API)
- Optional: [ffmpeg](https://ffmpeg.org/) (to regenerate placeholder assets under `mock_assets/`)

## Setup

1. Clone the repository and enter the project directory.

2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r mock_api/requirements.txt
   pip install -r scripts/requirements.txt
   ```

3. Copy environment template and fill in secrets:

   ```bash
   cp .env.example .env
   ```

4. **Generate mock media** (required before building the Docker image; files are not stored in git):

   ```bash
   chmod +x mock_assets/generate_mock_assets.sh
   ./mock_assets/generate_mock_assets.sh
   ```

5. Start the mock API:

   ```bash
   docker compose up --build -d
   ```

   OpenAPI docs: http://localhost:8080/docs

## n8n workflow

Regenerate the workflow JSON from the scripts in `scripts/`, then import into n8n:

```bash
python3 scripts/build_n8n_workflow.py
```

See [docs/phase3_n8n.md](docs/phase3_n8n.md) for Google Sheets import and credentials.

## Documentation

- [docs/phase1_accounts_and_apis.md](docs/phase1_accounts_and_apis.md) — accounts and APIs
- [docs/phase3_n8n.md](docs/phase3_n8n.md) — n8n workflow and troubleshooting
