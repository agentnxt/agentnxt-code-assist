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


# === Local Model/Fallback API ===

from agentnxt_code_assist.local_llm import MODELS, download_model, get_fallback_instructions, get_installed_models, is_llama_cpp_installed, run_local_model


@ app.get("/local/models")
def list_local_models() -> dict[str, any]:
    """List available local models."""
    # Check if air-gapped mode
    from agentnxt_code_assist.local_llm import is_air_gapped
    
    return {
        "installed": get_installed_models(),
        "available": MODELS,
        "air_gapped": is_air_gapped(),
    }


@app.post("/local/run")
async def run_local(prompt: dict[str, str]) -> dict[str, str]:
    """Run a prompt through local llama.cpp model."""
    from fastapi import HTTPException
    
    if not is_llama_cpp_installed():
        raise HTTPException(
            status_code=503,
            detail="llama.cpp not installed. Run: agennext-code-assist local help",
        )
    
    try:
        result = await run_local_model(
            prompt.get("prompt", ""),
            model=prompt.get("model", "llama3-8b"),
            max_tokens=prompt.get("max_tokens", 2048),
            temperature=prompt.get("temperature", 0.7),
        )
        return {"output": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/local/help")
def get_local_help() -> dict[str, str]:
    """Get fallback setup instructions."""
    return {"instructions": get_fallback_instructions()}


# === RAG/Memory API ===

from agentnxt_code_assist.memory_store import compact_memory as compact_repo_memory, read_memory, append_memory
from agentnxt_code_assist.rag_knowledge import query_cloud_rag, load_cross_repo_memory, get_rag_endpoint


@app.get("/memory/{repo_id}")
def get_repo_memory(repo_id: str) -> dict[str, str | None]:
    """Get memory for a repository."""
    from pathlib import Path
    repo_path = Path("/ srv/agennext/repos") / repo_id
    memory = read_memory(repo_path) if repo_path.exists() else None
    return {"repo": repo_id, "memory": memory}


@app.post("/memory/{repo_id}")
def add_to_memory(repo_id: str, result: dict[str, Any]) -> dict[str, str]:
    """Append to repository memory."""
    from pathlib import Path
    from agentnxt_code_assist.schemas import AssistResult
    repo_path = Path("/srv/agennext/repos") / repo_id
    if not repo_path.exists():
        raise HTTPException(status_code=404, detail="Repository not found")
    try:
        path = append_memory(repo_path, ".agennext/memory.md", AssistResult(**result))
        return {"repo": repo_id, "path": str(path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/{repo_id}/compact")
def compress_memory(repo_id: str) -> dict[str, int]:
    """Compress repository memory."""
    from pathlib import Path
    repo_path = Path("/srv/agennext/repos") / repo_id
    if not repo_path.exists():
        raise HTTPException(status_code=404, detail="Repository not found")
    removed = compact_repo_memory(repo_path)
    return {"repo": repo_id, "entries_removed": removed}


@app.post("/rag/query")
def search_rag(query: dict[str, str | int | None]) -> dict[str, list[str]]:
    """Query cloud RAG backend."""
    results = query_cloud_rag(
        query.get("query", ""),
        repo_name=query.get("repo_name"),
        top_k=query.get("top_k", 4),
        filter_tags=query.get("filter_tags"),
    )
    return {"results": results, "count": len(results)}


@app.get("/rag/endpoint")
def get_rag_config() -> dict[str, str | None]:
    """Get configured RAG endpoint."""
    return {"endpoint": get_rag_endpoint()}
