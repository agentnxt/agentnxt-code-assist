"""Request and response models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AssistRequest(BaseModel):
    instruction: str = Field(min_length=1)
    repo_path: Path
    files: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    api_base: str | None = None
    api_key: str | None = None
    env_vars: dict[str, str] = Field(default_factory=dict)
    auto_yes: bool | None = None
    auto_commits: bool | None = None
    dry_run: bool | None = None
    stream: bool = False


class AssistResult(BaseModel):
    ok: bool
    repo_path: str
    files: list[str]
    changed_files: list[str] = Field(default_factory=list)
    output: str = ""
    error: str | None = None
