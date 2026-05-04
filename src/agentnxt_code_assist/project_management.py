"""Project Management Module.

Tracks projects, tasks, milestones and dependencies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectStatus(Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Milestone:
    """Project milestone."""
    milestone_id: str
    name: str
    description: str
    due_date: str | None
    completed: bool = False
    completed_at: str | None = None


@dataclass
class Dependency:
    """Task dependency."""
    dependency_id: str
    from_task_id: str
    to_task_id: str
    dependency_type: str = "blocks"  # "blocks", "relates_to", "duplicates"


@dataclass
class Project:
    """Project record."""
    project_id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    due_date: str | None
    completed_at: str | None = None
    milestones: list[dict] = field(default_factory=list)
    tasks: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProjectManager:
    """Manages projects, tasks, milestones and dependencies."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path(".agennext/projects")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.log_dir / "projects.json"
        self.dependencies_file = self.log_dir / "dependencies.json"
        
        self._projects: list[dict] = []
        self._dependencies: list[dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load existing records."""
        if self.projects_file.exists():
            try:
                self._projects = json.loads(self.projects_file.read_text())
            except Exception:
                self._projects = []
        
        if self.dependencies_file.exists():
            try:
                self._dependencies = json.loads(self.dependencies_file.read_text())
            except Exception:
                self._dependencies = []
    
    def _save(self) -> None:
        """Persist records."""
        self.projects_file.write_text(json.dumps(self._projects, indent=2))
        self.dependencies_file.write_text(json.dumps(self._dependencies, indent=2))
    
    def create_project(
        self,
        name: str,
        description: str = "",
        due_date: str | None = None,
    ) -> str:
        """Create a new project."""
        project_id = f"proj-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{len(self._projects)}"
        
        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            status=ProjectStatus.ACTIVE.value,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            due_date=due_date,
        )
        
        self._projects.append(asdict(project))
        self._save()
        
        return project_id
    
    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        due_date: str | None = None,
    ) -> bool:
        """Update project details."""
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                if name:
                    proj["name"] = name
                if description is not None:
                    proj["description"] = description
                if status:
                    proj["status"] = status.value
                    if status == ProjectStatus.COMPLETED:
                        proj["completed_at"] = datetime.now(UTC).isoformat()
                if due_date is not None:
                    proj["due_date"] = due_date
                proj["updated_at"] = datetime.now(UTC).isoformat()
                self._save()
                return True
        return False
    
    def add_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
    ) -> str:
        """Add a task to a project."""
        task_id = f"task-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        
        task = {
            "task_id": task_id,
            "name": name,
            "description": description,
            "status": TaskStatus.PENDING.value,
            "priority": priority.value,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "due_date": due_date,
            "completed_at": None,
        }
        
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                proj["tasks"].append(task)
                proj["updated_at"] = datetime.now(UTC).isoformat()
                self._save()
                return task_id
        
        return ""
    
    def update_task(
        self,
        project_id: str,
        task_id: str,
        status: TaskStatus | None = None,
        name: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: str | None = None,
    ) -> bool:
        """Update a task."""
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                for task in proj.get("tasks", []):
                    if task.get("task_id") == task_id:
                        if name:
                            task["name"] = name
                        if description is not None:
                            task["description"] = description
                        if status:
                            task["status"] = status.value
                            if status == TaskStatus.COMPLETED:
                                task["completed_at"] = datetime.now(UTC).isoformat()
                        if priority:
                            task["priority"] = priority.value
                        if due_date is not None:
                            task["due_date"] = due_date
                        task["updated_at"] = datetime.now(UTC).isoformat()
                        proj["updated_at"] = datetime.now(UTC).isoformat()
                        self._save()
                        return True
        return False
    
    def add_milestone(
        self,
        project_id: str,
        name: str,
        description: str = "",
        due_date: str | None = None,
    ) -> str:
        """Add a milestone to a project."""
        milestone_id = f"milestone-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        
        milestone = {
            "milestone_id": milestone_id,
            "name": name,
            "description": description,
            "due_date": due_date,
            "completed": False,
            "completed_at": None,
        }
        
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                proj["milestones"].append(milestone)
                proj["updated_at"] = datetime.now(UTC).isoformat()
                self._save()
                return milestone_id
        
        return ""
    
    def complete_milestone(self, project_id: str, milestone_id: str) -> bool:
        """Complete a milestone."""
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                for milestone in proj.get("milestones", []):
                    if milestone.get("milestone_id") == milestone_id:
                        milestone["completed"] = True
                        milestone["completed_at"] = datetime.now(UTC).isoformat()
                        proj["updated_at"] = datetime.now(UTC).isoformat()
                        self._save()
                        return True
        return False
    
    def add_dependency(
        self,
        from_task_id: str,
        to_task_id: str,
        dependency_type: str = "blocks",
    ) -> str:
        """Add task dependency."""
        dependency_id = f"dep-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        
        dependency = {
            "dependency_id": dependency_id,
            "from_task_id": from_task_id,
            "to_task_id": to_task_id,
            "dependency_type": dependency_type,
        }
        
        self._dependencies.append(dependency)
        self._save()
        
        return dependency_id
    
    def get_blocked_tasks(self, project_id: str, task_id: str) -> list[dict]:
        """Get tasks blocked by given task."""
        blocked = []
        
        for dep in self._dependencies:
            if dep.get("from_task_id") == task_id and dep.get("dependency_type") == "blocks":
                for proj in self._projects:
                    if proj.get("project_id") == project_id:
                        for task in proj.get("tasks", []):
                            if task.get("task_id") == dep.get("to_task_id"):
                                task["dependency"] = dep
                                blocked.append(task)
        
        return blocked
    
    def get_project(self, project_id: str) -> dict | None:
        """Get project by ID."""
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                # Add dependency info to tasks
                for task in proj.get("tasks", []):
                    task["dependencies"] = [
                        d for d in self._dependencies
                        if d.get("from_task_id") == task.get("task_id")
                    ]
                    task["blocked_by"] = [
                        d for d in self._dependencies
                        if d.get("to_task_id") == task.get("task_id")
                    ]
                return proj
        return None
    
    def list_projects(self, status: ProjectStatus | None = None) -> list[dict]:
        """List projects."""
        projects = self._projects
        
        if status:
            projects = [p for p in projects if p.get("status") == status.value]
        
        return sorted(projects, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def get_statistics(self, project_id: str | None = None) -> dict:
        """Get project statistics."""
        projects = self._projects
        
        if project_id:
            projects = [p for p in projects if p.get("project_id") == project_id]
        
        stats = {
            "total_projects": len(projects),
            "active": 0,
            "on_hold": 0,
            "completed": 0,
            "archived": 0,
            "total_tasks": 0,
            "tasks_completed": 0,
            "tasks_blocked": 0,
            "total_milestones": 0,
            "milestones_completed": 0,
        }
        
        for proj in projects:
            status = proj.get("status")
            if status == ProjectStatus.ACTIVE.value:
                stats["active"] += 1
            elif status == ProjectStatus.ON_HOLD.value:
                stats["on_hold"] += 1
            elif status == ProjectStatus.COMPLETED.value:
                stats["completed"] += 1
            elif status == ProjectStatus.ARCHIVED.value:
                stats["archived"] += 1
            
            tasks = proj.get("tasks", [])
            stats["total_tasks"] += len(tasks)
            stats["tasks_completed"] += len([t for t in tasks if t.get("status") == TaskStatus.COMPLETED.value])
            stats["tasks_blocked"] += len([t for t in tasks if t.get("status") == TaskStatus.BLOCKED.value])
            
            milestones = proj.get("milestones", [])
            stats["total_milestones"] += len(milestones)
            stats["milestones_completed"] += len([m for m in milestones if m.get("completed")])
        
        return stats
    
    def generate_report(self) -> str:
        """Generate project management report."""
        stats = self.get_statistics()
        
        report = f"""# Project Management Report

## Summary
- Total Projects: {stats['total_projects']}
- Active: {stats['active']}, On Hold: {stats['on_hold']}, Completed: {stats['completed']}, Archived: {stats['archived']}

## Tasks
- Total: {stats['total_tasks']}
- Completed: {stats['tasks_completed']}
- Blocked: {stats['tasks_blocked']}

## Milestones
- Total: {stats['total_milestones']}
- Completed: {stats['milestones_completed']}

## Projects
"""
        
        for proj in self._projects:
            proj_tasks = proj.get("tasks", [])
            completed = len([t for t in proj_tasks if t.get("status") == TaskStatus.COMPLETED.value])
            progress = f"{completed}/{len(proj_tasks)}" if proj_tasks else "0/0"
            
            report += f"\n### {proj.get('name')} ({proj.get('status')})\n"
            report += f"- Tasks: {progress}\n"
            
            milestones = proj.get("milestones", [])
            if milestones:
                for m in milestones:
                    status = "✓" if m.get("completed") else "○"
                    report += f"  {status} {m.get('name')}\n"
        
        return report
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        self._projects = [p for p in self._projects if p.get("project_id") != project_id]
        self._dependencies = [
            d for d in self._dependencies
            if not any(
                t.get("task_id") in (d.get("from_task_id"), d.get("to_task_id"))
                for proj in self._projects
                for t in proj.get("tasks", [])
                if proj.get("project_id") == project_id
            )
        ]
        self._save()
        return True
    
    def delete_task(self, project_id: str, task_id: str) -> bool:
        """Delete a task from project."""
        for proj in self._projects:
            if proj.get("project_id") == project_id:
                proj["tasks"] = [t for t in proj.get("tasks", []) if t.get("task_id") != task_id]
                proj["updated_at"] = datetime.now(UTC).isoformat()
                self._save()
                return True
        return False


# Global instance
_manager: ProjectManager | None = None


def get_manager() -> ProjectManager:
    """Get global manager instance."""
    global _manager
    if _manager is None:
        _manager = ProjectManager()
    return _manager