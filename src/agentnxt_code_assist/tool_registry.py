"""Tools and skills registry with web search fallback.

Manages available tools and automatically falls back to web search
when local tools/skills are insufficient.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import json


# === Tool Categories ===

class ToolCategory(Enum):
    FILE = "file"
    SEARCH = "search"
    CODE = "code"
    SECURITY = "security"
    AUDIT = "audit"
    MEMORY = "memory"
    RAG = "rag"
    LLM = "llm"
    WEB = "web"
    UNKNOWN = "unknown"


@dataclass
class Tool:
    """Represents an available tool."""
    name: str
    category: ToolCategory
    description: str
    
    # Resource info
    is_local: bool = True
    requires_api: bool = False
    api_key_env: str | None = None
    
    # Capability
    can_handle: list[str] = field(default_factory=list)  # e.g., ["*.py", "*.ts"]
    keywords: list[str] = field(default_factory=list)  # e.g., ["find", "replace", "refactor"]
    
    # Performance
    estimated_time_ms: int = 1000
    success_rate: float = 0.95
    
    # Web fallback
    web_fallback_url: str | None = None
    web_search_query: str | None = None
    
    def can_handle_task(self, task: str) -> bool:
        """Check if this tool can handle the given task."""
        task_lower = task.lower()
        
        # Check keywords
        for kw in self.keywords:
            if kw.lower() in task_lower:
                return True
        
        # Check file patterns
        for pattern in self.can_handle:
            if "*" in pattern:
                import fnmatch
                if fnmatch.fnmatch(task, pattern):
                    return True
            elif pattern in task:
                return True
        
        return False
    
    def get_fallback_search(self, task: str) -> str | None:
        """Get web search query if tool is insufficient."""
        if self.is_local and self.web_search_query:
            return self.web_search_query.format(task=task)
        return None


# === Skills Registry ===

@dataclass
class Skill:
    """Represents an available skill."""
    name: str
    description: str
    keywords: list[str] = field(default_factory=list)
    
    # Source
    is_builtin: bool = True
    module_path: str | None = None
    url: str | None = None
    
    # Requirements
    requires_packages: list[str] = field(default_factory=list)
    requires_api: bool = False
    api_key_env: str | None = None
    
    # Capability
    supported_languages: list[str] = field(default_factory=list)  # e.g., ["python", "javascript"]
    file_types: list[str] = field(default_factory=list)  # e.g., [".py", ".ts"]
    
    def matches(self, query: str) -> float:
        """Return match score (0-1) for query."""
        query_lower = query.lower()
        score = 0.0
        
        for kw in self.keywords:
            if kw.lower() in query_lower:
                score += 0.3
        
        for lang in self.supported_languages:
            if lang.lower() in query_lower:
                score += 0.2
        
        for ext in self.file_types:
            if ext in query_lower:
                score += 0.2
        
        return min(1.0, score)


# === Tools Registry ===

class ToolsRegistry:
    """Registry of available tools with web search fallback."""
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._skills: dict[str, Skill] = {}
        self._web_fallback_enabled = True
        
        # Initialize default tools
        self._register_default_tools()
        self._register_default_skills()
    
    def _register_default_tools(self):
        """Register built-in tools."""
        # File tools
        self.register(Tool(
            name="file_editor",
            category=ToolCategory.FILE,
            description="View, create, edit files",
            can_handle=["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.md", "*.json", "*.yml"],
            keywords=["edit", "create", "view", "replace", "modify", "write"],
        ))
        
        self.register(Tool(
            name="terminal",
            category=ToolCategory.FILE,
            description="Execute shell commands",
            can_handle=["*"],
            keywords=["run", "execute", "command", "bash", "shell"],
        ))
        
        self.register(Tool(
            name="browser",
            category=ToolCategory.WEB,
            description="Navigate/interact with web pages",
            can_handle=["http://*", "https://*"],
            keywords=["browse", "navigate", "click", "scroll", "extract"],
            requires_api=True,
            api_key_env="BROWSER_TOKEN",
        ))
        
        # Code tools
        self.register(Tool(
            name="aider",
            category=ToolCategory.CODE,
            description="AI code editing with repo context",
            keywords=["refactor", "rewrite", "explain", "generate"],
            estimated_time_ms=5000,
        ))
        
        self.register(Tool(
            name="grep",
            category=ToolCategory.SEARCH,
            description="Search files for patterns",
            can_handle=["*.py", "*.ts", "*.js", "*.md"],
            keywords=["find", "search", "grep", "locate"],
            estimated_time_ms=100,
        ))
        
        # Audit tools
        self.register(Tool(
            name="repo_audit",
            category=ToolCategory.AUDIT,
            description="Audit repo for issues",
            keywords=["audit", "check", "verify"],
            requires_api=False,
        ))
        
        self.register(Tool(
            name="dependency_audit",
            category=ToolCategory.AUDIT,
            description="Audit dependencies for vulnerabilities",
            keywords=["security", "vuln", "dependency", "audit"],
            requires_api=False,
        ))
        
        # LLM tools
        self.register(Tool(
            name="openai",
            category=ToolCategory.LLM,
            description="OpenAI API",
            keywords=["llm", "gpt", "generate", "complete"],
            requires_api=True,
            api_key_env="OPENAI_API_KEY",
        ))
        
        self.register(Tool(
            name="anthropic",
            category=ToolCategory.LLM,
            description="Anthropic Claude API",
            keywords=["claude", "llm", "generate"],
            requires_api=True,
            api_key_env="ANTHROPIC_API_KEY",
        ))
        
        self.register(Tool(
            name="local_llm",
            category=ToolCategory.LLM,
            description="Local llama.cpp inference",
            keywords=["local", "offline", "llama", "gguf"],
            is_local=True,
            can_handle=["*.py", "*.ts", "*.js"],
        ))
    
    def _register_default_skills(self):
        """Register built-in skills."""
        self.register_skill(Skill(
            name="code-review",
            description="Code review focusing on quality and security",
            keywords=["review", "quality", "security", "pr"],
            is_builtin=True,
            module_path="skills/code_review.py",
        ))
        
        self.register_skill(Skill(
            name="security",
            description="Security best practices",
            keywords=["security", "auth", "vulnerability"],
            is_builtin=True,
            module_path="skills/security.py",
        ))
        
        self.register_skill(Skill(
            name="refactor",
            description="Code refactoring patterns",
            keywords=["refactor", "rewrite", "improve"],
            is_builtin=True,
            module_path="skills/refactor.py",
        ))
    
    def register(self, tool: Tool):
        self._tools[tool.name] = tool
    
    def register_skill(self, skill: Skill):
        self._skills[skill.name] = skill
    
    def get_tool(self, name: str) -> Tool | None:
        return self._tools.get(name)
    
    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)
    
    def find_tools_for_task(self, task: str) -> list[Tool]:
        """Find all tools that can handle the task."""
        matching = []
        for tool in self._tools.values():
            if tool.can_handle_task(task):
                matching.append(tool)
        
        # Sort by success rate
        matching.sort(key=lambda t: t.success_rate, reverse=True)
        return matching
    
    def find_skills_for_task(self, task: str) -> list[Skill]:
        """Find all skills that match the task."""
        matching = []
        for skill in self._skills.values():
            score = skill.matches(task)
            if score > 0:
                matching.append((score, skill))
        
        # Sort by score
        matching.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in matching]
    
    def select_best_tool(self, task: str) -> tuple[Tool | None, str | None]:
        """Select best tool for task, with web fallback if needed.
        
        Returns: (tool, fallback_search_query or None)
        """
        tools = self.find_tools_for_task(task)
        
        if not tools:
            # No local tool found - use web fallback
            if self._web_fallback_enabled:
                return None, f"how to {task}"
            return None, None
        
        best = tools[0]
        
        # Check if tool is available (has required API keys)
        if best.requires_api and best.api_key_env:
            if not os.getenv(best.api_key_env):
                # API key missing - return fallback
                if self._web_fallback_enabled:
                    return best, f"how to use {best.name} for {task}"
                return None, None
        
        return best, None
    
    def get_available_tools(self) -> list[str]:
        """Get list of available tool names."""
        available = []
        for name, tool in self._tools.items():
            if not tool.requires_api:
                available.append(name)
            elif tool.api_key_env and os.getenv(tool.api_key_env):
                available.append(name)
        return available
    
    def get_prompt_context(self) -> str:
        """Generate prompt context about available tools."""
        lines = ["## Available Tools"]
        
        available = self.get_available_tools()
        for tool in available:
            lines.append(f"- {tool}")
        
        lines.append("\n## Available Skills")
        for skill in self._skills.values():
            if skill.is_builtin:
                lines.append(f"- {skill.name}: {skill.description}")
        
        return "\n".join(lines)


# === Singleton ===

_registry: ToolsRegistry | None = None


def get_registry() -> ToolsRegistry:
    global _registry
    if _registry is None:
        _registry = ToolsRegistry()
    return _registry


def get_tools_for_task(task: str) -> list[Tool]:
    return get_registry().find_tools_for_task(task)


def select_tool(task: str) -> tuple[Tool | None, str | None]:
    return get_registry().select_best_tool(task)


# === Web Search Fallback ===

def get_web_search_context(task: str) -> str:
    """Get web search context when local tools are insufficient."""
    _, fallback = select_tool(task)
    
    if not fallback:
        return ""
    
    # Use web search
    from agentnxt_code_assist import tavily_tavily_search
    try:
        results = tavily_tavily_search(
            query=fallback,
            max_results=3,
            search_depth="basic",
        )
        
        if not results:
            return ""
        
        lines = [
            "## Web Search Results",
            "These results can help when local tools are insufficient:",
            "",
        ]
        
        for r in results:
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")[:200]
            lines.append(f"### {title}")
            lines.append(f"{content}...")
            lines.append(f"Source: {url}")
            lines.append("")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"Web search error: {e}"