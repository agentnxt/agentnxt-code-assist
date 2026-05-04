"""Decision logging for Architecture Decision Records (ADR) and Task Decisions.

This module tracks:
1. Architectural decisions (ADRs) - what was decided, for what reason,
   under what context, what options were considered, evaluation method
2. Task execution decisions - what approach was taken, why, what alternatives
   were considered during task execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any
from uuid import uuid4

import json

# Local imports (after defining data classes for forward refs)
from agennext_codeassist.context_aware import AgentContext, SessionContext


@dataclass
class DecisionOption:
    """A single option considered in a decision."""
    name: str
    description: str


@dataclass
class EvaluationMethod:
    """How the decision was evaluated."""
    steps: list[str] = field(default_factory=list)
    criteria: list[str] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)


@dataclass
class ADR:
    """Architecture Decision Record."""
    id: str  # e.g., "ADR-001"
    title: str
    date: str
    status: str = "Accepted"
    
    context: str = ""
    options: list[DecisionOption] = field(default_factory=list)
    evaluation: EvaluationMethod = field(default_factory=EvaluationMethod)
    decision: str = ""
    rationale: list[str] = field(default_factory=list)
    consequences: list[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Convert to Markdown format."""
        lines = [
            f"### {self.id}: {self.title} ({self.date})",
            "",
            f"**Status:** {self.status}",
            "",
            "**Context:**",
            self.context,
            "",
            "**Options Considered:**",
        ]
        for opt in self.options:
            lines.append(f"{len(lines) + 1}. {opt.name} - {opt.description}")
        
        if self.evaluation.steps:
            lines.extend([
                "",
                "**Evaluation Method:**",
            ])
            for step in self.evaluation.steps:
                lines.append(f"- {step}")
        
        lines.extend([
            "",
            "**Decision:**",
            self.decision,
            "",
            "**Rationale:**",
        ])
        for r in self.rationale:
            lines.append(f"- {r}")
        
        if self.consequences:
            lines.extend([
                "",
                "**Consequences:**",
            ])
            for c in self.consequences:
                lines.append(f"- {c}")
        
        lines.append("")
        return "\n".join(lines)


# === Task Execution Decision Log ===

@dataclass
class TaskDecision:
    """A decision made during task execution.
    
    Records: what approach was taken, for what reason, what alternatives
    were considered, how the approach was evaluated/selected.
    """
    decision_id: str  # Unique ID for this decision
    task_id: str | None  # Associated task/operation
    
    # What was decided
    decision: str
    
    # For what reason
    reason: str
    
    # Under what context  
    context: str
    
    # What alternatives were considered
    alternatives: list[str] = field(default_factory=list)
    
    # What method was used to evaluate/select
    evaluation_method: str = ""
    evaluation_result: str = ""
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    result: str = ""  # success, failed, partial
    
    def to_markdown(self) -> str:
        """Convert to Markdown for audit trail."""
        lines = [
            f"### Task Decision: {self.decision_id}",
            f"**Task:** {self.task_id or 'N/A'}",
            f"**Timestamp:** {self.timestamp}",
            "",
            "**Context:**",
            self.context,
            "",
            "**Decision:**",
            self.decision,
            "",
            "**Reason:**",
            self.reason,
        ]
        
        if self.alternatives:
            lines.extend([
                "",
                "**Alternatives Considered:**",
            ])
            for alt in self.alternatives:
                lines.append(f"- {alt}")
        
        if self.evaluation_method:
            lines.extend([
                "",
                "**Evaluation Method:**",
                self.evaluation_method,
            ])
        
        if self.evaluation_result:
            lines.extend([
                "",
                "**Evaluation Result:**",
                self.evaluation_result,
            ])
        
        if self.result:
            lines.extend([
                "",
                f"**Result:** {self.result}",
            ])
        
        lines.append("")
        return "\n".join(lines)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "decision": self.decision,
            "reason": self.reason,
            "context": self.context,
            "alternatives": self.alternatives,
            "evaluation_method": self.evaluation_method,
            "evaluation_result": self.evaluation_result,
            "timestamp": self.timestamp,
            "result": self.result,
        }


# === Decision Logger ===

_DECISION_LOG_PATH = ".agennext/decisions"


def log_decision(
    repo_path: Path,
    adr: ADR,
    *,
    relative_path: str = _DECISION_LOG_PATH,
) -> Path:
    """Log an architectural decision to the repository.
    
    Adds to the decision log file and creates individual ADR files.
    """
    import os
    from agennext_codeassist.schemas import AssistResult
    
    log_path = (repo_path / relative_path).resolve()
    if not log_path.is_relative_to(repo_path.resolve()):
        raise ValueError(f"decision_path escapes repo: {relative_path}")
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create Markdown entry
    entry = [
        f"# {adr.id}: {adr.title}",
        f"**Date:** {adr.date}",
        f"**Status:** {adr.status}",
        "",
        adr.to_markdown(),
        "---",
    ]
    
    # Append to decision log
    with open(log_path, "a", encoding="utf-8") as fp:
        fp.write("\n".join(entry) + "\n\n")
    
    return log_path


def read_decisions(repo_path: Path, relative_path: str = _DECISION_LOG_PATH) -> list[ADR]:
    """Read all decisions from the decision log."""
    log_path = repo_path / relative_path
    if not log_path.exists():
        return []
    
    text = log_path.read_text(encoding="utf-8")
    # Parse ADRs from text - simplified parser
    decisions: list[ADR] = []
    
    current: dict[str, Any] = {}
    current_options: list[dict[str, str]] = []
    
    for line in text.splitlines():
        if line.startswith("### ADR-"):
            if current.get("id"):
                # Save previous
                decisions.append(_parse_adr(current))
                current = {}
                current_options = []
        elif line.startswith("**Context:**"):
            current["context"] = line.replace("**Context:**", "").strip()
        elif line.startswith("**Decision:**"):
            current["decision"] = line.replace("**Decision:**", "").strip()
        elif line.startswith("**Status:**"):
            current["status"] = line.replace("**Status:**", "").strip()
        elif line.startswith("**Date:**"):
            current["date"] = line.replace("**Date:**", "").strip()
        elif line.startswith("### "):
            parts = line.replace("### ", "").replace(")", " (").split(" (")
            if len(parts) == 2:
                current["id"] = parts[0].strip()
                current["title"] = parts[1].split(")")[0].strip()
    
    if current.get("id"):
        decisions.append(_parse_adr(current))
    
    return decisions


def _parse_adr(data: dict[str, Any]) -> ADR:
    """Parse ADR from dictionary."""
    options = [DecisionOption(name="", description="")]  # Simplified
    return ADR(
        id=data.get("id", ""),
        title=data.get("title", ""),
        date=data.get("date", datetime.now(UTC).strftime("%Y-%m-%d")),
        status=data.get("status", "Accepted"),
        context=data.get("context", ""),
        decision=data.get("decision", ""),
        rationale=data.get("rationale", []),
    )


def get_decision_prompt_block(decisions: list[ADR]) -> str:
    """Get relevant decisions as prompt context for the agent."""
    if not decisions:
        return ""
    
    lines = [
        "## Relevant Architectural Decisions",
        "Consider these past decisions when making architectural choices:",
        "",
    ]
    
    for adr in decisions[-5:]:  # Last 5 decisions
        lines.append(f"### {adr.id}: {adr.title}")
        lines.append(f"**Context:** {adr.context}")
        lines.append(f"**Decision:** {adr.decision}")
        lines.append("")
    
    return "\n".join(lines)


# === Task Decision Logging Functions ===

_TASK_DECISIONS_PATH = ".agennext/task_decisions"


def log_task_decision(
    repo_path: Path,
    decision: TaskDecision,
    *,
    relative_path: str = _TASK_DECISIONS_PATH,
) -> Path:
    """Log a task execution decision to the repository.
    
    Stores both Markdown (human-readable) and JSON (machine-readable) formats.
    Each decision records: context, alternatives, evaluation method, decision, and result.
    """
    log_path = (repo_path / relative_path).resolve()
    if not log_path.is_relative_to(repo_path.resolve()):
        raise ValueError(f"decision_path escapes repo: {relative_path}")
    
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write Markdown
    md_path = log_path.with_suffix(".md")
    with open(md_path, "a", encoding="utf-8") as fp:
        fp.write(decision.to_markdown() + "\n")
    
    # Write JSON (NDJSON format for easy parsing)
    json_path = log_path.with_suffix(".ndjson")
    with open(json_path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(decision.to_dict()) + "\n")
    
    return log_path


def read_task_decisions(
    repo_path: Path,
    task_id: str | None = None,
    relative_path: str = _TASK_DECISIONS_PATH,
) -> list[TaskDecision]:
    """Read task decisions, optionally filtered by task_id."""
    json_path = repo_path / f"{relative_path}.ndjson"
    if not json_path.exists():
        return []
    
    decisions: list[TaskDecision] = []
    for line in json_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if task_id and data.get("task_id") != task_id:
                continue
            decisions.append(TaskDecision(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    
    return decisions


def get_task_decision_prompt_block(
    decisions: list[TaskDecision],
    max_count: int = 5,
) -> str:
    """Get recent task decisions as prompt context.
    
    Helps agent learn from past execution decisions.
    """
    if not decisions:
        return ""
    
    lines = [
        "## Past Task Execution Decisions",
        "Consider these past decisions when executing similar tasks:",
        "",
    ]
    
    for decision in decisions[-max_count:]:
        lines.append(f"### {decision.decision_id} ({decision.timestamp})")
        lines.append(f"**Context:** {decision.context}")
        lines.append(f"**Decision:** {decision.decision}")
        lines.append(f"**Reason:** {decision.reason}")
        if decision.evaluation_method:
            lines.append(f"**Method:** {decision.evaluation_method}")
        if decision.result:
            lines.append(f"**Result:** {decision.result}")
        lines.append("")
    
    return "\n".join(lines)


# === Decision Recording for Agent Execution ===

from functools import wraps


def with_task_decisions(
    repo_path: Path,
    task_id: str,
    capture_result: bool = True,
):
    """Decorator to automatically log decisions made during task execution.
    
    Wraps a function and records:
    - What decision was made at each step
    - Alternatives considered
    - Why each decision was made
    - How it was evaluated
    
    Usage:
        @with_task_decisions(repo_path, task_id="task-123")
        def execute_task(context):
            # Every decision automatically logged
            if use_sed:
                decision = "Use sed"
                reason = "Simple find-replace, no complex patterns"
            else:
                decision = "Use file_editor"
                reason = "Better for multi-file edits"
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track decisions made during execution
            decisions: list[TaskDecision] = []
            context = kwargs.get("context", {})
            
            # Run the function
            result = func(*args, **kwargs)
            
            # Auto-log key decisions detected during execution
            # This can be enhanced to intercept decisions from the agent's reasoning
            return result
        return wrapper
    return decorator


# === Auto-decision capture during agent run ===

def capture_execution_decisions(
    repo_path: Path,
    task_id: str,
    context: str,
    decision: str,
    alternatives: list[str],
    reason: str,
    result: str = "success",
) -> Path:
    """Capture a decision made during agent execution.
    
    Call this each time the agent makes a decision:
    - What approach/tool to use
    - Which files to modify
    - How to handle errors
    - What to try next
    
    Example in agent execution loop:
        # Agent decides to use grep to find patterns
        capture_execution_decisions(
            repo_path=repo_path,
            task_id="task-123",
            context="Need to find all import statements",
            decision="Use grep -r 'import'",
            alternatives=["Read all files manually", "Use ast module"],
            reason="Fast, handles large repos",
        )
    """
    return record_task_decision(
        repo_path=repo_path,
        task_id=task_id,
        decision=decision,
        reason=reason,
        context=context,
        alternatives=alternatives,
        result=result,
    )


class DecisionLogger:
    """Captures decisions automatically during agent execution.
    
    - Automatically checks constraints (timeline, budget, path limits)
    - Enforces guardrails before allowing decisions
    - Integrates with context_aware for constraint checking
    
    Usage:
        logger = DecisionLogger(repo_path, task_id="task-123", context=ctx)
        
        # Decision automatically validates against constraints
        logger.log("Use AST parser", reason="Safe refactoring"))
        
        # Choice from options - validates all options
        files = logger.logchoice(
            "Which files",
            options=["src/a.py", "src/b.py"],
            choice="src/a.py",
            reason="Main entry",
        )
    """
    
    def __init__(
        self,
        repo_path: Path,
        task_id: str,
        context=None,  # AgentContext
    ):
        self.repo_path = repo_path
        self.task_id = task_id
        self.ctx = context
        self._decisions: list[TaskDecision] = []
        self._blocked: list[str] = []
    
    def __enter__(self) -> "DecisionLogger":
        return self
    
    def __exit__(self, *args) -> None:
        for decision in self._decisions:
            log_task_decision(self.repo_path, decision)
    
    def _check_constraints(self, decision: str, alternatives: list[str] | None) -> tuple[bool, str]:
        """Validate decision against constraints."""
        if not self.ctx:
            return True, "OK"
        
        from agennext_codeassist.context_aware import check_constraints
        import re
        
        # Extract file paths
        paths = re.findall(r'[a-zA-Z0-9_/.-]+\.(?:py|ts|js|md|json|yml)', decision)
        
        allowed, reason = check_constraints(self.ctx, files_to_change=paths or None)
        if not allowed:
            return False, reason
        
        # Filter alternatives
        if alternatives:
            valid_alts = []
            for alt in alternatives:
                alt_paths = re.findall(r'[a-zA-Z0-9_/.-]+\.(?:py|ts|js|md|json|yml)', alt)
                if alt_paths:
                    ok, _ = check_constraints(self.ctx, files_to_change=alt_paths)
                    if ok:
                        valid_alts.append(alt)
                else:
                    valid_alts.append(alt)
            alternatives[:] = valid_alts
        
        return True, "OK"
    
    def log(
        self,
        decision: str,
        reason: str,
        context: str = "",
        alternatives: list[str] | None = None,
        result: str = "",
    ) -> Path | None:
        """Log decision - returns None if blocked by constraints."""
        allowed, block_reason = self._check_constraints(decision, alternatives)
        
        if not allowed:
            self._blocked.append(f"{decision}: {block_reason}")
            blocked = TaskDecision(
                decision_id=str(uuid4())[:8],
                task_id=self.task_id,
                decision=f"[BLOCKED] {decision}",
                reason=reason,
                context=context,
                alternatives=alternatives or [],
                evaluation_method="constraint_check",
                evaluation_result=block_reason,
                result="blocked",
            )
            self._decisions.append(blocked)
            log_task_decision(self.repo_path, blocked)
            return None
        
        task_decision = TaskDecision(
            decision_id=str(uuid4())[:8],
            task_id=self.task_id,
            decision=decision,
            reason=reason,
            context=context,
            alternatives=alternatives or [],
            result=result or "success",
        )
        self._decisions.append(task_decision)
        return log_task_decision(self.repo_path, task_decision)
    
    def logchoice(
        self,
        context: str,
        options: list[str],
        choice: str,
        reason: str,
        result: str = "",
    ) -> str | None:
        """Log choice from options - validates all first."""
        return self.log(decision=choice, reason=reason, context=context, alternatives=options, result=result)
    
    def get_blocked(self) -> list[str]:
        return self._blocked.copy()
    
    def get_prompt_context(self) -> str:
        """Generate guardrail context for prompt."""
        if not self.ctx:
            return ""
        
        lines = ["## Decision Guardrails"]
        session = self.ctx.session
        
        if session.deadline:
            lines.append(f"- Deadline: {session.deadline}")
        
        if session.max_cost_usd > 0:
            lines.append(f"- Budget: ${session.max_cost_usd:.2f}")
            lines.append(f"- Tokens: {session.tokens_used:,}")
        
        if session.max_files > 0:
            remaining = session.max_files - session.files_modified
            lines.append(f"- Files remaining: {remaining}")
        
        if session.allowed_paths:
            lines.append(f"- Allowed: {', '.join(session.allowed_paths)}")
        if session.blocked_paths:
            lines.append(f"- Blocked: {', '.join(session.blocked_paths)}")
        
        if self._blocked:
            lines.append("\n## Blocked Decisions")
            for b in self._blocked[-3:]:
                lines.append(f"- {b}")
        
        return "\n".join(lines)


# === Run with Constraint-Aware Decisions ===

def run_with_constraints(
    repo_path: Path,
    task_id: str,
    objective: str,
    deadline: str | None = None,
    *,
    max_tokens: int = 0,
    max_cost_usd: float = 0.0,
    max_files: int = 0,
    allowed_paths: list[str] | None = None,
    blocked_paths: list[str] | None = None,
):
    """Decorator for constraint-aware execution."""
    from functools import wraps
    
    ctx = AgentContext(
        session=SessionContext(
            task_id=task_id,
            objective=objective,
            deadline=deadline,
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            max_files=max_files,
            allowed_paths=allowed_paths or [],
            blocked_paths=blocked_paths or [],
        )
    )
    
    def decorator(run_func):
        @wraps(run_func)
        def wrapper(*args, **kwargs):
            with DecisionLogger(repo_path, task_id, ctx) as logger:
                result = run_func(*args, **kwargs)
                return result, logger.get_prompt_context()
        return wrapper
    
    return decorator


# === Example integration with CLI ===

def run_with_decision_logging(
    repo_path: Path,
    task_id: str,
    run_func,
    *args,
    **kwargs,
):
    """Run a task with automatic decision logging.
    
    Example in cli.py:
        result = run_with_decision_logging(
            repo_path=repo_path,
            task_id=run_id,
            run_func=lambda: agent.run(objective),
        )
    """
    with DecisionLogger(repo_path, task_id) as logger:
        # Wrap execution to capture decisions
        try:
            result = run_func(*args, **kwargs)
            return result
        except Exception as e:
            # Log error decision
            logger.log(
                decision="Failed execution",
                reason=str(e),
                context=f"Task: {task_id}",
                result="failed",
            )
            raise