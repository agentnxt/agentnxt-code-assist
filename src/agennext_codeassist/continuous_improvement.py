"""Continuous Improvement System.

Logs bugs, analyzes root causes, and enhances skills/tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any


class BugSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BugCategory(Enum):
    LOGIC = "logic"
    VALIDATION = "validation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


@dataclass
class BugRecord:
    """Record of a bug found during execution."""
    bug_id: str
    timestamp: str
    severity: str
    category: str
    description: str
    exception_type: str | None
    exception_message: str | None
    stack_trace: str | None
    context: dict[str, Any]
    root_cause: str
    prevention: str
    file_path: str | None
    line_number: int | None
    fix_applied: bool = False
    fix_description: str | None = None
    skills_enhanced: list[str] = field(default_factory=list)
    tools_enhanced: list[str] = field(default_factory=list)


@dataclass
class ImprovementRecommendation:
    """Recommendation for improving skills or tools."""
    recommendation_id: str
    timestamp: str
    bug_id: str
    recommendation_type: str  # "skill_enhancement", "tool_enhancement", "validation", "documentation"
    description: str
    priority: str  # "high", "medium", "low"
    implemented: bool = False
    notes: str | None = None


class ContinuousImprover:
    """Manages continuous improvement logging and skill enhancement."""
    
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or Path(".agennext/improvements")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.bugs_file = self.log_dir / "bugs.json"
        self.recommendations_file = self.log_dir / "recommendations.json"
        
        self._bugs: list[dict] = []
        self._recommendations: list[dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load existing bug logs and recommendations."""
        if self.bugs_file.exists():
            try:
                self._bugs = json.loads(self.bugs_file.read_text())
            except Exception:
                self._bugs = []
        
        if self.recommendations_file.exists():
            try:
                self._recommendations = json.loads(self.recommendations_file.read_text())
            except Exception:
                self._recommendations = []
    
    def _save(self) -> None:
        """Persist bug logs and recommendations."""
        self.bugs_file.write_text(json.dumps(self._bugs, indent=2))
        self.recommendations_file.write_text(json.dumps(self._recommendations, indent=2))
    
    def log_bug(
        self,
        description: str,
        exception: Exception | None = None,
        context: dict[str, Any] | None = None,
        severity: BugSeverity = BugSeverity.MEDIUM,
        category: BugCategory = BugCategory.UNKNOWN,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> str:
        """Log a bug and generate root cause analysis."""
        import traceback
        
        bug_id = f"bug-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{len(self._bugs)}"
        
        # Extract stack trace
        stack_trace = None
        if exception and exception.__traceback__:
            stack_trace = "".join(traceback.format_tb(exception.__traceback__))
        
        # Analyze root cause
        root_cause = self._analyze_root_cause(exception, description, context)
        
        # Generate prevention recommendations
        prevention = self._generate_prevention(category, exception, description)
        
        bug_record = BugRecord(
            bug_id=bug_id,
            timestamp=datetime.now(UTC).isoformat(),
            severity=severity.value,
            category=category.value,
            description=description,
            exception_type=type(exception).__name__ if exception else None,
            exception_message=str(exception) if exception else None,
            stack_trace=stack_trace,
            context=context or {},
            root_cause=root_cause,
            prevention=prevention,
            file_path=file_path,
            line_number=line_number,
        )
        
        self._bugs.append(asdict(bug_record))
        
        # Generate improvement recommendations if needed
        self._generate_recommendations(bug_record)
        
        self._save()
        
        return bug_id
    
    def _analyze_root_cause(
        self,
        exception: Exception | None,
        description: str,
        context: dict[str, Any] | None,
    ) -> str:
        """Analyze and document root cause."""
        if exception is None:
            return f"Logic issue: {description}"
        
        exc_type = type(exception).__name__
        
        # Common patterns
        causes = {
            "AttributeError": "Accessing undefined attribute or method",
            "TypeError": "Invalid type operation or argument",
            "ValueError": "Invalid value passed to function",
            "KeyError": "Missing dictionary key",
            "FileNotFoundError": "File path does not exist or inaccessible",
            "PermissionError": "Insufficient permissions",
            "TimeoutError": "Operation took too long",
            "ConnectionError": "Network or connection failure",
            "JSONDecodeError": "Invalid JSON format",
            "ValidationError": "Input validation failed",
        }
        
        base_cause = causes.get(exc_type, f"Unhandled {exc_type}")
        
        # Add context-specific analysis
        if context:
            if "file_path" in context and "not exist" in str(exception).lower():
                base_cause += " - file verification missing"
            if "api" in str(exception).lower():
                base_cause += " - API error handling insufficient"
        
        return base_cause
    
    def _generate_prevention(
        self,
        category: BugCategory,
        exception: Exception | None,
        description: str,
    ) -> str:
        """Generate prevention recommendations."""
        prevention_map = {
            BugCategory.LOGIC: "Add unit tests for logic branches",
            BugCategory.VALIDATION: "Add input validation and type checking",
            BugCategory.SECURITY: "Review security implications",
            BugCategory.PERFORMANCE: "Add caching or optimize queries",
            BugCategory.INTEGRATION: "Add error handling for API changes",
            BugCategory.CONFIGURATION: "Add environment validation",
            BugCategory.DEPENDENCY: "Pin dependency versions",
            BugCategory.UNKNOWN: "Add logging and create reproduction case",
        }
        
        base = prevention_map.get(category, "Add bug reproduction case")
        
        if exception:
            # Add specific prevention based on exception type
            exc_type = type(exception).__name__
            if exc_type == "AttributeError":
                base += ", check attribute existence before access"
            elif exc_type == "KeyError":
                base += ", use .get() or check key first"
            elif exc_type in ("FileNotFoundError", "PermissionError"):
                base += ", validate paths before operations"
        
        return base
    
    def _generate_recommendations(self, bug: BugRecord) -> None:
        """Generate skill/tool improvement recommendations."""
        rec_type = "documentation"
        
        if bug.category == BugCategory.VALIDATION.value:
            if not any("validation" in r.get("recommendation_type", "") for r in self._recommendations):
                rec_type = "validation"
        
        elif bug.category == BugCategory.SECURITY.value:
            rec_type = "security"
        
        elif bug.severity in (BugSeverity.CRITICAL.value, BugSeverity.HIGH.value):
            rec_type = "skill_enhancement"
        
        rec = ImprovementRecommendation(
            recommendation_id=f"rec-{bug.bug_id}",
            timestamp=datetime.now(UTC).isoformat(),
            bug_id=bug.bug_id,
            recommendation_type=rec_type,
            description=f"Consider enhancing {rec_type.replace('_', ' ')} based on bug: {bug.description}",
            priority="medium" if bug.severity == BugSeverity.LOW.value else "high",
        )
        
        self._recommendations.append(asdict(rec))
    
    def get_bugs(self, limit: int = 50) -> list[dict]:
        """Get recent bug records."""
        return self._bugs[-limit:]
    
    def get_unfixed_bugs(self) -> list[dict]:
        """Get bugs that haven't been fixed."""
        return [b for b in self._bugs if not b.get("fix_applied", False)]
    
    def get_recommendations(self) -> list[dict]:
        """Get pending recommendations."""
        return [r for r in self._recommendations if not r.get("implemented", False)]
    
    def apply_fix(
        self,
        bug_id: str,
        fix_description: str,
        skills_enhanced: list[str] | None = None,
        tools_enhanced: list[str] | None = None,
    ) -> bool:
        """Mark bug as fixed and record the fix."""
        for bug in self._bugs:
            if bug.get("bug_id") == bug_id:
                bug["fix_applied"] = True
                bug["fix_description"] = fix_description
                bug["skills_enhanced"] = skills_enhanced or []
                bug["tools_enhanced"] = tools_enhanced or []
                self._save()
                return True
        return False
    
    def implement_recommendation(
        self,
        recommendation_id: str,
        notes: str | None = None,
    ) -> bool:
        """Mark recommendation as implemented."""
        for rec in self._recommendations:
            if rec.get("recommendation_id") == recommendation_id:
                rec["implemented"] = True
                rec["notes"] = notes
                self._save()
                return True
        return False
    
    def generate_report(self) -> str:
        """Generate improvement report."""
        total_bugs = len(self._bugs)
        fixed_bugs = len([b for b in self._bugs if b.get("fix_applied", False)])
        
        by_severity = {}
        by_category = {}
        
        for bug in self._bugs:
            sev = bug.get("severity", "unknown")
            cat = bug.get("category", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_category[cat] = by_category.get(cat, 0) + 1
        
        report = f"""# CodeAssist Continuous Improvement Report

## Summary
- Total Bugs: {total_bugs}
- Fixed: {fixed_bugs}
- Success Rate: {(fixed_bugs/total_bugs*100):.1f}% if total_bugs > 0 else 0%

## By Severity
"""
        for sev, count in sorted(by_severity.items()):
            report += f"- {sev}: {count}\n"
        
        report += "\n## By Category\n"
        for cat, count in sorted(by_category.items()):
            report += f"- {cat}: {count}\n"
        
        pending_recs = self.get_recommendations()
        report += f"\n## Pending Recommendations\n"
        report += f"- Total: {len(pending_recs)}\n"
        
        return report


# Global instance
_improver: ContinuousImprover | None = None


def get_improver() -> ContinuousImprover:
    """Get global improver instance."""
    global _improver
    if _improver is None:
        _improver = ContinuousImprover()
    return _improver


def log_bug(*args, **kwargs) -> str:
    """Convenience function to log a bug."""
    return get_improver().log_bug(*args, **kwargs)