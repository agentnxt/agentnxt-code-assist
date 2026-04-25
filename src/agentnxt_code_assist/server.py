"""HTTP API for AgentNXT Code Assist."""

from __future__ import annotations

import os
from importlib.resources import files

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agentnxt_code_assist.aider_runner import AiderCodeAssist
from agentnxt_code_assist.config import Settings
from agentnxt_code_assist.schemas import AssistRequest, AssistResult

app = FastAPI(title="AgentNXT Code Assist", version="0.1.0")
assistant = AiderCodeAssist()
settings = Settings.from_env()
static_dir = files("agentnxt_code_assist").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(static_dir.joinpath("index.html")))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict[str, object]:
    env_keys = [
        "OPENAI_API_KEY",
        "OPENAI_API_BASE",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "AIDER_MODEL",
        "AGENTNXT_CODE_ASSIST_MODEL",
    ]
    return {
        "model": settings.model,
        "auto_yes": settings.auto_yes,
        "auto_commits": settings.auto_commits,
        "dry_run": settings.dry_run,
        "env": {key: bool(os.getenv(key)) for key in env_keys},
    }


@app.post("/assist", response_model=AssistResult)
def assist(request: AssistRequest) -> AssistResult:
    result = assistant.run(request)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result
