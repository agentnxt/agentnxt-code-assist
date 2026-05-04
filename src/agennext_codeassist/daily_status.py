"""Daily Status Update Module.

Generates end-of-day reports with email and Slack notifications.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


@dataclass
class DailySummary:
    """Daily status summary."""
    date: str
    generated_at: str
    completed_tasks: list[dict] = field(default_factory=list)
    planned_next: list[str] = field(default_factory=list)
    blockers: list[dict] = field(default_factory=list)
    projects_on_track: list[dict] = field(default_factory=list)
    projects_at_risk: list[dict] = field(default_factory=list)
    tasks_completed_count: int = 0
    bugs_fixed: int = 0
    improvements_made: int = 0
    notes: str | None = None


class DailyStatusReporter:
    """Generates daily status reports."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path(".agennext/daily")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.reports_file = self.log_dir / "reports.json"
        self.plans_file = self.log_dir / "plans.json"
        
        self._reports: list[dict] = []
        self._plans: list[dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load existing records."""
        if self.reports_file.exists():
            try:
                self._reports = json.loads(self.reports_file.read_text())
            except Exception:
                self._reports = []
        
        if self.plans_file.exists():
            try:
                self._plans = json.loads(self.plans_file.read_text())
            except Exception:
                self._plans = []
    
    def _save(self) -> None:
        """Persist records."""
        self.reports_file.write_text(json.dumps(self._reports, indent=2))
        self.plans_file.write_text(json.dumps(self._plans, indent=2))
    
    def add_completed_task(self, task_name: str, description: str = "") -> str:
        """Log a completed task for today."""
        entry = {
            "id": f"task-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "date": datetime.now(UTC).strftime('%Y-%m-%d'),
            "task_name": task_name,
            "description": description,
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self._reports.append(entry)
        self._save()
        return entry["id"]
    
    def add_plan(self, task_name: str, priority: str = "medium") -> str:
        """Add plan for next day."""
        entry = {
            "id": f"plan-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "date": datetime.now(UTC).strftime('%Y-%m-%d'),
            "task_name": task_name,
            "priority": priority,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._plans.append(entry)
        self._save()
        return entry["id"]
    
    def add_blocker(self, description: str, severity: str = "medium") -> str:
        """Log a blocker."""
        entry = {
            "id": f"blocker-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            "date": datetime.now(UTC).strftime('%Y-%m-%d'),
            "description": description,
            "severity": severity,
            "created_at": datetime.now(UTC).isoformat(),
            "resolved": False,
            "resolved_at": None,
        }
        self._reports.append(entry)
        self._save()
        return entry["id"]
    
    def resolve_blocker(self, blocker_id: str) -> bool:
        """Mark blocker as resolved."""
        for entry in self._reports:
            if entry.get("id") == blocker_id and entry.get("id", "").startswith("blocker-"):
                entry["resolved"] = True
                entry["resolved_at"] = datetime.now(UTC).isoformat()
                self._save()
                return True
        return False
    
    def generate_summary(self) -> DailySummary:
        """Generate today's summary."""
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        
        # Get today's entries
        completed = [
            e for e in self._reports
            if e.get("date") == today and e.get("id", "").startswith("task-")
        ]
        blockers = [
            e for e in self._reports
            if e.get("date") == today and e.get("id", "").startswith("blocker-")
        ]
        planned = [
            p for p in self._plans
            if p.get("date") == today or p.get("date") == datetime.now(UTC).strftime('%Y-%m-%d')
        ]
        
        # Get project status
        try:
            from agennext_codeassist.project_management import get_manager
            projects = get_manager().list_projects()
            
            on_track = []
            at_risk = []
            
            for proj in projects:
                tasks = proj.get("tasks", [])
                if tasks:
                    completed_count = len([t for t in tasks if t.get("status") == "completed"])
                    blocked_count = len([t for t in tasks if t.get("status") == "blocked"])
                    total = len(tasks)
                    
                    if blocked_count > 0 or completed_count / total < 0.5:
                        at_risk.append({
                            "name": proj.get("name"),
                            "progress": f"{completed_count}/{total}",
                            "blocked": blocked_count,
                        })
                    else:
                        on_track.append({
                            "name": proj.get("name"),
                            "progress": f"{completed_count}/{total}",
                        })
        except Exception:
            on_track = []
            at_risk = []
        
        # Get bugs fixed
        try:
            from agennext_codeassist.continuous_improvement import get_improver
            bugs = get_improver().get_bugs(limit=100)
            bugs_fixed = len([b for b in bugs if b.get("date", "").startswith(today) and b.get("fix_applied")])
        except Exception:
            bugs_fixed = 0
        
        # Get improvements
        try:
            from agennext_codeassist.process_excellence import get_excellence
            improvements = get_excellence().get_pending_improvements()
            improvements_made = len([i for i in improvements if i.get("implemented")])
        except Exception:
            improvements_made = 0
        
        summary = DailySummary(
            date=today,
            generated_at=datetime.now(UTC).isoformat(),
            completed_tasks=completed,
            planned_next=[p.get("task_name", "") for p in planned],
            blockers=blockers,
            projects_on_track=on_track,
            projects_at_risk=at_risk,
            tasks_completed_count=len(completed),
            bugs_fixed=bugs_fixed,
            improvements_made=improvements_made,
        )
        
        return summary
    
    def generate_email_report(self) -> tuple[str, str]:
        """Generate email report (subject, body)."""
        summary = self.generate_summary()
        
        subject = f"Daily Status: {summary.date}"
        
        body = f"""# Daily Status Report - {summary.date}

## Summary
- Tasks Completed: {summary.tasks_completed_count}
- Bugs Fixed: {summary.bugs_fixed}
- Improvements Made: {summary.improvements_made}

## Completed Tasks
"""
        if summary.completed_tasks:
            for task in summary.completed_tasks:
                body += f"- {task.get('task_name', 'Untitled')}\n"
        else:
            body += "- None\n"
        
        body += "\n## Plan for Tomorrow\n"
        if summary.planned_next:
            for plan in summary.planned_next:
                body += f"- {plan}\n"
        else:
            body += "- TBD\n"
        
        body += "\n## Blockers\n"
        unresolved = [b for b in summary.blockers if not b.get("resolved")]
        if unresolved:
            for blocker in unresolved:
                body += f"- [{blocker.get('severity')}] {blocker.get('description')}\n"
        else:
            body += "- None\n"
        
        body += "\n## Project Status\n"
        
        body += "\n### On Track\n"
        if summary.projects_on_track:
            for proj in summary.projects_on_track:
                body += f"- {proj.get('name')}: {proj.get('progress')} complete\n"
        else:
            body += "- All projects at risk or no active projects\n"
        
        body += "\n### At Risk\n"
        if summary.projects_at_risk:
            for proj in summary.projects_at_risk:
                body += f"- {proj.get('name')}: {proj.get('progress')} ({proj.get('blocked')} blocked)\n"
        else:
            body += "- No projects at risk\n"
        
        body += f"\n---\nGenerated at {summary.generated_at}"
        
        return subject, body
    
    def generate_slack_report(self) -> dict[str, str]:
        """Generate Slack webhook payload."""
        summary = self.generate_summary()
        
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📊 Daily Status - {summary.date}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Tasks Completed:*\n{summary.tasks_completed_count}"},
                    {"type": "mrkdwn", "text": f"*Bugs Fixed:*\n{summary.bugs_fixed}"},
                ]
            }
        ]
        
        # Completed tasks
        if summary.completed_tasks:
            task_text = "\n".join([f"• {t.get('task_name')}" for t in summary.completed_tasks[:5]])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Completed:*\n{task_text}"}
            })
        
        # Blockers
        unresolved = [b for b in summary.blockers if not b.get("resolved")]
        if unresolved:
            blocker_text = "\n".join([f"⚠️ {b.get('description')}" for b in unresolved])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Blockers:*\n{blocker_text}"}
            })
        
        # Project status
        if summary.projects_at_risk:
            risk_text = "\n".join([f"🔴 {p.get('name')}: {p.get('progress')}" for p in summary.projects_at_risk])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*At Risk:*\n{risk_text}"}
            })
        
        if summary.projects_on_track:
            track_text = "\n".join([f"🟢 {p.get('name')}: {p.get('progress')}" for p in summary.projects_on_track])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*On Track:*\n{track_text}"}
            })
        
        return {"blocks": blocks}
    
    def send_email(self) -> dict[str, str]:
        """Send email report via SMTP."""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_url = os.environ.get("AGENNEXT_CODE_ASSIST_SMTP_URL", "")
        from_email = os.environ.get("AGENNEXT_CODE_ASSIST_SMTP_FROM_EMAIL", "daily@localhost")
        to_email = os.environ.get("AGENNEXT_CODE_ASSIST_SMTP_TO_EMAIL", "")
        
        if not smtp_url or not to_email:
            return {"status": "not_configured", "message": "SMTP not configured"}
        
        subject, body = self.generate_email_report()
        
        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        
        try:
            server = smtplib.SMTP(smtp_url)
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()
            return {"status": "sent", "message": "Email sent"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def send_slack(self) -> dict[str, str]:
        """Send Slack webhook."""
        import requests
        
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        
        if not webhook_url:
            return {"status": "not_configured", "message": "Slack not configured"}
        
        payload = self.generate_slack_report()
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                return {"status": "sent", "message": "Slack sent"}
            return {"status": "error", "message": f"Status {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def send_all(self) -> dict[str, Any]:
        """Send all configured notifications."""
        results = {}
        
        email_result = self.send_email()
        results["email"] = email_result
        
        slack_result = self.send_slack()
        results["slack"] = slack_result
        
        return results
    
    def get_today_entries(self) -> dict[str, list]:
        """Get today's entries."""
        today = datetime.now(UTC).strftime('%Y-%m-%d')
        
        return {
            "completed": [
                e for e in self._reports
                if e.get("date") == today and e.get("id", "").startswith("task-")
            ],
            "blockers": [
                e for e in self._reports
                if e.get("date") == today and e.get("id", "").startswith("blocker-")
            ],
            "plans": [
                p for p in self._plans
                if p.get("date") == today
            ]
        }


# Global instance
_reporter: DailyStatusReporter | None = None


def get_reporter() -> DailyStatusReporter:
    """Get global reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = DailyStatusReporter()
    return _reporter