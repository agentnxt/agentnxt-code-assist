"""Self-improvement for the agent: learns from execution results.

SELF-IMPROVEMENT LOOP (continuous):
1. Before: Recommend skills/tools based on history
2. During: Monitor progress, detect stalls
3. After: Record results, analyze patterns
4. Auto-improve: Update skills/tools/constraints
5. Next: Better recommendations

This runs continuously - after every execution cycle.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

import json
import time


# === Execution Result ===

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


# === Auto-Skill Improvement ===

def auto_improve_skills(
    skill_registry,
    metrics_path: Path | None = None,
) -> list[str]:
    """Auto-improve skills based on performance metrics.
    
    Returns: list of skill names that were improved/replaced
    """
    from agennext_codeassist.skill_registry import SkillPriority
    
    engine = SelfImprovementEngine(metrics_path)
    improvements = []
    
    # Find underperforming skills
    for name, perf in engine.skill_performance.items():
        if perf.times_used >= 5 and perf.success_rate < 0.4:
            skill = skill_registry.get(name)
            if skill:
                # Lower priority for underperformers
                old_priority = skill.priority
                skill.priority = SkillPriority.OPTIONAL
                improvements.append(
                    f"Demoted {name} from {old_priority.name} to OPTIONAL "
                    f"(only {perf.success_rate:.0%} success)"
                )
        
        elif perf.times_used >= 5 and perf.success_rate > 0.85:
            skill = skill_registry.get(name)
            if skill and skill.priority == SkillPriority.RECOMMENDED:
                # Boost highly successful skills
                old_priority = skill.priority
                skill.priority = SkillPriority.REQUIRED
                improvements.append(
                    f"Promoted {name} to REQUIRED "
                    f"({perf.success_rate:.0%} success)"
                )
    
    return improvements


# === Auto-Tool Improvement ===

def auto_improve_tools(
    tool_registry,
    metrics_path: Path | None = None,
) -> list[str]:
    """Auto-improve tools based on performance metrics.
    
    Returns: list of tool names that were modified
    """
    engine = SelfImprovementEngine(metrics_path)
    improvements = []
    
    # Mark slow tools as lower priority
    for name, perf in engine.tool_performance.items():
        if perf.times_used >= 3 and perf.avg_duration > 120:
            # Add timeout hint
            tool = tool_registry.get_tool(name)
            if tool and tool.estimated_time_ms > 1000:
                # Reduce estimated time for retry planning
                tool.estimated_time_ms = int(perf.avg_duration * 1000)
                improvements.append(f"Updated {name} timeout to {perf.avg_duration:.0f}s")
    
    # Mark failed tools
    for name, perf in engine.tool_performance.items():
        if perf.times_used >= 3 and perf.success_rate < 0.3:
            tool = tool_registry.get_tool(name)
            if tool:
                tool.success_rate = perf.success_rate
                improvements.append(
                    f"Updated {name} success_rate to {perf.success_rate:.0%}"
                )
    
    return improvements


# === Adaptive Constraint Tuning ===

def suggest_better_constraints(
    metrics_path: Path | None = None,
) -> dict[str, Any]:
    """Suggest better constraint values based on past data."""
    engine = SelfImprovementEngine(metrics_path)
    
    suggestions = {}
    
    # Analyze cost effectiveness
    for skill_name, perf in engine.skill_performance.items():
        if perf.times_used >= 3:
            avg_cost = perf.avg_cost
            suggestions[skill_name] = {
                "optimal_budget": avg_cost * 1.5,  # 50% buffer
                "recommended_tokens": perf.total_tokens // max(1, perf.times_used) * 2,
                "timeout_seconds": perf.avg_duration * 1.5,
            }
    
    return suggestions


# === Full Auto-Improve ===

def auto_improve_all(
    skills_registry=None,
    tools_registry=None,
    metrics_path: Path | None = None,
) -> str:
    """Run full self-improvement: skills + tools + constraints.
    
    Returns: improvement report
    """
    lines = ["## Auto-Improvement Report"]
    lines.append("Running self-improvement checks...")
    
    # Improve skills
    if skills_registry:
        skill_improvements = auto_improve_skills(skills_registry, metrics_path)
        if skill_improvements:
            lines.append("\n### Skill Improvements")
            lines.extend(skill_improvements)
        else:
            lines.append("\n### Skills: No improvements needed")
    
    # Improve tools
    if tools_registry:
        tool_improvements = auto_improve_tools(tools_registry, metrics_path)
        if tool_improvements:
            lines.append("\n### Tool Improvements")
            lines.extend(tool_improvements)
        else:
            lines.append("\n### Tools: No improvements needed")
    
    # Suggest constraint tuning
    constraints = suggest_better_constraints(metrics_path)
    if constraints:
        lines.append("\n### Suggested Constraints")
        for skill, cfg in constraints.items():
            lines.append(
                f"- {skill}: budget=${cfg['optimal_budget']:.4f}, "
                f"timeout={cfg['timeout_seconds']:.0f}s"
            )
    
    return "\n".join(lines)

def record_execution_and_learn(
    result: ExecutionResult,
    storage_path: Path | None = None,
):
    """Record result and trigger learning."""
    engine = SelfImprovementEngine(storage_path)
    engine.record_result(result)
    
    # Also trigger notifications if significant
    if not result.success and result.errors:
        from agennext_codeassist.notifications import notify
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


# === Continuous Self-Improvement Loop ===

class SelfImprovementLoop:
    """Continuous self-improvement that runs in the background.
    
    THE LOOP:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                                                     │
    │  ┌─────────┐   Execute   ┌─────────┐   After    │
    │  │ Before  │──>Task     │──>During  │──>Record  │
    │  │(recommend)          │(monitor)  │(result)  │
    │  └────┬────┘           └────┬─────┘   └────┬────┘
    │       │                    │           │
    │       │                    ▼           ▼
    │       │            ┌───────────────┐
    │       │            │  Detect      │
    │       │            │  Stalls/     │
    │       │            │  Issues     │
    │       │            └──────┬──────┘
    │       │                   │
    │       ◄──────────────────┘
    │       │
    │       ▼
    │  ┌─────────┐
    │  │ Auto    │──>Improve──>Better──>Back to start
    │  │ Improve │
    │  └─────────┘
    │                                                     │
    └───────────────────────────────────────────────────────
    """
    
    def __init__(
        self,
        storage_path: Path | None = None,
        loop_interval_seconds: int = 300,  # 5 min between loops
    ):
        self.storage_path = storage_path or Path(".agennext/self_improvement")
        self.engine = SelfImprovementEngine(self.storage_path)
        
        # Loop control
        self.loop_interval = loop_interval_seconds
        self._running = False
        self._thread: Thread | None = None
        
        # Current session tracking
        self.current_run_id: str | None = None
        self.run_start_time: datetime | None = None
        self.progress_milestones: list[tuple[int, str]] = []  # (seconds, milestone)
        self.last_progress: datetime | None = None
    
    def start_loop(self):
        """Start the continuous improvement loop."""
        if self._running:
            return
        
        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop_loop(self):
        """Stop the continuous improvement loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def _run_loop(self):
        """Background loop that periodically improves."""
        while self._running:
            try:
                # Run auto-improvement
                self._periodic_improve()
                
                # Sleep until next iteration
                for _ in range(self.loop_interval):
                    if not self._running:
                        break
                    time.sleep(1)
            
            except Exception as e:
                print(f"Improvement loop error: {e}")
                time.sleep(60)  # Wait before retry
    
    def _periodic_improve(self):
        """Run periodic improvements."""
        # Check if there are enough results to learn from
        if len(self.engine.skill_performance) < 3:
            return  # Not enough data yet
        
        # Run auto-improvement
        try:
            from agennext_codeassist.skill_registry import get_skills_registry
            from agennext_codeassist.tool_registry import get_registry
            
            auto_improve_all(
                skills_registry=get_skills_registry(),
                tools_registry=get_registry(),
                metrics_path=self.storage_path,
            )
        except ImportError:
            pass
    
    # === Before: Get Recommendations ===
    
    def get_recommendations(
        self,
        objective: str,
    ) -> dict[str, Any]:
        """Get optimized recommendations before execution."""
        # Get skill recommendations
        skills = self.engine.get_recommended_skills(objective)
        
        # Get tool recommendations  
        tools = self.engine.get_recommended_tools(objective)
        
        # Get constraint suggestions
        constraints = suggest_better_constraints(self.engine.storage_path)
        
        return {
            "recommended_skills": skills,
            "recommended_tools": tools,
            "suggested_constraints": constraints,
            "confidence": "high" if len(self.engine.skill_performance) > 5 else "low",
        }
    
    # === During: Monitor Progress ===
    
    def start_monitoring(
        self,
        run_id: str,
        objective: str,
        expected_duration_seconds: int = 300,
    ):
        """Start monitoring a run."""
        self.current_run_id = run_id
        self.run_start_time = datetime.now(UTC)
        self.progress_milestones = [
            (expected_duration_seconds // 4, "25%"),
            (expected_duration_seconds // 2, "50%"),
            (expected_duration_seconds * 3 // 4, "75%"),
            (expected_duration_seconds, "complete"),
        ]
    
    def check_progress(self) -> tuple[bool, str]:
        """Check if execution is progressing well.
        
        Returns: (is_stalled, message)
        """
        if not self.run_start_time or not self.current_run_id:
            return False, ""
        
        # Calculate elapsed
        elapsed = (datetime.now(UTC) - self.run_start_time).total_seconds()
        
        # Check for stall (no progress in 60s)
        if self.last_progress:
            since_last = (datetime.now(UTC) - self.last_progress).total_seconds()
            if since_last > 60:
                return True, "No progress in 60 seconds - might be stalled"
        
        # Check milestone
        for threshold, milestone in self.progress_milestones:
            if elapsed > threshold and milestone != "complete":
                # Still going after this long
                if elapsed > threshold * 1.5:
                    return True, f"Taking longer than expected ({milestone})"
        
        return False, ""
    
    def record_progress(self):
        """Record progress checkpoint."""
        self.last_progress = datetime.now(UTC)
    
    # === After: Record Results ===
    
    def complete(
        self,
        result: ExecutionResult,
        run_id: str | None = None,
    ):
        """Record execution result."""
        if run_id:
            self.current_run_id = None
            self.run_start_time = None
        
        # Record in engine
        self.engine.record_result(result)
        
        # Check if we should run immediate improvement
        if result.success and len(self.engine.skill_performance) >= 10:
            # Good time to learn
            try:
                self._periodic_improve()
            except Exception:
                pass
    
    # === Continuous: Status ===
    
    def get_loop_status(self) -> dict[str, Any]:
        """Get current loop status."""
        return {
            "running": self._running,
            "data_points": len(self.engine.skill_performance),
            "current_run": self.current_run_id,
            "uptime_seconds": (
                (datetime.now(UTC) - self.run_start_time).total_seconds()
                if self.run_start_time else 0
            ),
        }


# === Singleton Loop ===

_loop: SelfImprovementLoop | None = None


def start_self_improvement_loop(
    loop_interval: int = 300,
) -> SelfImprovementLoop:
    """Start the continuous self-improvement loop."""
    global _loop
    
    _loop = SelfImprovementLoop(
        loop_interval_seconds=loop_interval,
    )
    _loop.start_loop()
    
    return _loop


def stop_self_improvement_loop():
    """Stop the continuous self-improvement loop."""
    global _loop
    
    if _loop:
        _loop.stop_loop()
        _loop = None


def get_self_improvement_loop() -> SelfImprovementLoop | None:
    """Get the current loop."""
    return _loop

_engine: SelfImprovementEngine | None = None


def get_self_improvement_engine() -> SelfImprovementEngine:
    global _engine
    if _engine is None:
        _engine = SelfImprovementEngine()
    return _engine