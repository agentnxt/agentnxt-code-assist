"""Jira Integration Module.

Syncs projects, tasks, and issues with Jira.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any


class JiraIssueType(Enum):
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"
    EPIC = "Epic"
    SUBTASK = "Sub-task"


class JiraPriority(Enum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class JiraStatus(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"


@dataclass
class JiraConfig:
    """Jira configuration."""
    url: str = os.environ.get("JIRA_URL", "")
    email: str = os.environ.get("JIRA_EMAIL", "")
    api_token: str = os.environ.get("JIRA_API_TOKEN", "")
    project_key: str = os.environ.get("JIRA_PROJECT_KEY", "")
    webhook_url: str = os.environ.get("SLACK_WEBHOOK_URL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.email and self.api_token and self.project_key)


@dataclass
class JiraIssue:
    """Jira issue mapping."""
    jira_key: str
    summary: str
    description: str
    issue_type: str
    status: str
    priority: str
    created: str
    updated: str
    completed: str | None
    assignee: str | None
    labels: list[str] = field(default_factory=list)
    parent_key: str | None = None
    local_task_id: str | None = None


class JiraIntegration:
    """Integration with Jira for project management."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path(".agennext/jira")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.mappings_file = self.log_dir / "mappings.json"
        
        self._mappings: list[dict] = []
        self.config = JiraConfig()
        self._load()
    
    def _load(self) -> None:
        """Load existing mappings."""
        if self.mappings_file.exists():
            try:
                self._mappings = json.loads(self.mappings_file.read_text())
            except Exception:
                self._mappings = []
    
    def _save(self) -> None:
        """Persist mappings."""
        self.mappings_file.write_text(json.dumps(self._mappings, indent=2))
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict[str, Any]:
        """Make API request to Jira."""
        import requests
        
        if not self.config.is_configured:
            return {"error": "Jira not configured"}
        
        url = f"{self.config.url}/rest/api/3/{endpoint}"
        auth = (self.config.email, self.config.api_token)
        headers = {"Content-Type": "application/json"}
        
        try:
            if method == "GET":
                response = requests.get(url, auth=auth, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, auth=auth, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, auth=auth, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, auth=auth, headers=headers, timeout=30)
            else:
                return {"error": f"Unknown method: {method}"}
            
            if response.status_code in (200, 201):
                return response.json() if response.text else {"success": True}
            return {"error": f"Status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    def create_issue(
        self,
        summary: str,
        description: str = "",
        issue_type: JiraIssueType = JiraIssueType.TASK,
        priority: JiraPriority = JiraPriority.MEDIUM,
        parent_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Jira issue."""
        data = {
            "fields": {
                "project": {"key": self.config.project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description or summary}]
                        }
                    ]
                },
                "issuetype": {"name": issue_type.value},
                "priority": {"name": priority.value},
            }
        }
        
        if parent_key:
            data["fields"]["parent"] = {"key": parent_key}
        
        result = self._make_request("POST", "issue", data)
        
        if "key" in result:
            return {
                "jira_key": result["key"],
                "local_id": result.get("id"),
                "status": "created"
            }
        return {"error": result.get("error", "Failed to create issue")}
    
    def update_issue(
        self,
        jira_key: str,
        summary: str | None = None,
        description: str | None = None,
        status: JiraStatus | None = None,
        priority: JiraPriority | None = None,
    ) -> dict[str, Any]:
        """Update a Jira issue."""
        fields = {}
        
        if summary:
            fields["summary"] = summary
        if description:
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            }
        if priority:
            fields["priority"] = {"name": priority.value}
        
        if not fields:
            return {"error": "No fields to update"}
        
        data = {"fields": fields}
        
        # Update issue fields
        result = self._make_request("PUT", f"issue/{jira_key}", data)
        
        # Update status if provided
        if status and result.get("success") or not result.get("error"):
            transitions = self._get_transitions(jira_key)
            for t in transitions:
                if t.get("name") == status.value:
                    self._make_request("POST", f"issue/{jira_key}/transitions", {
                        "transition": {"id": t.get("id")}
                    })
                    break
        
        return {"status": "updated", "jira_key": jira_key}
    
    def _get_transitions(self, jira_key: str) -> list[dict]:
        """Get available transitions for issue."""
        result = self._make_request("GET", f"issue/{jira_key}/transitions")
        return result.get("transitions", []) if isinstance(result, dict) else []
    
    def transition_issue(
        self,
        jira_key: str,
        status: JiraStatus,
    ) -> dict[str, Any]:
        """Transition Jira issue to new status."""
        transitions = self._get_transitions(jira_key)
        
        for t in transitions:
            if t.get("name") == status.value:
                result = self._make_request("POST", f"issue/{jira_key}/transitions", {
                    "transition": {"id": t.get("id")}
                })
                return {"status": "transitioned", "jira_key": jira_key}
        
        return {"error": f"No transition to {status.value}"}
    
    def link_issue(
        self,
        from_key: str,
        to_key: str,
        link_type: str = "Blocks",
    ) -> dict[str, Any]:
        """Link two Jira issues."""
        data = {
            "type": {"name": link_type},
            "inwardIssue": {"key": from_key},
            "outwardIssue": {"key": to_key},
        }
        
        result = self._make_request("POST", "issueLink", data)
        
        if "success" in result or not result.get("error"):
            return {"status": "linked"}
        return {"error": result.get("error", "Failed to link")}
    
    def get_issue(self, jira_key: str) -> dict | None:
        """Get Jira issue details."""
        result = self._make_request("GET", f"issue/{jira_key}")
        
        if "error" in result:
            return None
        
        fields = result.get("fields", {})
        
        return {
            "jira_key": result.get("key"),
            "summary": fields.get("summary"),
            "description": fields.get("description", {}).get("content", [{}])[0].get("content", [{}])[0].get("text", ""),
            "issue_type": fields.get("issuetype", {}).get("name"),
            "status": fields.get("status", {}).get("name"),
            "priority": fields.get("priority", {}).get("name"),
            "created": fields.get("created"),
            "updated": fields.get("updated"),
            "assignee": fields.get("assignee", {}).get("displayName"),
            "labels": fields.get("labels", []),
            "parent_key": fields.get("parent", {}).get("key"),
        }
    
    def search_issues(self, jql: str = "") -> list[dict]:
        """Search Jira issues."""
        if not jql:
            jql = f"project={self.config.project_key} ORDER BY updated DESC"
        
        result = self._make_request("GET", f"search?jql={jql}&maxResults=50")
        
        if "error" in result:
            return []
        
        issues = []
        for issue in result.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "jira_key": issue.get("key"),
                "summary": fields.get("summary"),
                "issue_type": fields.get("issuetype", {}).get("name"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "created": fields.get("created"),
                "updated": fields.get("updated"),
            })
        
        return issues
    
    def sync_from_jira(self, project_id: str) -> dict[str, Any]:
        """Sync tasks from Jira to local project."""
        from agentnxt_code_assist.project_management import get_manager
        
        issues = self.search_issues()
        results = {"created": 0, "updated": 0, "errors": []}
        
        for issue in issues:
            # Check if already mapped
            existing = any(
                m.get("jira_key") == issue.get("jira_key")
                for m in self._mappings
            )
            
            if existing:
                results["updated"] += 1
                continue
            
            # Map Jira status to local
            status_map = {
                "To Do": "pending",
                "In Progress": "in_progress",
                "In Review": "in_progress",
                "Done": "completed",
            }
            
            priority_map = {
                "Highest": "critical",
                "High": "high",
                "Medium": "medium",
                "Low": "low",
                "Lowest": "low",
            }
            
            status = status_map.get(issue.get("status", ""), "pending")
            priority = priority_map.get(issue.get("priority", ""), "medium")
            
            # Create local task
            task_id = get_manager().add_task(
                project_id,
                issue.get("summary", ""),
                f"Jira: {issue.get('jira_key')}",
                priority,
                None,
            )
            
            if task_id:
                # Update status
                from agentnxt_code_assist.project_management import TaskStatus
                get_manager().update_task(project_id, task_id, TaskStatus(status))
                
                # Save mapping
                self._mappings.append({
                    "jira_key": issue.get("jira_key"),
                    "local_task_id": task_id,
                    "project_id": project_id,
                    "synced_at": datetime.now(UTC).isoformat(),
                })
                results["created"] += 1
        
        self._save()
        return results
    
    def sync_to_jira(
        self,
        project_id: str,
        create_issues: bool = True,
    ) -> dict[str, Any]:
        """Sync local tasks to Jira."""
        project = get_manager().get_project(project_id)
        
        if not project:
            return {"error": "Project not found"}
        
        results = {"created": 0, "linked": 0, "errors": []}
        
        for task in project.get("tasks", []):
            task_id = task.get("task_id")
            
            # Check if already mapped
            existing = next(
                (m for m in self._mappings if m.get("local_task_id") == task_id),
                None
            )
            
            if existing:
                continue
            
            # Map local status to Jira
            status_map = {
                "pending": JiraStatus.TODO,
                "in_progress": JiraStatus.IN_PROGRESS,
                "completed": JiraStatus.DONE,
                "blocked": JiraStatus.TODO,
            }
            
            priority_map = {
                "critical": JiraPriority.HIGH,
                "high": JiraPriority.HIGH,
                "medium": JiraPriority.MEDIUM,
                "low": JiraPriority.LOW,
            }
            
            status = status_map.get(task.get("status", ""), JiraStatus.TODO)
            priority = priority_map.get(task.get("priority", ""), JiraPriority.MEDIUM)
            
            # Create Jira issue
            issue_result = self.create_issue(
                task.get("name", ""),
                task.get("description", ""),
                JiraIssueType.TASK,
                priority,
            )
            
            if "jira_key" in issue_result:
                # Update status
                self.transition_issue(issue_result["jira_key"], status)
                
                # Save mapping
                self._mappings.append({
                    "jira_key": issue_result["jira_key"],
                    "local_task_id": task_id,
                    "project_id": project_id,
                    "synced_at": datetime.now(UTC).isoformat(),
                })
                results["created"] += 1
        
        # Sync dependencies
        for task in project.get("tasks", []):
            for dep in task.get("blocked_by", []):
                from_key = next(
                    (m.get("jira_key") for m in self._mappings
                     if m.get("local_task_id") == dep.get("from_task_id")),
                    None
                )
                to_key = next(
                    (m.get("jira_key") for m in self._mappings
                     if m.get("local_task_id") == task.get("task_id")),
                    None
                )
                
                if from_key and to_key:
                    self.link_issue(from_key, to_key, "Blocks")
                    results["linked"] += 1
        
        self._save()
        return results
    
    def get_mappings(self) -> list[dict]:
        """Get all Jira-local mappings."""
        return self._mappings


# Global instance
_jira: JiraIntegration | None = None


def get_jira() -> JiraIntegration:
    """Get global Jira instance."""
    global _jira
    if _jira is None:
        _jira = JiraIntegration()
    return _jira