"""Contextual awareness for the agent.

Provides awareness of:
- Environment state (online, offline, air-gapped)
- Available tools and capabilities
- Session history and past interactions  
- Current working context (repo, branch, files)
- User preferences and configuration
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json


# === Context Types ===

@dataclass
class EnvironmentState:
    """Current environment context."""
    is_air_gapped: bool = False
    is_online: bool = True
    network_available: bool = True
    has_internet: bool = True
    
    # Working directory context
    cwd: str = ""
    repo_path: str | None = None
    repo_name: str | None = None
    branch: str = "main"
    
    # Time context
    timezone: str = "UTC"
    current_time: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_prompt_text(self) -> str:
        """Generate prompt context."""
        lines = ["## Environment Context"]
        
        if self.is_air_gapped:
            lines.append("- 🔴 Air-gapped mode (no internet)")
        elif not self.is_online:
            lines.append("- 🟡 Offline mode")
        else:
            lines.append("- 🟢 Online mode")
        
        if self.repo_path:
            lines.append(f"- Repository: {self.repo_name or self.repo_path}")
            lines.append(f"- Branch: {self.branch}")
        
        lines.append(f"- Working directory: {self.cwd}")
        lines.append(f"- Timestamp: {self.current_time}")
        
        return "\n".join(lines)


@dataclass
class ToolState:
    """State of available tools."""
    # Local LLM
    local_llm_available: bool = False
    local_llm_models: list[str] = field(default_factory=list)
    local_llm_active: bool = False
    
    # Provider capabilities
    openai_available: bool = False
    anthropic_available: bool = False
    openrouter_available: bool = False
    
    # Security tools
    git_available: bool = True  # Assumed available
    has_gitleaks: bool = False
    has_trufflehog: bool = False
    
    def to_prompt_text(self) -> str:
        lines = ["## Available Tools"]
        
        # LLM Providers
        if self.local_llm_available:
            lines.append(f"- 🖥️ Local LLM: {', '.join(self.local_llm_models) or 'available'}")
            if self.local_llm_active:
                lines.append("  (currently active)")
        
        if self.openai_available:
            lines.append("- 🟢 OpenAI API")
        if self.anthropic_available:
            lines.append("- 🟢 Anthropic API")
        if self.openrouter_available:
            lines.append("- 🟢 OpenRouter")
        
        # Security
        if self.git_available:
            lines.append("- 🔧 Git CLI")
        
        return "\n".join(lines)


@dataclass
class SessionContext:
    """Current session state."""
    session_id: str = ""
    run_id: str = ""
    task_id: str | None = None
    objective: str = ""
    
    # Timeline constraints
    deadline: str | None = None  # ISO timestamp
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    # Cost constraints
    max_tokens: int = 0  # 0 = unlimited
    max_cost_usd: float = 0.0  # 0 = unlimited
    budget_exceeded: bool = False
    
    # Constraints
    max_files: int = 0  # 0 = unlimited
    max_changes: int = 0  # 0 = unlimited
    allowed_paths: list[str] = field(default_factory=list)  # empty = all
    blocked_paths: list[str] = field(default_factory=list)
    
    # History
    messages_count: int = 0
    tokens_used: int = 0
    files_modified: int = 0
    decisions_logged: int = 0
    
    # Progress
    current_step: int = 0
    total_steps: int = 0
    
    def to_prompt_text(self) -> str:
        lines = ["## Session Context"]
        lines.append(f"- Session: {self.session_id[:8] if self.session_id else 'new'}")
        lines.append(f"- Run: {self.run_id[:8] if self.run_id else 'new'}")
        
        if self.objective:
            lines.append(f"- Objective: {self.objective[:100]}")
        
        # Timeline
        if self.deadline:
            lines.append(f"- Deadline: {self.deadline}")
        
        # Cost
        if self.max_cost_usd > 0:
            lines.append(f"- Budget: ${self.max_cost_usd:.2f}")
            lines.append(f"- Tokens: {self.tokens_used:,}")
        
        # Constraints
        if self.max_files > 0:
            lines.append(f"- Max files: {self.max_files}")
        if self.max_changes > 0:
            lines.append(f"- Max changes: {self.max_changes}")
        
        lines.append(f"- Messages: {self.messages_count}")
        lines.append(f"- Files modified: {self.files_modified}")
        lines.append(f"- Decisions logged: {self.decisions_logged}")
        
        if self.current_step > 0:
            lines.append(f"- Progress: step {self.current_step}/{self.total_steps}")
        
        return "\n".join(lines)


@dataclass
class UserPreferences:
    """User-configured preferences."""
    # LLM preferences
    preferred_provider: str = ""  # "openai", "anthropic", "local", "gateway"
    preferred_model: str = ""
    
    # Behavior preferences
    fail_on_warning: bool = False
    verbose: bool = True
    auto_audit: bool = True
    
    # Feature flags
    use_local_fallback: bool = True
    use_memory: bool = True
    use_rag: bool = True
    
    @classmethod
    def from_env(cls) -> "UserPreferences":
        """Load from environment variables."""
        return cls(
            preferred_provider=os.getenv("PREFERRED_PROVIDER", ""),
            preferred_model=os.getenv("PREFERRED_MODEL", ""),
            fail_on_warning=os.getenv("FAIL_ON_WARNING", "false").lower() == "true",
            verbose=os.getenv("VERBOSE", "true").lower() != "false",
            auto_audit=os.getenv("AUTO_AUDIT", "true").lower() != "false",
            use_local_fallback=os.getenv("USE_LOCAL_FALLBACK", "true").lower() != "false",
            use_memory=os.getenv("USE_MEMORY", "true").lower() != "false",
            use_rag=os.getenv("USE_RAG", "false").lower() == "true",
        )
    
    def to_prompt_text(self) -> str:
        lines = ["## User Preferences"]
        
        if self.preferred_provider:
            lines.append(f"- Provider: {self.preferred_provider}")
        if self.preferred_model:
            lines.append(f"- Model: {self.preferred_model}")
        
        lines.append(f"- Verbose: {'yes' if self.verbose else 'no'}")
        lines.append(f"- Auto-audit: {'yes' if self.auto_audit else 'no'}")
        lines.append(f"- Local fallback: {'yes' if self.use_local_fallback else 'no'}")
        
        return "\n".join(lines)


# === Context Aggregator ===

@dataclass
class AgentContext:
    """Complete context for the agent."""
    environment: EnvironmentState = field(default_factory=EnvironmentState)
    tools: ToolState = field(default_factory=ToolState)
    session: SessionContext = field(default_factory=SessionContext)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Additional context
    recent_errors: list[str] = field(default_factory=list)
    last_decision: str = ""
    
    def to_prompt_text(self, max_lines: int = 30) -> str:
        """Generate full context prompt for the agent."""
        sections = [
            self.environment.to_prompt_text(),
            self.tools.to_prompt_text(),
            self.session.to_prompt_text(),
            self.preferences.to_prompt_text(),
        ]
        
        if self.recent_errors:
            sections.append("## Recent Errors")
            for err in self.recent_errors[-3:]:
                sections.append(f"- {err}")
        
        # Combine and limit
        full = "\n\n".join(sections)
        lines = full.splitlines()
        
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append("... (context truncated)")
        
        return "\n".join(lines)
    
    @classmethod
    def from_environment(cls) -> "AgentContext":
        """Auto-detect context from environment."""
        prefs = UserPreferences.from_env()
        
        # Detect environment state
        is_air_gapped = os.getenv("AIR_GAPPED", "").lower() == "true"
        if not is_air_gapped:
            # Try network test
            import urllib.request
            try:
                urllib.request.urlopen("https://api.github.com", timeout=3)
                has_internet = True
            except Exception:
                has_internet = False
                is_air_gapped = not has_internet
        else:
            has_internet = False
        
        cwd = os.getcwd() or os.getenv("PWD", "")
        
        return cls(
            environment=EnvironmentState(
                is_air_gapped=is_air_gapped,
                is_online=has_internet,
                network_available=has_internet,
                has_internet=has_internet,
                cwd=cwd,
            ),
            preferences=prefs,
        )


# === Context Aware Functions ===

def get_context() -> AgentContext:
    """Get current agent context."""
    return AgentContext.from_environment()


def get_context_prompt() -> str:
    """Get context prompt for agent."""
    return get_context().to_prompt_text()


def update_context(
    ctx: AgentContext,
    *,
    task_id: str | None = None,
    objective: str | None = None,
    step: int | None = None,
    total_steps: int | None = None,
    files_modified: int | None = None,
    decision: str | None = None,
    error: str | None = None,
    tokens_used: int | None = None,
    cost_usd: float | None = None,
) -> AgentContext:
    """Update context with new information."""
    if task_id:
        ctx.session.task_id = task_id
    if objective:
        ctx.session.objective = objective
    if step:
        ctx.session.current_step = step
    if total_steps:
        ctx.session.total_steps = total_steps
    if files_modified is not None:
        ctx.session.files_modified = files_modified
    if decision:
        ctx.session.decisions_logged += 1
        ctx.last_decision = decision
    if error:
        ctx.recent_errors.append(error)
        ctx.recent_errors = ctx.recent_errors[-10:]  # Keep last 10
    if tokens_used is not None:
        ctx.session.tokens_used = tokens_used
    if cost_usd is not None:
        # Check budget
        if ctx.session.max_cost_usd > 0 and cost_usd > ctx.session.max_cost_usd:
            ctx.session.budget_exceeded = True
    
    ctx.session.last_activity = datetime.now(UTC).isoformat()
    return ctx


def check_constraints(
    ctx: AgentContext,
    *,
    files_to_change: list[str] | None = None,
    estimated_tokens: int | None = None,
) -> tuple[bool, str]:
    """Check if proposed changes violate constraints.
    
    Returns: (allowed, reason)
    """
    session = ctx.session
    
    # Check timeline
    if session.deadline:
        deadline_dt = datetime.fromisoformat(session.deadline.replace("Z", "+00:00"))
        if datetime.now(UTC) > deadline_dt:
            return False, "Deadline exceeded"
    
    # Check budget
    if session.budget_exceeded:
        return False, "Budget exceeded"
    
    # Check tokens
    if estimated_tokens and session.max_tokens > 0:
        if session.tokens_used + estimated_tokens > session.max_tokens:
            return False, "Token limit would be exceeded"
    
    # Check file limits
    if files_to_change and session.max_files > 0:
        if len(files_to_change) > session.max_files:
            return False, f"Max {session.max_files} files allowed"
    
    # Check blocked paths
    if files_to_change and session.blocked_paths:
        for path in files_to_change:
            for blocked in session.blocked_paths:
                if blocked in path:
                    return False, f"Path {path} is blocked"
    
    # Check allowed paths
    if files_to_change and session.allowed_paths:
        for path in files_to_change:
            allowed = False
            for allowed_path in session.allowed_paths:
                if path.startswith(allowed_path):
                    allowed = True
                    break
            if not allowed:
                return False, f"Path {path} not in allowed list"
    
    return True, "OK"


def get_remaining_budget(ctx: AgentContext) -> dict[str, float]:
    """Get remaining budget information."""
    session = ctx.session
    return {
        "tokens_remaining": max(0, session.max_tokens - session.tokens_used) if session.max_tokens > 0 else -1,
        "cost_remaining": max(0, session.max_cost_usd - (session.tokens_used * 0.00001)) if session.max_cost_usd > 0 else -1,  # rough estimate
        "files_remaining": max(0, session.max_files - session.files_modified) if session.max_files > 0 else -1,
    }


# === Context Persistence ===

_CONTEXT_FILE = ".agennext/agent_context.json"


def save_context(
    repo_path: Path,
    ctx: AgentContext,
    *,
    relative_path: str = _CONTEXT_FILE,
) -> Path:
    """Save context for future sessions."""
    ctx_path = (repo_path / relative_path).resolve()
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "environment": {
            "is_air_gapped": ctx.environment.is_air_gapped,
            "cwd": ctx.environment.cwd,
            "repo_path": ctx.environment.repo_path,
            "repo_name": ctx.environment.repo_name,
            "branch": ctx.environment.branch,
        },
        "session": {
            "session_id": ctx.session.session_id,
            "run_id": ctx.session.run_id,
            "task_id": ctx.session.task_id,
            "objective": ctx.session.objective,
            "started_at": ctx.session.started_at,
        },
        "preferences": {
            "preferred_provider": ctx.preferences.preferred_provider,
            "preferred_model": ctx.preferences.preferred_model,
            "fail_on_warning": ctx.preferences.fail_on_warning,
            "verbose": ctx.preferences.verbose,
        },
    }
    
    ctx_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ctx_path


def load_context(
    repo_path: Path,
    *,
    relative_path: str = _CONTEXT_FILE,
) -> AgentContext | None:
    """Load context from previous session."""
    ctx_path = repo_path / relative_path
    if not ctx_path.exists():
        return None
    
    try:
        data = json.loads(ctx_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    
    env = data.get("environment", {})
    session = data.get("session", {})
    prefs = data.get("preferences", {})
    
    return AgentContext(
        environment=EnvironmentState(
            is_air_gapped=env.get("is_air_gapped", False),
            cwd=env.get("cwd", ""),
            repo_path=env.get("repo_path"),
            repo_name=env.get("repo_name"),
            branch=env.get("branch", "main"),
        ),
        session=SessionContext(
            session_id=session.get("session_id", ""),
            run_id=session.get("run_id", ""),
            task_id=session.get("task_id"),
            objective=session.get("objective", ""),
            started_at=session.get("started_at", ""),
        ),
        preferences=UserPreferences(
            preferred_provider=prefs.get("preferred_provider", ""),
            preferred_model=prefs.get("preferred_model", ""),
            fail_on_warning=prefs.get("fail_on_warning", False),
            verbose=prefs.get("verbose", True),
        ),
    )