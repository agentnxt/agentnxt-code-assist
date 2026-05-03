"""Self-improvement for the agent: learns from execution results.

Tracks:
- What skills/tools work best for different tasks
- Success rates of different approaches
- Constraint effectiveness  
- Performance metrics
- Auto-updates skills based on outcomes
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import json


# === Execution Metrics ===

@dataclass
class ExecutionResult:
    """Result of a task execution."""
    task_id: str
    objective: str
    
    # What was tried
    skills_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    approach: str = ""
    
    # Outcome
    success: bool = False
    files_modified: int = 0
    duration_seconds: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    
    # Errors
    errors: list[str] = field(default_factory=list)
    blocked_decisions: list[str] = field(default_factory=list)
    
    # Feedback
    user_feedback: str | None = None
    
    # When
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "objective": self.objective,
            "skills_used": self.skills_used,
            "tools_used": self.tools_used,
            "approach": self.approach,
            "success": self.success,
            "metrics": {
                "files_modified": self.files_modified,
                "duration": self.duration_seconds,
                "tokens": self.tokens_used,
                "cost_usd": self.cost_usd,
            },
            "errors": self.errors,
            "blocked_decisions": self.blocked_decisions,
            "user_feedback": self.user_feedback,
            "timestamp": self.timestamp,
        }


# === Performance Analytics ===

@dataclass
class SkillPerformance:
    """Performance metrics for a skill."""
    name: str
    
    # Usage
    times_used: int = 0
    times_succeeded: int = 0
    times_failed: int = 0
    
    # Timing
    total_duration: float = 0.0
    avg_duration: float = 0.0
    
    # Quality
    avg_files_modified: float = 0.0
    total_tokens: int = 0
    
    # Task types
    task_types: dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 0.0
        return self.times_succeeded / self.times_used
    
    @property
    def avg_cost(self) -> float:
        if self.times_used == 0:
            return 0.0
        return (self.total_tokens * 0.00001) / self.times_used
    
    def record(self, result: ExecutionResult, succeeded: bool):
        self.times_used += 1
        if succeeded:
            self.times_succeeded += 1
        else:
            self.times_failed += 1
        
        self.total_duration += result.duration_seconds
        if self.times_used > 0:
            self.avg_duration = self.total_duration / self.times_used
        
        self.total_tokens += result.tokens_used
    
    def to_prompt(self) -> str:
        return (
            f"{self.name}: {self.success_rate:.0%} success, "
            f"{self.avg_duration:.1f}s avg, ${self.avg_cost:.4f} avg"
        )


@dataclass
class ToolPerformance:
    """Performance metrics for a tool."""
    name: str
    
    times_used: int = 0
    times_succeeded: int = 0
    
    total_duration: float = 0.0
    avg_duration: float = 0.0
    
    failures: list[str] = field(default_factory=list)  # Error types
    
    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 0.0
        return self.times_succeeded / self.times_used
    
    def record(self, result: ExecutionResult, succeeded: bool):
        self.times_used += 1
        if succeeded:
            self.times_succeeded += 1
        else:
            if result.errors:
                self.failures.extend(result.errors[:3])
        
        self.total_duration += result.duration_seconds
        if self.times_used > 0:
            self.avg_duration = self.total_duration / self.times_used


# === Self-Improvement Engine ===

class SelfImprovementEngine:
    """Learns from execution results to improve future performance."""
    
    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path(".agennext/self_improvement")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.skill_performance: dict[str, SkillPerformance] = {}
        self.tool_performance: dict[str, ToolPerformance] = {}
        
        # Task patterns
        self.task_patterns: dict[str, list[str]] = defaultdict(list)  # objective -> skills that worked
        
        # Constraint feedback
        self.constraint_effectiveness: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # {constraint_type: {value: success_count}}
        
        # Load existing data
        self._load()
    
    def record_result(self, result: ExecutionResult):
        """Record execution result for learning."""
        # Record skill performance
        for skill in result.skills_used:
            if skill not in self.skill_performance:
                self.skill_performance[skill] = SkillPerformance(name=skill)
            self.skill_performance[skill].record(result, result.success)
        
        # Record tool performance
        for tool in result.tools_used:
            if tool not in self.tool_performance:
                self.tool_performance[tool] = ToolPerformance(name=tool)
            self.tool_performance[tool].record(result, result.success)
        
        # Record task pattern (what worked)
        if result.success:
            obj_key = result.objective[:30].lower()
            for skill in result.skills_used:
                if skill not in self.task_patterns[obj_key]:
                    self.task_patterns[obj_key].append(skill)
        
        # Save
        self._save()
    
    def get_recommended_skills(self, objective: str) -> list[str]:
        """Get recommended skills based on past success."""
        obj_key = objective[:30].lower()
        
        # Direct pattern match
        if obj_key in self.task_patterns:
            return self.task_patterns[obj_key]
        
        # Fuzzy match
        for pattern, skills in self.task_patterns.items():
            if any(word in objective.lower() for word in pattern.split()):
                return skills
        
        # Fallback to best performers
        best = [
            (s.name, s.success_rate) 
            for s in self.skill_performance.values()
            if s.times_used >= 3
        ]
        best.sort(key=lambda x: x[1], reverse=True)
        
        return [s[0] for s in best[:3]]
    
    def get_recommended_tools(self, objective: str) -> list[str]:
        """Get recommended tools based on past success."""
        # Find best performing tools
        best = [
            (t.name, t.success_rate)
            for t in self.tool_performance.values()
            if t.times_used >= 2
        ]
        best.sort(key=lambda x: x[1], reverse=True)
        
        return [t[0] for t in best[:3]]
    
    def get_constraint_feedback(self, constraint_type: str, value: str) -> dict[str, Any]:
        """Get feedback on constraint effectiveness."""
        stats = self.constraint_effectiveness[constraint_type][value]
        
        return {
            "times_used": sum(stats.values()),
            "success_count": stats.get("success", 0),
            "failure_count": stats.get("failed", 0),
            "success_rate": (
                stats.get("success", 0) / max(1, sum(stats.values()))
            ),
        }
    
    def record_constraint_outcome(
        self, 
        constraint_type: str, 
        value: str, 
        success: bool
    ):
        """Record how well a constraint worked."""
        key = "success" if success else "failed"
        self.constraint_effectiveness[constraint_type][value][key] += 1
    
    def get_improvement_report(self) -> str:
        """Generate improvement report."""
        lines = ["## Self-Improvement Report"]
        
        # Best skills
        lines.append("\n### Top Performing Skills")
        best_skills = [
            s.to_prompt()
            for s in sorted(
                self.skill_performance.values(),
                key=lambda s: s.success_rate,
                reverse=True,
            )[:5]
        ]
        lines.extend(best_skills or ["- No data yet"])
        
        # Best tools
        lines.append("\n### Top Performing Tools")
        best_tools = [
            f"{t.name}: {t.success_rate:.0%} success, {t.avg_duration:.1f}s avg"
            for t in sorted(
                self.tool_performance.values(),
                key=lambda t: t.success_rate,
                reverse=True,
            )[:5]
        ]
        lines.extend(best_tools or ["- No data yet"])
        
        # Task patterns
        lines.append("\n### Learned Task Patterns")
        if self.task_patterns:
            for obj, skills in list(self.task_patterns.items())[:5]:
                lines.append(f"- {obj}: {', '.join(skills)}")
        else:
            lines.append("- No patterns learned yet")
        
        # Issues to address
        issues = []
        for skill in self.skill_performance.values():
            if skill.success_rate < 0.5 and skill.times_used >= 5:
                issues.append(f"- {skill.name}: only {skill.success_rate:.0%} success rate")
        
        if issues:
            lines.append("\n### Skills Needing Improvement")
            lines.extend(issues[:5])
        
        return "\n".join(lines)
    
    def suggest_improvements(self) -> list[str]:
        """Suggest specific improvements based on data."""
        suggestions = []
        
        # Low-performing skills
        for skill in self.skill_performance.values():
            if skill.success_rate < 0.5 and skill.times_used >= 5:
                suggestions.append(
                    f"Consider improving or replacing '{skill.name}' "
                    f"(only {skill.success_rate:.0%} success)"
                )
        
        # Slow tools
        for tool in self.tool_performance.values():
            if tool.avg_duration > 60 and tool.times_used >= 3:
                suggestions.append(
                    f"'{tool.name}' is slow ({tool.avg_duration:.0f}s avg). "
                    f"Consider optimization or replacement."
                )
        
        # Missing data
        if len(self.skill_performance) < 3:
            suggestions.append(
                "Need more execution data to make solid recommendations. "
                "Keep using the agent to build performance history."
            )
        
        return suggestions
    
    def _save(self):
        """Save metrics to disk."""
        data = {
            "skill_performance": {
                name: {
                    "times_used": s.times_used,
                    "times_succeeded": s.times_succeeded,
                    "avg_duration": s.avg_duration,
                    "total_tokens": s.total_tokens,
                }
                for name, s in self.skill_performance.items()
            },
            "tool_performance": {
                name: {
                    "times_used": t.times_used,
                    "times_succeeded": t.times_succeeded,
                    "avg_duration": t.avg_duration,
                }
                for name, t in self.tool_performance.items()
            },
            "task_patterns": dict(self.task_patterns),
            "constraint_feedback": {
                k: dict(v) 
                for k, v in self.constraint_effectiveness.items()
            },
        }
        
        path = self.storage_path / "metrics.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def _load(self):
        """Load metrics from disk."""
        path = self.storage_path / "metrics.json"
        if not path.exists():
            return
        
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        
        # Load skill performance
        for name, stats in data.get("skill_performance", {}).items():
            perf = SkillPerformance(name=name)
            perf.times_used = stats.get("times_used", 0)
            perf.times_succeeded = stats.get("times_succeeded", 0)
            perf.avg_duration = stats.get("avg_duration", 0.0)
            perf.total_tokens = stats.get("total_tokens", 0)
            self.skill_performance[name] = perf
        
        # Load tool performance
        for name, stats in data.get("tool_performance", {}).items():
            perf = ToolPerformance(name=name)
            perf.times_used = stats.get("times_used", 0)
            perf.times_succeeded = stats.get("times_succeeded", 0)
            perf.avg_duration = stats.get("avg_duration", 0.0)
            self.tool_performance[name] = perf
        
        # Load patterns
        self.task_patterns = defaultdict(list, data.get("task_patterns", {}))
        
        # Load constraint feedback
        for k, v in data.get("constraint_feedback", {}).items():
            self.constraint_effectiveness[k] = defaultdict(int, v)


# === Auto-Improvement ===

def record_execution_and_learn(
    result: ExecutionResult,
    storage_path: Path | None = None,
):
    """Record result and trigger learning."""
    engine = SelfImprovementEngine(storage_path)
    engine.record_result(result)
    
    # Also trigger notifications if significant
    if not result.success and result.errors:
        from agentnxt_code_assist.notifications import notify
        notify(
            "⚠️ Execution Failed",
            f"Errors: {'; '.join(result.errors[:2])}",
            priority="high",
        )


def get_optimized_context(
    objective: str,
    storage_path: Path | None = None,
) -> str:
    """Get context optimized by self-improvement data."""
    engine = SelfImprovementEngine(storage_path)
    
    # Get recommendations
    skills = engine.get_recommended_skills(objective)
    tools = engine.get_recommended_tools(objective)
    
    # Generate context
    lines = ["## Self-Improvement Recommendations"]
    
    if skills:
        lines.append(f"\n**Recommended Skills** (based on past success):")
        for skill in skills:
            perf = engine.skill_performance.get(skill)
            if perf:
                lines.append(f"- {perf.to_prompt()}")
            else:
                lines.append(f"- {skill}")
    
    if tools:
        lines.append(f"\n**Recommended Tools**: {', '.join(tools)}")
    
    # Add suggestions
    suggestions = engine.suggest_improvements()
    if suggestions:
        lines.append("\n### Improvements Suggested")
        for s in suggestions[:3]:
            lines.append(f"- {s}")
    
    return "\n".join(lines)


# === Singleton ===

_engine: SelfImprovementEngine | None = None


def get_self_improvement_engine() -> SelfImprovementEngine:
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine()
    return _engine