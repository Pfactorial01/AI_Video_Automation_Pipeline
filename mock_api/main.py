"""
Mock API for GenAIPro, Runway, Suno, RunPod ComfyUI, and Creatomate.
Serves static files from mock_assets and returns vendor-shaped JSON.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mock_api.config import settings

_lock = threading.Lock()
_scene_seq = 0


def _next_scene_index() -> int:
    global _scene_seq
    with _lock:
        _scene_seq += 1
        return (_scene_seq - 1) % max(1, settings.scene_count) + 1


def _asset_url(name: str) -> str:
    return f"{settings.base_url.rstrip('/')}/static/{name}"


# --- In-memory job stores (POST seeds, GET returns same payload) ---
_runway_tasks: dict[str, dict[str, Any]] = {}
_runpod_jobs: dict[str, dict[str, Any]] = {}
_creatomate_renders: dict[str, dict[str, Any]] = {}


# --- Request models (minimal; real APIs vary) ---


class GenAIPRO_TTS_Request(BaseModel):
    text: str = ""
    voice_id: str | None = None
    format: str = "mp3"
    speed: float = 1.0


class RunwayI2V_Request(BaseModel):
    image_url: str = ""
    prompt: str | None = None
    duration_sec: int = 5
    ratio: str | None = "1280:720"


class SunoGenerate_Request(BaseModel):
    prompt: str = ""
    instrumental: bool = True
    n_variants: int = Field(default=4, ge=1, le=8)


class RunPodComfy_Request(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class CreatomateRender_Request(BaseModel):
    template_id: str = ""
    modifications: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="AI Video Pipeline — Mock vendor APIs",
    version="1.0.0",
    description="Proof-of-work mocks. See /docs for schemas.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, Any]:
    """Entry point: links to docs and example static URLs (same host as BASE_URL)."""
    base = settings.base_url.rstrip("/")
    return {
        "service": "mock-api",
        "health": "/health",
        "docs": "/docs",
        "static_prefix": "/static/",
        "example_audio": _asset_url("vo.mp3"),
        "example_video": _asset_url("final.mp4"),
        "note": f"Fetch media at {base}/static/<filename> (CORS enabled).",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- GenAIPro (TTS / voiceover) ---


@app.post("/v1/genaipro/tts")
def genaipro_tts(body: GenAIPRO_TTS_Request) -> dict[str, Any]:
    """Text → voiceover URL (static vo.mp3)."""
    return {
        "job_id": f"gapr_{uuid.uuid4().hex[:12]}",
        "status": "completed",
        "audio_url": _asset_url("vo.mp3"),
        "duration_sec": 25.0,
        "format": body.format,
        "request_echo": {"text_len": len(body.text), "voice_id": body.voice_id},
    }


# --- Runway (image → video) ---


@app.post("/v1/runway/video")
def runway_create(body: RunwayI2V_Request) -> dict[str, Any]:
    """Create async task; poll GET /v1/runway/video/{task_id}."""
    task_id = f"rw_{uuid.uuid4().hex[:16]}"
    idx = _next_scene_index()
    vid = f"scene_{idx:02d}.mp4"
    _runway_tasks[task_id] = {
        "task_id": task_id,
        "status": "succeeded",
        "video_url": _asset_url(vid),
        "duration_sec": min(body.duration_sec, 30),
        "request_echo": {
            "image_url": body.image_url,
            "prompt": body.prompt,
        },
    }
    return {"task_id": task_id, "status": "pending"}


@app.get("/v1/runway/video/{task_id}")
def runway_get(task_id: str) -> dict[str, Any]:
    data = _runway_tasks.get(task_id)
    if not data:
        raise HTTPException(status_code=404, detail="Unknown task_id")
    return data


# --- Suno (background music) ---


@app.post("/v1/suno/generate")
def suno_generate(body: SunoGenerate_Request) -> dict[str, Any]:
    """Return four static BGM tracks."""
    n = min(body.n_variants, 4)
    tracks = []
    for i in range(1, n + 1):
        tracks.append(
            {
                "track_id": f"t{i}",
                "audio_url": _asset_url(f"bgm_{i}.mp3"),
                "duration_sec": 45.0,
            }
        )
    return {
        "batch_id": f"sun_{uuid.uuid4().hex[:12]}",
        "status": "completed",
        "tracks": tracks,
        "request_echo": {"prompt": body.prompt, "instrumental": body.instrumental},
    }


# --- RunPod ComfyUI ---


@app.post("/v1/runpod/comfy")
def runpod_comfy_submit(body: RunPodComfy_Request) -> dict[str, Any]:
    """Queue Comfy job; poll GET /v1/runpod/comfy/{job_id}."""
    job_id = f"rp_{uuid.uuid4().hex[:16]}"
    idx = _next_scene_index()
    png = f"scene_{idx:02d}.png"
    _runpod_jobs[job_id] = {
        "id": job_id,
        "status": "COMPLETED",
        "output": {
            "images": [
                {
                    "filename": png,
                    "url": _asset_url(png),
                }
            ]
        },
        "request_echo": {"input_keys": list(body.input.keys())},
    }
    return {"id": job_id, "status": "IN_QUEUE"}


@app.get("/v1/runpod/comfy/{job_id}")
def runpod_comfy_get(job_id: str) -> dict[str, Any]:
    data = _runpod_jobs.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return data


# --- Creatomate ---


@app.post("/v1/creatomate/renders")
def creatomate_render(body: CreatomateRender_Request) -> dict[str, Any]:
    """Start render; poll GET /v1/creatomate/renders/{render_id}."""
    render_id = f"cm_{uuid.uuid4().hex[:16]}"
    _creatomate_renders[render_id] = {
        "render_id": render_id,
        "status": "succeeded",
        "url": _asset_url("final.mp4"),
        "duration_sec": 20.0,
        "request_echo": {
            "template_id": body.template_id,
            "modifications_keys": list(body.modifications.keys()),
        },
    }
    return {"render_id": render_id, "status": "planned"}


@app.get("/v1/creatomate/renders/{render_id}")
def creatomate_get(render_id: str) -> dict[str, Any]:
    data = _creatomate_renders.get(render_id)
    if not data:
        raise HTTPException(status_code=404, detail="Unknown render_id")
    return data


# --- Static assets ---


def _mount_static() -> None:
    root = settings.assets_path()
    if not root.is_dir():
        raise FileNotFoundError(f"MOCK assets dir missing: {root}")
    app.mount(
        "/static",
        StaticFiles(directory=str(root)),
        name="static",
    )


_mount_static()

