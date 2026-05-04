"""Process Excellence Module.

Tracks task completion time and suggests improvements for repeat tasks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImprovementType(Enum):
    CACHING = "caching"
    PARALLELIZATION = "parallelization"
    SKIP_LOGIC = "skip_logic"
    BATCHING = "batching"
    PRECOMPUTATION = "precomputation"
    OPTIMIZATION = "optimization"
    CODEGEN = "codegen"
    MEMOIZATION = "memoization"


@dataclass
class TaskRecord:
    """Record of a task execution."""
    task_id: str
    task_name: str
    timestamp: str
    status: str
    duration_ms: int
    repeat_count: int = 1
    previous_duration_ms: int | None = None
    improvement_potential: int = 0  # ms that could be saved
    steps: list[dict] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ProcessImprovement:
    """Improvement suggestion for a process."""
    improvement_id: str
    timestamp: str
    task_id: str
    improvement_type: str
    description: str
    estimated_time_saved_ms: int
    implementation_effort: str  # "low", "medium", "high"
    approved: bool = False
    implemented: bool = False
    notes: str | None = None


class ProcessExcellence:
    """Manages process excellence tracking."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path(".agennext/processes")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.log_dir / "tasks.json"
        self.improvements_file = self.log_dir / "improvements.json"
        
        self._tasks: list[dict] = []
        self._improvements: list[dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load existing records."""
        if self.tasks_file.exists():
            try:
                self._tasks = json.loads(self.tasks_file.read_text())
            except Exception:
                self._tasks = []
        
        if self.improvements_file.exists():
            try:
                self._improvements = json.loads(self.improvements_file.read_text())
            except Exception:
                self._improvements = []
    
    def _save(self) -> None:
        """Persist records."""
        self.tasks_file.write_text(json.dumps(self._tasks, indent=2))
        self.improvements_file.write_text(json.dumps(self._improvements, indent=2))
    
    def start_task(self, task_name: str, context: dict[str, Any] | None = None) -> str:
        """Start tracking a task."""
        task_id = f"task-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{len(self._tasks)}"
        
        task = TaskRecord(
            task_id=task_id,
            task_name=task_name,
            timestamp=datetime.now(UTC).isoformat(),
            status=TaskStatus.RUNNING.value,
            duration_ms=0,
            context=context or {},
        )
        
        self._tasks.append(asdict(task))
        self._save()
        
        return task_id
    
    def complete_task(
        self,
        task_id: str,
        status: TaskStatus = TaskStatus.COMPLETED,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> int:
        """Complete a task and analyze for improvements."""
        # Find the task
        task = None
        for t in self._tasks:
            if t.get("task_id") == task_id:
                task = t
                break
        
        if not task:
            return 0
        
        # Calculate duration if not provided
        if duration_ms is None:
            start = datetime.fromisoformat(task["timestamp"])
            duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        
        task["status"] = status.value
        task["duration_ms"] = duration_ms
        
        if error:
            task["error"] = error
        
        # Get previous run for this task
        same_name_tasks = [
            t for t in self._tasks
            if t.get("task_name") == task["task_name"]
            and t.get("task_id") != task_id
            and t.get("status") == TaskStatus.COMPLETED.value
        ]
        
        if same_name_tasks:
            # Find most recent completed task with same name
            same_name_tasks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            prev = same_name_tasks[0]
            
            task["previous_duration_ms"] = prev.get("duration_ms", 0)
            task["repeat_count"] = len(same_name_tasks) + 1
            
            # Analyze if time increased or stayed same
            prev_duration = prev.get("duration_ms", 0)
            
            if prev_duration > 0 and duration_ms >= prev_duration:
                # Time increased or same - generate improvements
                improvement_potential = self._analyze_improvement(
                    task["task_name"],
                    duration_ms,
                    prev_duration,
                    task.get("context", {}),
                )
                task["improvement_potential"] = improvement_potential
                
                if improvement_potential > 0:
                    self._generate_improvements(
                        task_id,
                        task["task_name"],
                        duration_ms,
                        prev_duration,
                        task.get("context", {}),
                        improvement_potential,
                    )
        
        self._save()
        
        return duration_ms
    
    def _analyze_improvement(
        self,
        task_name: str,
        current_duration: int,
        previous_duration: int,
        context: dict[str, Any],
    ) -> int:
        """Calculate potential improvement."""
        # Simple algorithm: if current >= previous, suggest savings
        # 20% improvement potential if same or slightly longer
        # 40% if significantly longer
        
        if current_duration <= previous_duration:
            return 0  # Already improved
        
        increase_ratio = current_duration / max(previous_duration, 1)
        
        if increase_ratio <= 1.1:
            return int(current_duration * 0.2)  # 20%
        elif increase_ratio <= 1.5:
            return int(current_duration * 0.3)  # 30%
        else:
            return int(current_duration * 0.4)  # 40%
    
    def _generate_improvements(
        self,
        task_id: str,
        task_name: str,
        current_duration: int,
        previous_duration: int,
        context: dict[str, Any],
        potential: int,
    ) -> None:
        """Generate improvement suggestions."""
        improvements = []
        
        # Generate type-specific improvements
        improvements.append(ProcessImprovement(
            improvement_id=f"imp-{task_id}-1",
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_id,
            improvement_type=ImprovementType.CACHING.value,
            description=f"Add caching layer for {task_name} to avoid redundant computations",
            estimated_time_saved_ms=int(potential * 0.5),
            implementation_effort="medium",
        ))
        
        improvements.append(ProcessImprovement(
            improvement_id=f"imp-{task_id}-2",
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_id,
            improvement_type=ImprovementType.PARALLELIZATION.value,
            description=f"Run independent steps of {task_name} in parallel",
            estimated_time_saved_ms=int(potential * 0.4),
            implementation_effort="high",
        ))
        
        # Add skip logic if context has conditional parts
        if any(k for k in context.keys() if "filter" in k.lower() or "condition" in k.lower()):
            improvements.append(ProcessImprovement(
                improvement_id=f"imp-{task_id}-3",
                timestamp=datetime.now(UTC).isoformat(),
                task_id=task_id,
                improvement_type=ImprovementType.SKIP_LOGIC.value,
                description=f"Add skip logic for unchanged inputs in {task_name}",
                estimated_time_saved_ms=int(potential * 0.6),
                implementation_effort="low",
            ))
        
        for imp in improvements:
            self._improvements.append(asdict(imp))
    
    def get_task(self, task_id: str) -> dict | None:
        """Get task by ID."""
        for task in self._tasks:
            if task.get("task_id") == task_id:
                return task
        return None
    
    def get_tasks(self, task_name: str | None = None, limit: int = 50) -> list[dict]:
        """Get recent tasks."""
        tasks = self._tasks
        
        if task_name:
            tasks = [t for t in tasks if t.get("task_name") == task_name]
        
        return tasks[-limit:]
    
    def get_pending_improvements(self) -> list[dict]:
        """Get unimplemented improvements."""
        return [imp for imp in self._improvements if not imp.get("implemented", False)]
    
    def approve_improvement(self, improvement_id: str) -> bool:
        """Mark improvement as approved."""
        for imp in self._improvements:
            if imp.get("improvement_id") == improvement_id:
                imp["approved"] = True
                self._save()
                return True
        return False
    
    def implement_improvement(
        self,
        improvement_id: str,
        notes: str | None = None,
    ) -> bool:
        """Mark improvement as implemented."""
        for imp in self._improvements:
            if imp.get("improvement_id") == improvement_id:
                imp["implemented"] = True
                imp["notes"] = notes
                self._save()
                return True
        return False
    
    def get_statistics(self, task_name: str | None = None) -> dict:
        """Get process statistics."""
        tasks = self._tasks
        
        if task_name:
            tasks = [t for t in tasks if t.get("task_name") == task_name]
        
        completed = [t for t in tasks if t.get("status") == TaskStatus.COMPLETED.value]
        
        if not completed:
            return {"total": 0, "avg_duration_ms": 0, "improved": 0, "degraded": 0}
        
        durations = [t.get("duration_ms", 0) for t in completed]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        improved = len([t for t in completed if t.get("previous_duration_ms") and 
                     t.get("duration_ms", 0) < t.get("previous_duration_ms", 0)])
        
        degraded = len([t for t in completed if t.get("previous_duration_ms") and 
                       t.get("duration_ms", 0) >= t.get("previous_duration_ms", 0)])
        
        return {
            "total": len(completed),
            "avg_duration_ms": int(avg_duration),
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "improved": improved,
            "degraded": degraded,
            "repeat_tasks": sum(t.get("repeat_count", 1) for t in completed),
        }
    
    def generate_report(self) -> str:
        """Generate process excellence report."""
        stats = self.get_statistics()
        
        # Group by task name
        by_task = {}
        for task in self._tasks:
            name = task.get("task_name", "unknown")
            if name not in by_task:
                by_task[name] = []
            by_task[name].append(task)
        
        report = f"""# Process Excellence Report

## Overall Statistics
- Total Tasks: {stats['total']}
- Avg Duration: {stats['avg_duration_ms']}ms
- Min Duration: {stats['min_duration_ms']}ms
- Max Duration: {stats['max_duration_ms']}ms
- Improved: {stats['improved']}
- Degraded: {stats['degraded']}
"""
        
        pending = self.get_pending_improvements()
        if pending:
            report += f"\n## Pending Improvements\n"
            for imp in pending:
                report += f"- [{imp.get('improvement_type')}] {imp.get('description')} "
                report += f"(~{imp.get('estimated_time_saved_ms')}ms saved)\n"
        
        report += "\n## By Task\n"
        for name, tasks in sorted(by_task.items()):
            task_stats = self.get_statistics(name)
            report += f"\n### {name}\n"
            report += f"- Runs: {task_stats['total']}, Avg: {task_stats['avg_duration_ms']}ms\n"
        
        return report


# Global instance
_excellence: ProcessExcellence | None = None


def get_excellence() -> ProcessExcellence:
    """Get global excellence instance."""
    global _excellence
    if _excellence is None:
        _excellence = ProcessExcellence()
    return _excellence


def start_task(*args, **kwargs) -> str:
    """Convenience function to start a task."""
    return get_excellence().start_task(*args, **kwargs)


def complete_task(*args, **kwargs) -> int:
    """Convenience function to complete a task."""
    return get_excellence().complete_task(*args, **kwargs)