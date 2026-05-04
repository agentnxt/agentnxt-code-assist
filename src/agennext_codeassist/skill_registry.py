"""Skill registry for Code Assist.

Extensible skill system with:
- Built-in skills (quality, security, refactoring, etc.)
- External skills from GitHub
- Dynamic skill loading
- Skill chaining for complex tasks
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import json


# === Skill Categories ===

class SkillCategory(Enum):
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DEVOPS = "devops"
    ARCHITECTURE = "architecture"
    DATA = "data"
    AI = "ai"


class SkillPriority(Enum):
    REQUIRED = "required"  # Must apply
    RECOMMENDED = "recommended"  # Should apply if applicable
    OPTIONAL = "optional"  # Optionally apply


@dataclass
class Skill:
    """A skill that can be applied to a task."""
    name: str
    description: str
    
    # Prompt/guidance
    prompt: str
    category: SkillCategory = SkillCategory.CODE_QUALITY
    priority: SkillPriority = SkillPriority.RECOMMENDED
    
    # Matching
    keywords: list[str] = field(default_factory=list)
    file_extensions: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    
    # Source
    is_builtin: bool = True
    source_url: str | None = None
    module_path: str | None = None
    
    # Requirements
    requires_tools: list[str] = field(default_factory=list)
    requires_api: bool = False
    api_key_env: str | None = None
    
    # Execution
    pre_hooks: list[str] = field(default_factory=list)  # Commands to run before
    post_hooks: list[str] = field(default_factory=list)  # Commands to run after
    
    def matches_query(self, query: str) -> float:
        """Return match score (0-1) for query."""
        query_lower = query.lower()
        score = 0.0
        
        # Keywords match
        for kw in self.keywords:
            if kw.lower() in query_lower:
                score += 0.25
        
        # Language match
        for lang in self.languages:
            if lang.lower() in query_lower:
                score += 0.15
        
        # File extension match
        for ext in self.file_extensions:
            if ext in query_lower:
                score += 0.1
        
        return min(1.0, score)
    
    def matches_file(self, path: str) -> bool:
        """Check if skill applies to file."""
        if not self.file_extensions:
            return True  # Universal skill
        
        for ext in self.file_extensions:
            if path.endswith(ext):
                return True
        return False


# === Built-in Skills ===

_SKILLS: dict[str, Skill] = {
    # Code Quality
    "code-review": Skill(
        name="code-review",
        description="Rigorous code review focusing on data structures, simplicity, security, pragmatism, and risk/safety evaluation.",
        prompt="""
## Skill: Code Review

Apply code review discipline:

1. **Data Structures**: Use appropriate data structures for the problem. Consider time/space.
2. **Simplicity**: Prefer simple solutions over clever ones. Clear > Concise.
3. **Security**: Check for: injection, auth issues, secrets exposure, input validation.
4. **Pragmatism**: Balance ideal with practical. Ship working code.
5. **Risk/Safety**: Identify potential failure modes and edge cases.

**Review Checklist**:
- [ ] No hardcoded secrets or API keys
- [ ] Input validation present
- [ ] Error handling appropriate
- [ ] No SQL/natural language injection risks
- [ ] Dependencies are trusted/audited
- [ ] Tests cover critical paths
- [ ] Documentation updated
""",
        category=SkillCategory.CODE_QUALITY,
        priority=SkillPriority.REQUIRED,
        keywords=["review", "pr", "quality", "check"],
        languages=["python", "javascript", "typescript"],
    ),
    
    "security": Skill(
        name="security",
        description="Security best practices: auth, encryption, validation, secrets management.",
        prompt="""
## Skill: Security

Apply security best practices:

1. **Authentication**: Verify auth flows, token handling, session management.
2. **Authorization**: Check role-based access, principle of least privilege.
3. **Input Validation**: Validate all inputs, parameterize queries.
4. **Secrets**: Never log or hardcode secrets. Use env vars/secrets managers.
5. **Encryption**: Use TLS, encrypt sensitive data at rest.
6. **Dependencies**: Check for known CVEs, keep deps updated.

**Security Checklist**:
- [ ] No credentials in code/logs
- [ ] SQL uses parameterized queries
- [ ] User input is validated/sanitized
- [ ] Auth tokens handled securely
- [ ] HTTPS used for sensitive data
- [ ] No sensitive data in URLs
""",
        category=SkillCategory.SECURITY,
        priority=SkillPriority.REQUIRED,
        keywords=["security", "auth", "encryption", "credential", "secret"],
        languages=["python", "javascript"],
    ),
    
    "refactor": Skill(
        name="refactor",
        description="Code refactoring: improve structure without changing behavior.",
        prompt="""
## Skill: Refactoring

Apply refactoring discipline:

1. **Behavior**: Preserve existing behavior. Tests must pass.
2. **Incremental**: Make small, reversible changes.
3. **Intent**: Code intent should be clear from names/docstrings.
4. **DRY**: Extract common patterns, avoid duplication.
5. **Single Responsibility**: Each function/class does one thing well.

**Refactoring Patterns**:
- Extract function: duplicated code → shared function
- Rename: unclear name → descriptive name
- Compose: separate concerns → smaller focused functions
- Inline: trivial wrapper → direct call
- Replace conditionals: polymorphic dispatch or strategy

**Before committing**:
- [ ] Tests still pass
- [ ] No behavioral changes
- [ ] Intent is clearer
""",
        category=SkillCategory.REFACTORING,
        priority=SkillPriority.RECOMMENDED,
        keywords=["refactor", "cleanup", "improve", "restructure"],
        languages=["python", "javascript", "typescript"],
    ),
    
    "testing": Skill(
        name="testing",
        description="Write effective tests: unit, integration, E2E patterns.",
        prompt="""
## Skill: Testing

Apply testing discipline:

1. **Test Pyramid**: Many unit tests, fewer integration, minimal E2E.
2. **Arrange-Act-Assert**: Clear test structure.
3. **Isolation**: Tests don't depend on each other.
4. **Edge Cases**: Test happy path + error handling + edge cases.
5. **Meaningful Names**: Test names describe what's being tested.

**Test Patterns**:
- Unit: Test single function/class in isolation
- Integration: Test component interactions
- Mock: Replace external dependencies
- Fixture: Shared test data setup
- Parametrize: Same test with different inputs

**Coverage Goals**:
- Critical paths: 100%
- Error handling: 100%
- Edge cases: As reasonable
""",
        category=SkillCategory.TESTING,
        priority=SkillPriority.RECOMMENDED,
        keywords=["test", "spec", "mock", "fixture", "coverage"],
        languages=["python", "javascript", "typescript"],
    ),
    
    "documentation": Skill(
        name="documentation",
        description="Write clear documentation: README, API docs, docstrings.",
        prompt="""
## Skill: Documentation

Apply documentation discipline:

1. **README**: Project overview, quick start, prerequisites, examples.
2. **API Docs**: Endpoints, request/response format, error codes.
3. **Docstrings**: Public APIs need docstrings. Params, returns, raises.
4. **Inline**: Complex logic needs comments. "Why" not "What".
5. **Changelog**: Track significant changes.

**Docstring Formats**:
- Google: Args, Returns, Raises
- NumPy: Parameters, Returns
- Sphinx: reStructuredText

**Check**:
- [ ] README has quick start
- [ ] API has examples
- [ ] Public functions documented
- [ ] Complex logic explained
- [ ] Changelog updated
""",
        category=SkillCategory.DOCUMENTATION,
        priority=SkillPriority.OPTIONAL,
        keywords=["doc", "readme", "changelog", "comment"],
        languages=["python", "javascript"],
    ),
    
    "frontend": Skill(
        name="frontend",
        description="Build production-ready frontend: components, accessibility, responsive.",
        prompt="""
## Skill: Frontend Development

Apply frontend discipline:

1. **Component Architecture**: Reusable, composable components.
2. **State Management**: Explicit, predictable state.
3. **Accessibility**: Semantic HTML, ARIA, keyboard navigation.
4. **Responsive**: Mobile-first, fluid layouts.
5. **Performance**: Lazy loading, caching, optimized assets.

**Checklist**:
- [ ] Semantic HTML elements
- [ ] Form inputs have labels
- [ ] Focus states visible
- [ ] Keyboard navigable
- [ ] Loading/error states
- [ ] No hardcoded secrets
- [ ] Environment-specific URLs in env vars

**Run after**:
- TypeScript: typecheck
- React/Vue: lint + build
- CSS: stylelint or equivalent
""",
        category=SkillCategory.FRONTEND,
        priority=SkillPriority.RECOMMENDED,
        keywords=["ui", "component", "frontend", "css", "jsx", "tsx"],
        file_extensions=[".tsx", ".jsx", ".css", ".scss"],
    ),
    
    "backend": Skill(
        name="backend",
        description="Build production backend: APIs, database, security, error handling.",
        prompt="""
## Skill: Backend Development

Apply backend discipline:

1. **API Design**: RESTful or GraphQL. Consistent patterns.
2. **Error Handling**: Proper HTTP codes, error messages.
3. **Validation**: Input validation, sanitization.
4. **Database**: Proper queries, connections, migrations.
5. **Security**: Auth, authorization, rate limiting.

**Checklist**:
- [ ] Proper HTTP status codes
- [ ] Input validation
- [ ] Error messages (no stack traces)
- [ ] Connection pooling
- [ ] Authentication check
- [ ] Authorization check

**Run after**:
- Lint + type check
- Unit tests
- Integration tests
""",
        category=SkillCategory.BACKEND,
        priority=SkillPriority.RECOMMENDED,
        keywords=["api", "backend", "server", "database"],
        languages=["python", "javascript"],
    ),
    
    "devops": Skill(
        name="devops",
        description="DevOps best practices: CI/CD, containers, monitoring.",
        prompt="""
## Skill: DevOps

Apply DevOps discipline:

1. **CI/CD**: Automated pipelines, tests, deployments.
2. **Containers**: Minimal images, non-root user, healthcheck.
3. **Configuration**: 12-factor, env vars for config.
4. **Monitoring**: Logs, metrics, alerts.
5. **Rollback**: Ensure rollback capability.

**Docker Best Practices**:
- [ ] Use specific version tags
- [ ] Multi-stage builds
- [ ] Run as non-root
- [ ] HEALTHCHECK defined
- [ ] Minimal packages

**CI Best Practices**:
- [ ] Builds reproducible
- [ ] Tests automated
- [ ] Secrets from env vars
- [ ] Artifacts versioned
""",
        category=SkillCategory.DEVOPS,
        priority=SkillPriority.OPTIONAL,
        keywords=["docker", "ci", "cd", "pipeline", "deploy", "kubernetes"],
        file_extensions=[".dockerfile", ".yml", ".yaml"],
    ),
    
    "ai-prompt-engineering": Skill(
        name="ai-prompt-engineering",
        description="Effective AI/LLM prompting techniques.",
        prompt="""
## Skill: AI Prompt Engineering

Apply prompt engineering:

1. **Clear Intent**: State what you want clearly.
2. **Context**: Provide relevant background.
3. **Constraints**: Specify limits/requirements.
4. **Examples**: Show input/output pairs.
5. **Format**: Define output structure.

**Patterns**:
- Chain of Thought: Step by step reasoning
- Few-shot: Example driven
- Role: Act as [role]
- Template: Fill in [placeholders]

**Check**:
- [ ] Intent is clear
- [ ] Enough context provided
- [ ] Constraints specified
- [ ] Expected output shown
- [ ] Ambiguous terms avoided
""",
        category=SkillCategory.AI,
        priority=SkillPriority.OPTIONAL,
        keywords=["prompt", "llm", "ai", "gpt", "claude"],
    ),
}


# === Skills Registry ===

class SkillsRegistry:
    """Extensible skills registry."""
    
    def __init__(self):
        self._skills: dict[str, Skill] = dict(_SKILLS)
        self._skill_hooks: dict[str, Callable] = {}
    
    def register(self, skill: Skill):
        self._skills[skill.name] = skill
    
    def register_hook(self, name: str, hook: Callable):
        self._skill_hooks[name] = hook
    
    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)
    
    def find_for_query(self, query: str) -> list[tuple[Skill, float]]:
        """Find skills matching query."""
        matches = []
        for skill in self._skills.values():
            score = skill.matches_query(query)
            if score > 0.1:
                matches.append((skill, score))
        
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def find_for_file(self, path: str) -> list[Skill]:
        """Find skills applicable to file."""
        return [
            s for s in self._skills.values()
            if s.matches_file(path)
        ]
    
    def find_by_category(self, category: SkillCategory) -> list[Skill]:
        return [
            s for s in self._skills.values()
            if s.category == category
        ]
    
    def find_required(self) -> list[Skill]:
        return [
            s for s in self._skills.values()
            if s.priority == SkillPriority.REQUIRED
        ]
    
    def get_prompt_for_skills(self, skill_names: list[str]) -> str:
        """Get combined prompt for skill names."""
        blocks = []
        for name in skill_names:
            skill = self._skills.get(name)
            if skill:
                blocks.append(skill.prompt)
            else:
                blocks.append(f"## Unknown skill: {name}")
        return "\n\n\n".join(blocks)
    
    def get_auto_prompt(self, query: str, max_skills: int = 3) -> str:
        """Get prompt for automatically selected skills."""
        matches = self.find_for_query(query)[:max_skills]
        
        if not matches:
            return ""
        
        blocks = [
            "## Applied Skills",
            *(f"{i+1}. {s.name}: {s.description}" 
              for i, (s, _) in enumerate(matches)),
            "",
            *(s.prompt for s, _ in matches),
        ]
        return "\n\n".join(blocks)


# === Singleton ===

_registry: SkillsRegistry | None = None


def get_skills_registry() -> SkillsRegistry:
    global _registry
    if _registry is None:
        _registry = SkillsRegistry()
    return _registry


def available_skills() -> list[Skill]:
    return list(get_skills_registry()._skills.values())


def skill_prompt_block(skill_names: list[str]) -> str:
    return get_skills_registry().get_prompt_for_skills(skill_names)


def auto_skills_prompt(query: str) -> str:
    return get_skills_registry().get_auto_prompt(query)
