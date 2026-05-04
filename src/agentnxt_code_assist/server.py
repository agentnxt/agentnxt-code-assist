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


# === Project Management API ===

from agentnxt_code_assist.project_management import (
    ProjectManager,
    get_manager,
    ProjectStatus,
    TaskStatus,
    Priority,
)


@app.get("/projects/statistics")
def project_statistics(project_id: str | None = None) -> dict:
    """Get project statistics."""
    return get_manager().get_statistics(project_id)


@app.get("/projects")
def list_projects(status: str | None = None) -> dict[str, list]:
    """List all projects."""
    proj_status = None
    if status:
        try:
            proj_status = ProjectStatus(status)
        except ValueError:
            pass
    return {"projects": get_manager().list_projects(proj_status)}


@app.get("/projects/{project_id}")
def get_project(project_id: str) -> dict:
    """Get project details."""
    project = get_manager().get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


class ProjectInput(BaseModel):
    name: str
    description: str = ""
    due_date: str | None = None


@app.post("/projects")
def create_project(input: ProjectInput) -> dict[str, str]:
    """Create a new project."""
    project_id = get_manager().create_project(input.name, input.description, input.due_date)
    return {"project_id": project_id, "status": "created"}


class UpdateProjectInput(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: str | None = None


@app.put("/projects/{project_id}")
def update_project(project_id: str, input: UpdateProjectInput) -> dict[str, bool]:
    """Update project."""
    status = None
    if input.status:
        try:
            status = ProjectStatus(input.status)
        except ValueError:
            pass
    
    success = get_manager().update_project(
        project_id,
        input.name,
        input.description,
        status,
        input.due_date,
    )
    return {"success": success}


@app.delete("/projects/{project_id}")
def delete_project(project_id: str) -> dict[str, bool]:
    """Delete project."""
    success = get_manager().delete_project(project_id)
    return {"success": success}


class TaskInput(BaseModel):
    name: str
    description: str = ""
    priority: str = "medium"
    due_date: str | None = None


@app.post("/projects/{project_id}/tasks")
def add_task(project_id: str, input: TaskInput) -> dict[str, str]:
    """Add task to project."""
    try:
        priority = Priority(input.priority)
    except ValueError:
        priority = Priority.MEDIUM
    
    task_id = get_manager().add_task(
        project_id,
        input.name,
        input.description,
        priority,
        input.due_date,
    )
    return {"task_id": task_id, "status": "created"}


class UpdateTaskInput(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: str | None = None


@app.put("/projects/{project_id}/tasks/{task_id}")
def update_task(project_id: str, task_id: str, input: UpdateTaskInput) -> dict[str, bool]:
    """Update task."""
    status = None
    if input.status:
        try:
            status = TaskStatus(input.status)
        except ValueError:
            pass
    
    priority = None
    if input.priority:
        try:
            priority = Priority(input.priority)
        except ValueError:
            pass
    
    success = get_manager().update_task(
        project_id,
        task_id,
        status,
        input.name,
        input.description,
        priority,
        input.due_date,
    )
    return {"success": success}


@app.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: str, task_id: str) -> dict[str, bool]:
    """Delete task."""
    success = get_manager().delete_task(project_id, task_id)
    return {"success": success}


class MilestoneInput(BaseModel):
    name: str
    description: str = ""
    due_date: str | None = None


@app.post("/projects/{project_id}/milestones")
def add_milestone(project_id: str, input: MilestoneInput) -> dict[str, str]:
    """Add milestone to project."""
    milestone_id = get_manager().add_milestone(
        project_id,
        input.name,
        input.description,
        input.due_date,
    )
    return {"milestone_id": milestone_id, "status": "created"}


@app.post("/projects/{project_id}/milestones/{milestone_id}/complete")
def complete_milestone(project_id: str, milestone_id: str) -> dict[str, bool]:
    """Complete milestone."""
    success = get_manager().complete_milestone(project_id, milestone_id)
    return {"success": success}


class DependencyInput(BaseModel):
    from_task_id: str
    to_task_id: str
    dependency_type: str = "blocks"


@app.post("/projects/{project_id}/dependencies")
def add_dependency(project_id: str, input: DependencyInput) -> dict[str, str]:
    """Add task dependency."""
    dependency_id = get_manager().add_dependency(
        input.from_task_id,
        input.to_task_id,
        input.dependency_type,
    )
    return {"dependency_id": dependency_id, "status": "created"}


@app.get("/projects/{project_id}/tasks/{task_id}/blocked")
def get_blocked_tasks(project_id: str, task_id: str) -> dict[str, list]:
    """Get tasks blocked by given task."""
    return {"tasks": get_manager().get_blocked_tasks(project_id, task_id)}


@app.get("/projects/report")
def project_report() -> str:
    """Get project management report."""
    return get_manager().generate_report()


# === Daily Status API ===

from agentnxt_code_assist.daily_status import (
    DailyStatusReporter,
    get_reporter,
)


@app.get("/daily/summary")
def daily_summary() -> dict:
    """Get today's summary."""
    return asdict(get_reporter().generate_summary())


@app.get("/daily/report/email")
def email_report() -> dict[str, str]:
    """Generate email report."""
    subject, body = get_reporter().generate_email_report()
    return {"subject": subject, "body": body}


@app.get("/daily/report/slack")
def slack_report() -> dict:
    """Generate Slack report."""
    return get_reporter().generate_slack_report()


@app.post("/daily/send")
def send_daily_report() -> dict:
    """Send daily report via all configured channels."""
    return get_reporter().send_all()


class CompletedTaskInput(BaseModel):
    task_name: str
    description: str = ""


@app.post("/daily/completed")
def log_completed_task(input: CompletedTaskInput) -> dict[str, str]:
    """Log a completed task."""
    task_id = get_reporter().add_completed_task(input.task_name, input.description)
    return {"task_id": task_id, "status": "logged"}


class PlanInput(BaseModel):
    task_name: str
    priority: str = "medium"


@app.post("/daily/plan")
def add_daily_plan(input: PlanInput) -> dict[str, str]:
    """Add plan for next day."""
    plan_id = get_reporter().add_plan(input.task_name, input.priority)
    return {"plan_id": plan_id, "status": "logged"}


class BlockerInput(BaseModel):
    description: str
    severity: str = "medium"


@app.post("/daily/blockers")
def add_blocker(input: BlockerInput) -> dict[str, str]:
    """Add a blocker."""
    blocker_id = get_reporter().add_blocker(input.description, input.severity)
    return {"blocker_id": blocker_id, "status": "logged"}


@app.post("/daily/blockers/{blocker_id}/resolve")
def resolve_blocker(blocker_id: str) -> dict[str, bool]:
    """Resolve a blocker."""
    success = get_reporter().resolve_blocker(blocker_id)
    return {"success": success}


# === Jira Integration API ===

from agentnxt_code_assist.jira_integration import (
    JiraIntegration,
    get_jira,
    JiraIssueType,
    JiraPriority,
    JiraStatus,
)


@app.get("/jira/config")
def jira_config() -> dict:
    """Get Jira configuration status."""
    return {
        "configured": get_jira().config.is_configured,
        "url": get_jira().config.url,
        "project_key": get_jira().config.project_key,
    }


@app.get("/jira/issues")
def list_jira_issues(jql: str = "") -> dict[str, list]:
    """Search Jira issues."""
    return {"issues": get_jira().search_issues(jql)}


@app.get("/jira/issues/{jira_key}")
def get_jira_issue(jira_key: str) -> dict:
    """Get Jira issue details."""
    issue = get_jira().get_issue(jira_key)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


class JiraIssueInput(BaseModel):
    summary: str
    description: str = ""
    issue_type: str = "Task"
    priority: str = "Medium"
    parent_key: str | None = None


@app.post("/jira/issues")
def create_jira_issue(input: JiraIssueInput) -> dict:
    """Create a Jira issue."""
    try:
        issue_type = JiraIssueType(input.issue_type)
    except ValueError:
        issue_type = JiraIssueType.TASK
    
    try:
        priority = JiraPriority(input.priority)
    except ValueError:
        priority = JiraPriority.MEDIUM
    
    return get_jira().create_issue(
        input.summary,
        input.description,
        issue_type,
        priority,
        input.parent_key,
    )


class JiraUpdateInput(BaseModel):
    summary: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None


@app.put("/jira/issues/{jira_key}")
def update_jira_issue(jira_key: str, input: JiraUpdateInput) -> dict:
    """Update a Jira issue."""
    status = None
    if input.status:
        try:
            status = JiraStatus(input.status)
        except ValueError:
            pass
    
    priority = None
    if input.priority:
        try:
            priority = JiraPriority(input.priority)
        except ValueError:
            pass
    
    return get_jira().update_issue(
        jira_key,
        input.summary,
        input.description,
        status,
        priority,
    )


@app.post("/jira/issues/{jira_key}/transition")
def transition_jira_issue(jira_key: str, status: str) -> dict:
    """Transition Jira issue."""
    try:
        status_enum = JiraStatus(status)
    except ValueError:
        return {"error": "Invalid status"}
    
    return get_jira().transition_issue(jira_key, status_enum)


class JiraLinkInput(BaseModel):
    from_key: str
    to_key: str
    link_type: str = "Blocks"


@app.post("/jira/links")
def link_jira_issues(input: JiraLinkInput) -> dict:
    """Link two Jira issues."""
    return get_jira().link_issue(input.from_key, input.to_key, input.link_type)


@app.post("/jira/sync/{project_id}/from")
def sync_from_jira(project_id: str) -> dict:
    """Sync tasks from Jira to local project."""
    return get_jira().sync_from_jira(project_id)


@app.post("/jira/sync/{project_id}/to")
def sync_to_jira(project_id: str) -> dict:
    """Sync local tasks to Jira."""
    return get_jira().sync_to_jira(project_id)


@app.get("/jira/mappings")
def list_jira_mappings() -> dict[str, list]:
    """Get Jira-local mappings."""
    return {"mappings": get_jira().get_mappings()}
