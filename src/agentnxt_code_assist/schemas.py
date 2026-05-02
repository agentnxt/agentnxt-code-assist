"""Request and response models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class CheckResult(BaseModel):
    command: str
    exit_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""


class AssistRequest(BaseModel):
    instruction: str = Field(min_length=1)
    repo_path: Path | None = None
    repo_url: str | None = None
    repo_full_name: str | None = None
    base_branch: str = "main"
    work_branch: str | None = None
    workspace_root: Path | None = None
    issue_number: int | None = None
    push: bool = False
    open_pr: bool = False
    pr_title: str | None = None
    pr_body: str | None = None
    checks: list[str] = Field(default_factory=list)
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

    @model_validator(mode="after")
    def validate_repo_source(self) -> "AssistRequest":
        local_mode = self.repo_path is not None
        managed_mode = bool(self.repo_url or self.repo_full_name)
        if local_mode == managed_mode:
            raise ValueError("provide exactly one of repo_path or repo_url/repo_full_name")
        if managed_mode and not self.work_branch:
            if self.issue_number is None:
                raise ValueError(
                    "managed checkout mode requires work_branch or issue_number"
                )
            self.work_branch = f"code-assist/issue-{self.issue_number}"
        if self.work_branch in {"main", "master", self.base_branch}:
            raise ValueError("work_branch must not be the base branch")
        if self.open_pr and not self.push:
            raise ValueError("open_pr requires push=true")
        return self


class AssistResult(BaseModel):
    ok: bool
    repo_path: str
    files: list[str]
    changed_files: list[str] = Field(default_factory=list)
    output: str = ""
    error: str | None = None
    base_branch: str | None = None
    work_branch: str | None = None
    before_sha: str | None = None
    after_sha: str | None = None
    checks: list[CheckResult] = Field(default_factory=list)
    pushed: bool = False
    pr_url: str | None = None
