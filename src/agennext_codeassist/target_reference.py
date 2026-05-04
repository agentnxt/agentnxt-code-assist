"""Parse GitHub target URLs into managed checkout hints."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class TargetReference:
    repo_full_name: str
    kind: str
    branch: str | None = None
    issue_number: int | None = None
    pull_number: int | None = None
    discussion_number: int | None = None

    @property
    def repo_url(self) -> str:
        return f"https://github.com/{self.repo_full_name}.git"


def parse_github_target_url(url: str) -> TargetReference:
    parsed = urlparse(url.strip())
    if parsed.netloc not in {"github.com", "www.github.com"}:
        raise ValueError("target_url must be a github.com URL")

    parts = [unquote(part) for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("target_url must include owner and repository")

    owner, repo = parts[0], parts[1]
    repo_full_name = f"{owner}/{repo}"

    if len(parts) == 2:
        return TargetReference(repo_full_name=repo_full_name, kind="repo")

    marker = parts[2]
    if marker == "tree" and len(parts) >= 4:
        return TargetReference(
            repo_full_name=repo_full_name,
            kind="branch",
            branch="/".join(parts[3:]),
        )

    if marker == "pull" and len(parts) >= 4:
        return TargetReference(
            repo_full_name=repo_full_name,
            kind="pull_request",
            pull_number=_parse_number(parts[3], "pull request"),
            issue_number=_parse_number(parts[3], "pull request"),
        )

    if marker == "issues" and len(parts) >= 4:
        return TargetReference(
            repo_full_name=repo_full_name,
            kind="issue",
            issue_number=_parse_number(parts[3], "issue"),
        )

    if marker == "discussions" and len(parts) >= 4:
        return TargetReference(
            repo_full_name=repo_full_name,
            kind="discussion",
            discussion_number=_parse_number(parts[3], "discussion"),
        )

    raise ValueError(
        "target_url must be a repo, branch, pull request, issue, or discussion URL"
    )


def _parse_number(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label} number: {value}") from exc
