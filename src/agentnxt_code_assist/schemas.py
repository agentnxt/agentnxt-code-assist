"""Request and response models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from agentnxt_code_assist.target_reference import parse_github_target_url


class CheckResult(BaseModel):
    command: str
    exit_code: int
    stdout_tail: str = ""
    stderr_tail: str = ""


class RepoAnomalyResult(BaseModel):
    severity: str
    code: str
    message: str
    evidence: str | None = None


class AssistRequest(BaseModel):
    instruction: str = Field(min_length=1)
    repo_path: Path | None = None
    repo_url: str | None = None
    repo_full_name: str | None = None
    target_url: str | None = None
    target_kind: str | None = None
    base_branch: str = "main"
    work_branch: str | None = None
    workspace_root: Path | None = None
    issue_number: int | None = None
    pull_number: int | None = None
    discussion_number: int | None = None
    hydrate_context: bool = True
    audit_repo: bool = True
    fail_on_anomaly_severity: str | None = None
    write_change_log: bool = True
    change_log_path: str = "CODE_ASSIST_CHANGELOG.md"

    # Write/remote-operation guardrails. These must be explicitly authorized.
    allow_commits: bool = False
    allow_push: bool = False
    allow_pr: bool = False
    allow_merge: bool = False

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
        if self.target_url:
            target = parse_github_target_url(self.target_url)
            self.repo_full_name = self.repo_full_name or target.repo_full_name
            self.repo_url = self.repo_url or target.repo_url
            self.target_kind = target.kind
            if target.branch and self.base_branch == "main":
                self.base_branch = target.branch
            self.issue_number = self.issue_number or target.issue_number
            self.pull_number = self.pull_number or target.pull_number
            self.discussion_number = self.discussion_number or target.discussion_number

        local_mode = self.repo_path is not None
        managed_mode = bool(self.repo_url or self.repo_full_name or self.target_url)
        if local_mode == managed_mode:
            raise ValueError("provide exactly one of repo_path or target_url/repo_url/repo_full_name")
        if managed_mode and not self.work_branch:
            if self.issue_number is None and self.pull_number is None and self.discussion_number is None:
                raise ValueError(
                    "managed checkout mode requires work_branch or issue/pull/discussion number"
                )
            suffix = (
                f"issue-{self.issue_number}"
                if self.issue_number is not None
                else f"pr-{self.pull_number}"
                if self.pull_number is not None
                else f"discussion-{self.discussion_number}"
            )
            self.work_branch = f"code-assist/{suffix}"
        if self.work_branch in {"main", "master", self.base_branch}:
            raise ValueError("work_branch must not be the base branch")
        if self.auto_commits and not self.allow_commits:
            raise ValueError("auto_commits requires allow_commits=true")
        if self.push and not self.allow_push:
            raise ValueError("push requires allow_push=true")
        if self.open_pr and not self.allow_pr:
            raise ValueError("open_pr requires allow_pr=true")
        if self.open_pr and not self.push:
            raise ValueError("open_pr requires push=true")
        if self.allow_merge:
            raise ValueError("merge is not supported by code-assist; merge must happen outside this tool after human approval")
        if self.fail_on_anomaly_severity not in {None, "info", "warning", "error"}:
            raise ValueError("fail_on_anomaly_severity must be info, warning, error, or null")
        if not self.change_log_path.strip():
            raise ValueError("change_log_path must not be empty")
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
    target_url: str | None = None
    target_kind: str | None = None
    repo_full_name: str | None = None
    issue_number: int | None = None
    pull_number: int | None = None
    discussion_number: int | None = None
    hydrated_context: str | None = None
    anomalies: list[RepoAnomalyResult] = Field(default_factory=list)
    change_log: str | None = None
    change_log_path: str | None = None
