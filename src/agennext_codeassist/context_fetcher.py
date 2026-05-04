"""Fetch lightweight GitHub target context for coding tasks."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class TargetContext:
    source: str
    title: str | None = None
    body: str | None = None
    state: str | None = None
    url: str | None = None

    def to_prompt_block(self) -> str:
        parts = [f"Context source: {self.source}"]
        if self.url:
            parts.append(f"URL: {self.url}")
        if self.state:
            parts.append(f"State: {self.state}")
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.body:
            parts.append("Body:\n" + self.body.strip())
        return "\n".join(parts).strip()


def fetch_target_context(
    *,
    repo_full_name: str | None,
    target_kind: str | None,
    issue_number: int | None = None,
    pull_number: int | None = None,
    discussion_number: int | None = None,
    target_url: str | None = None,
) -> TargetContext | None:
    """Fetch issue/PR context where the GitHub REST API supports it.

    Discussions are not fetched yet because GitHub discussions require GraphQL access in
    most setups. We still return a marker so the caller can flag missing hydration.
    """

    if not repo_full_name or not target_kind:
        return None

    if target_kind == "issue" and issue_number is not None:
        data = _github_json(f"/repos/{repo_full_name}/issues/{issue_number}")
        return TargetContext(
            source="github_issue",
            title=data.get("title"),
            body=data.get("body"),
            state=data.get("state"),
            url=data.get("html_url") or target_url,
        )

    if target_kind == "pull_request" and pull_number is not None:
        data = _github_json(f"/repos/{repo_full_name}/pulls/{pull_number}")
        return TargetContext(
            source="github_pull_request",
            title=data.get("title"),
            body=data.get("body"),
            state=data.get("state"),
            url=data.get("html_url") or target_url,
        )

    if target_kind == "discussion":
        return TargetContext(
            source="github_discussion_unhydrated",
            title=f"Discussion #{discussion_number}" if discussion_number else None,
            body="Discussion body hydration is not implemented yet. Paste discussion requirements into the instruction.",
            url=target_url,
        )

    return None


def _github_json(path: str) -> dict[str, object]:
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "agentnxt-code-assist",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"failed to fetch GitHub context from {path}: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to fetch GitHub context from {path}: {exc.reason}") from exc
