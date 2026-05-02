"""Skill registry for focused Code Assist passes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    prompt: str


_SKILLS: dict[str, Skill] = {
    "frontend-development": Skill(
        name="frontend-development",
        description="Build production-ready frontend UI from requirements, mockups, or design-system tokens.",
        prompt="""
## Skill: Front-end development

Apply front-end development discipline to this task:

- Translate requirements, mockups, and design-system tokens into accessible UI.
- Prefer componentized, typed, maintainable UI code.
- Keep state management simple and explicit.
- Preserve existing routing, API contracts, and backend safety guardrails.
- Implement responsive layouts for desktop and mobile where applicable.
- Use semantic HTML and accessible controls, labels, focus states, and keyboard paths.
- Keep visual styling consistent with the existing design system.
- Avoid hard-coded secrets, API keys, or environment-specific URLs in client code.
- Add or update frontend tests where the repo already has a test pattern.
- Run relevant checks: typecheck, lint, unit/component tests, build, smoke.
- Document UI changes in the change log, including next steps and open design gaps.
""".strip(),
    ),
    "figma-design": Skill(
        name="figma-design",
        description="Create Figma-ready mockup and design-system handoff artifacts.",
        prompt="""
## Skill: Figma design handoff

Apply Figma/design-system discipline to this task:

- Capture user flows, screens, states, and components before implementation when relevant.
- Produce or update design tokens for color, spacing, radius, typography, and elevation.
- Keep artifacts importable or understandable for Figma/Token Studio workflows.
- Identify component variants, empty states, loading states, error states, and responsive behavior.
- Ensure the implementation can be traced back to the mockup and design-system decisions.
""".strip(),
    ),
}


def available_skills() -> list[Skill]:
    return list(_SKILLS.values())


def skill_prompt_block(skill_names: list[str]) -> str:
    if not skill_names:
        return ""
    blocks: list[str] = []
    unknown: list[str] = []
    for raw_name in skill_names:
        name = raw_name.strip().lower()
        if not name:
            continue
        skill = _SKILLS.get(name)
        if skill is None:
            unknown.append(raw_name)
            continue
        blocks.append(skill.prompt)
    if unknown:
        blocks.append(
            "## Unknown requested skills\n"
            + "\n".join(f"- {name}" for name in unknown)
            + "\nTreat unknown skills as informational only and do not invent unsafe behavior."
        )
    return "\n\n".join(blocks)
