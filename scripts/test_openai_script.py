#!/usr/bin/env python3
"""
Call OpenAI Chat Completions with JSON-schema structured output matching
schemas/script_and_scenes.schema.json. Requires OPENAI_API_KEY.

Usage (from repo root):
  export OPENAI_API_KEY=sk-...
  ./.venv/bin/python scripts/test_openai_script.py
  ./.venv/bin/python scripts/test_openai_script.py "Your topic here"
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "script_and_scenes.schema.json"

DEFAULT_TOPIC = "How a taxi driver helped take down a dangerous cartel — documentary style"


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("Set OPENAI_API_KEY to run this check.", file=sys.stderr)
        return 1

    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    # OpenAI expects the JSON Schema object; strip metaschema $id if present
    schema.pop("$schema", None)
    schema.pop("$id", None)

    try:
        from openai import OpenAI
    except ImportError:
        print("Install openai: pip install -r scripts/requirements.txt", file=sys.stderr)
        return 1

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_SCRIPT_MODEL", "gpt-4o-mini")

    system = (
        "You are a documentary scriptwriter for a faceless YouTube channel. "
        "Output must match the JSON schema exactly. "
        "Use cinematic, desaturated documentary tone; avoid graphic gore. "
        "Keep scenes to at most 8 for this test unless the schema allows more."
    )
    user = (
        f"Topic: {topic}\n\n"
        "Produce title, full_script (continuous VO), and scenes with distinct visual_prompt "
        "for each scene. approx_duration_sec should sum roughly to a 3–8 minute video."
    )

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "script_and_scenes",
                "strict": True,
                "schema": schema,
            },
        },
    )

    raw = completion.choices[0].message.content
    if not raw:
        print("Empty response", file=sys.stderr)
        return 1

    data = json.loads(raw)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
