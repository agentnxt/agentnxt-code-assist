"""HTTP API for AGenNext Code Assist."""

from __future__ import annotations

import os
from importlib.resources import files

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agentnxt_code_assist.aider_runner import AiderCodeAssist
from agentnxt_code_assist.auth import Provider, get_available_models, parse_provider
from agentnxt_code_assist.config import Settings
from agentnxt_code_assist.schemas import AssistRequest, AssistResult

app = FastAPI(title="AGenNext Code Assist", version="0.1.0")
assistant = AiderCodeAssist()
settings = Settings.from_env()
API_BASE = os.environ.get("AGENNEXT_CODE_ASSIST_API_URL", f"http://{settings.host}:{settings.port}")
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
        "AGENNEXT_CODE_ASSIST_MODEL",
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


# === Provider/Auth API ===

from pydantic import BaseModel


class ProviderSetup(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    api_base: str | None = None
    enabled: bool = True


class AuthResponse(BaseModel):
    ok: bool
    message: str
    provider: str | None = None
    model: str | None = None
    models: list[str] | None = None
    login_url: str | None = None


@app.get("/auth/providers")
def list_providers() -> AuthResponse:
    """List available providers for OAuth login."""
    return AuthResponse(
        ok=True,
        message="Available providers",
        models=[p.value for p in Provider],
    )


@app.get("/auth/providers/{provider}")
def get_provider(provider: str) -> AuthResponse:
    """Get models and OAuth login URL for a specific provider."""
    try:
        p = parse_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    models = get_available_models(p)
    login_url = get_provider_login_url(p, f"{API_BASE}/auth/callback/{provider}")
    
    return AuthResponse(
        ok=True,
        message=f"Provider {provider}",
        provider=provider,
        models=models,
        login_url=login_url,
    )


@app.get("/auth/login/{provider}")
def login_with_provider(provider: str) -> dict[str, str]:
    """Redirect to provider's OAuth login page."""
    try:
        p = parse_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    login_url = get_provider_login_url(p, f"{API_BASE}/auth/callback/{provider}")
    
    # Store provider in session for callback
    return {"redirect": login_url}


@app.post("/auth/providers/{provider}")
def setup_provider(provider: str, setup: ProviderSetup) -> AuthResponse:
    """Configure a provider with API key and model."""
    try:
        p = parse_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Store the configuration (in production, persist to database)
    if setup.api_key:
        os.environ[f"{provider.upper()}_API_KEY"] = setup.api_key
    if setup.api_base:
        os.environ[f"{provider.upper()}_API_BASE"] = setup.api_base
    
    # Set model for this provider
    os.environ["AGENNEXT_CODE_ASSIST_MODEL"] = setup.model
    settings.model = setup.model
    
    return AuthResponse(
        ok=True,
        message=f"Provider {provider} configured with model {setup.model}",
        provider=provider,
        model=setup.model,
    )


@app.delete("/auth/providers/{provider}")
def remove_provider(provider: str) -> AuthResponse:
    """Remove a provider configuration."""
    try:
        p = parse_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Clear environment variables
    key = f"{provider.upper()}_API_KEY"
    if key in os.environ:
        del os.environ[key]
    
    return AuthResponse(
        ok=True,
        message=f"Provider {provider} removed",
        provider=provider,
    )
