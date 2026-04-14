#!/usr/bin/env bash
# Hit mock vendor endpoints; exit non-zero on failure.
# Usage: MOCK_BASE_URL=http://127.0.0.1:8080 ./scripts/verify_mock_vendors.sh
set -euo pipefail
BASE="${MOCK_BASE_URL:-http://127.0.0.1:8080}"

echo "== GET /health =="
curl -sf "${BASE}/health" | python3 -m json.tool

echo "== POST /v1/genaipro/tts =="
curl -sf -X POST "${BASE}/v1/genaipro/tts" -H 'Content-Type: application/json' \
  -d '{"text":"test","voice_id":"x","format":"mp3"}' | python3 -m json.tool

echo "== Runway POST + GET =="
TASK=$(curl -sf -X POST "${BASE}/v1/runway/video" -H 'Content-Type: application/json' \
  -d '{"image_url":"http://example.com/a.png","duration_sec":5}' | python3 -c "import sys,json; print(json.load(sys.stdin)['task_id'])")
curl -sf "${BASE}/v1/runway/video/${TASK}" | python3 -m json.tool

echo "== POST /v1/suno/generate =="
curl -sf -X POST "${BASE}/v1/suno/generate" -H 'Content-Type: application/json' \
  -d '{"prompt":"dark ambient","instrumental":true,"n_variants":4}' | python3 -m json.tool

echo "== RunPod POST + GET =="
JOB=$(curl -sf -X POST "${BASE}/v1/runpod/comfy" -H 'Content-Type: application/json' \
  -d '{"input":{"workflow":{}}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -sf "${BASE}/v1/runpod/comfy/${JOB}" | python3 -m json.tool

echo "== Creatomate POST + GET =="
RID=$(curl -sf -X POST "${BASE}/v1/creatomate/renders" -H 'Content-Type: application/json' \
  -d '{"template_id":"t1","modifications":{}}' | python3 -c "import sys,json; print(json.load(sys.stdin)['render_id'])")
curl -sf "${BASE}/v1/creatomate/renders/${RID}" | python3 -m json.tool

echo "== GET /static/vo.mp3 (expect 200) =="
curl -sf -o /dev/null -w "%{http_code}\n" "${BASE}/static/vo.mp3"

echo "All mock checks passed."
