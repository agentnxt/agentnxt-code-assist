"""Decision logging for Architecture Decision Records (ADR).

This module tracks architectural decisions with full context: what was decided,
for what reason, under what context, what options were considered, and how the
decision was evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import json


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
    from agentnxt_code_assist.schemas import AssistResult
    
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