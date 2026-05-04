from __future__ import annotations

import os
from importlib.resources import files
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
import time

from agentnxt_code_assist.aider_runner import AiderCodeAssist
from agentnxt_code_assist.auth import Provider, get_available_models, parse_provider, get_provider_login_url
from agentnxt_code_assist.config import Settings
from agentnxt_code_assist.schemas import AssistRequest, AssistResult

# Production configuration
PRODUCTION_MODE = os.environ.get("PRODUCTION", "false").lower() == "true"
API_KEY_REQUIRED = os.environ.get("API_KEY_REQUIRED", "false").lower() == "true"
REQUIRED_API_KEY = os.environ.get("REQUIRED_API_KEY", "")

app = FastAPI(title="AGenNext Code Assist", version="0.1.0")


# Security middleware - Rate limiting (simple in-memory)
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts: dict[str, list[float]] = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60
        
        # Clean old entries
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                ts for ts in self.request_counts[client_ip] if ts > window_start
            ]
        else:
            self.request_counts[client_ip] = []
        
        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )
        
        self.request_counts[client_ip].append(now)
        return await call_next(request)


# Add security middleware
# Configure CORS for production - restrict origins in production
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Add security headers (configure for production)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Initialize app
assistant = AiderCodeAssist()
settings = Settings.from_env()
API_BASE = os.environ.get("AGENNEXT_CODE_ASSIST_API_URL", f"http://{settings.host}:{settings.port}")
static_dir = files("agentnxt_code_assist").joinpath("static")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# === API Key Authentication ===

def verify_api_key(request: Request) -> bool:
    """Verify API key for protected endpoints."""
    if not API_KEY_REQUIRED:
        return True
    
    if not REQUIRED_API_KEY:
        return True
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        provided_key = auth_header[7:]
        if provided_key == REQUIRED_API_KEY:
            return True
    
    return False


def require_auth(func: Callable) -> Callable:
    """Decorator to require API key authentication."""
    async def wrapper(request: Request, *args, **kwargs):
        if not verify_api_key(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await func(request, *args, **kwargs)
    return wrapper


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(static_dir.joinpath("index.html")))


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "production": str(PRODUCTION_MODE).lower()}


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
        "production": PRODUCTION_MODE,
        "api_key_required": API_KEY_REQUIRED,
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
    return {"redirect": login_url}


@app.post("/auth/providers/{provider}")
def setup_provider(provider: str, setup: ProviderSetup) -> AuthResponse:
    """Configure a provider with API key and model."""
    try:
        p = parse_provider(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Store the configuration securely
    if setup.api_key:
        os.environ[f"{provider.upper()}_API_KEY"] = setup.api_key
    if setup.api_base:
        os.environ[f"{provider.upper()}_API_BASE"] = setup.api_base
    
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

from agentnxt_code_assist.local_llm import (
    MODELS,
    download_model,
    get_fallback_instructions,
    get_installed_models,
    is_llama_cpp_installed,
    run_local_model,
)


@app.get("/local/models")
def list_local_models() -> dict[str, any]:
    """List available local models."""
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
from typing import Any


@app.get("/memory/{repo_id}")
def get_repo_memory(repo_id: str) -> dict[str, str | None]:
    """Get memory for a repository."""
    from pathlib import Path
    repo_path = Path("/srv/agennext/repos") / repo_id
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


# === API Documentation ===

@app.get("/docs", include_in_schema=False)
async def redundant_docs():
    """Redirect to /redoc for API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/redoc")


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc API documentation."""
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AGenNext CodeAssist API</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:400,700|ROBOTO:300,400,700|INCONSOLATA:400,700" rel="stylesheet" type="text/css" />
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js" />
            <style>
                body { margin: 0; padding: 0; }
            </style>
        </head>
        <body>
            <redoc spec-url='/openapi.json'></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """,
        media_type="text/html"
    )


@app.get("/openapi.json", include_in_schema=False)
async def openapi():
    """Get OpenAPI schema."""
    schema = get_openapi(
        title="AGenNext CodeAssist API",
        version="0.1.0",
        description="API for AGenNext CodeAssist - AI Coding Assistant",
        routes=app.routes,
    )
    return schema


# === Continuous Improvement API ===

from agentnxt_code_assist.continuous_improvement import (
    BugCategory,
    BugSeverity,
    get_improver,
)


@app.get("/improvements/bugs")
def list_bugs(limit: int = 50) -> dict[str, list]:
    """Get recent bug records."""
    return {"bugs": get_improver().get_bugs(limit)}


@app.get("/improvements/unfixed")
def list_unfixed_bugs() -> dict[str, list]:
    """Get unfixed bugs."""
    return {"bugs": get_improver().get_unfixed_bugs()}


@app.get("/improvements/recommendations")
def list_recommendations() -> dict[str, list]:
    """Get pending recommendations."""
    return {"recommendations": get_improver().get_recommendations()}


@app.get("/improvements/report")
def improvement_report() -> str:
    """Get improvement report."""
    return get_improver().generate_report()


from pydantic import BaseModel


class BugInput(BaseModel):
    description: str
    severity: str = "medium"
    category: str = "unknown"
    exception_type: str | None = None
    exception_message: str | None = None
    file_path: str | None = None
    line_number: int | None = None


@app.post("/improvements/bugs")
def log_bug(input: BugInput) -> dict[str, str]:
    """Log a new bug."""
    try:
        severity_enum = BugSeverity(input.severity)
    except ValueError:
        severity_enum = BugSeverity.MEDIUM
    
    try:
        category_enum = BugCategory(input.category)
    except ValueError:
        category_enum = BugCategory.UNKNOWN
    
    bug_id = get_improver().log_bug(
        description=input.description,
        severity=severity_enum,
        category=category_enum,
        context={"exception_type": input.exception_type, "exception_message": input.exception_message},
        file_path=input.file_path,
        line_number=input.line_number,
    )
    
    return {"bug_id": bug_id, "status": "logged"}


class FixInput(BaseModel):
    fix_description: str
    skills_enhanced: list[str] = []
    tools_enhanced: list[str] = []


@app.post("/improvements/bugs/{bug_id}/fix")
def apply_fix(bug_id: str, input: FixInput) -> dict[str, bool]:
    """Mark a bug as fixed."""
    success = get_improver().apply_fix(
        bug_id,
        input.fix_description,
        input.skills_enhanced,
        input.tools_enhanced,
    )
    return {"success": success}


@app.post("/improvements/recommendations/{recommendation_id}/implement")
def implement_recommendation(recommendation_id: str, notes: str | None = None) -> dict[str, bool]:
    """Mark recommendation as implemented."""
    success = get_improver().implement_recommendation(recommendation_id, notes)
    return {"success": success}


# === Process Excellence API ===

from agentnxt_code_assist.process_excellence import (
    ProcessExcellence,
    get_excellence,
    start_task,
    complete_task,
    TaskStatus,
)


@app.get("/processes/statistics")
def process_statistics(task_name: str | None = None) -> dict:
    """Get process statistics."""
    return get_excellence().get_statistics(task_name)


@app.get("/processes/tasks")
def list_tasks(task_name: str | None = None, limit: int = 50) -> dict[str, list]:
    """List recent tasks."""
    return {"tasks": get_excellence().get_tasks(task_name, limit)}


@app.get("/processes/improvements")
def list_improvements() -> dict[str, list]:
    """Get pending improvements."""
    return {"improvements": get_excellence().get_pending_improvements()}


@app.get("/processes/report")
def process_report() -> str:
    """Get process excellence report."""
    return get_excellence().generate_report()


class TaskInput(BaseModel):
    task_name: str
    context: dict = {}


@app.post("/processes/tasks/start")
def task_start(input: TaskInput) -> dict[str, str]:
    """Start tracking a task."""
    task_id = start_task(input.task_name, input.context)
    return {"task_id": task_id, "status": "started"}


class CompleteInput(BaseModel):
    status: str = "completed"
    duration_ms: int | None = None
    error: str | None = None


@app.post("/processes/tasks/{task_id}/complete")
def task_complete(task_id: str, input: CompleteInput) -> dict[str, Any]:
    """Complete a task."""
    status = TaskStatus(input.status)
    duration = complete_task(task_id, status, input.duration_ms, input.error)
    return {"task_id": task_id, "duration_ms": duration}


class ApproveInput(BaseModel):
    approved: bool


@app.post("/processes/improvements/{improvement_id}/approve")
def approve_improvement(improvement_id: str, input: ApproveInput) -> dict[str, bool]:
    """Approve an improvement."""
    if input.approved:
        success = get_excellence().approve_improvement(improvement_id)
    else:
        success = True
    return {"success": success}


class ImplementInput(BaseModel):
    notes: str | None = None


@app.post("/processes/improvements/{improvement_id}/implement")
def implement_improvement_endpoint(
    improvement_id: str,
    input: ImplementInput
) -> dict[str, bool]:
    """Implement an approved improvement."""
    success = get_excellence().implement_improvement(
        improvement_id,
        input.notes,
    )
    return {"success": success}
