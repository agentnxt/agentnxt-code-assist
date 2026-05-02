"""Managed git workspace helpers for target repository checkout."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse


class GitWorkspaceError(RuntimeError):
    """Raised when managed git workspace operations fail."""


def sanitize_repo_name(repo_url: str | None = None, repo_full_name: str | None = None) -> str:
    raw = repo_full_name or _full_name_from_url(repo_url or "")
    if not raw:
        raise GitWorkspaceError("repo_url or repo_full_name is required")
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "__", raw.strip().strip("/"))
    sanitized = sanitized.strip("._-")
    if not sanitized:
        raise GitWorkspaceError("could not derive safe repository workspace name")
    return sanitized


def ensure_repo_checkout(
    *,
    repo_url: str | None,
    repo_full_name: str | None,
    workspace_root: Path,
) -> Path:
    workspace_root = workspace_root.expanduser().resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    checkout_dir = (workspace_root / sanitize_repo_name(repo_url, repo_full_name)).resolve()
    if not checkout_dir.is_relative_to(workspace_root):
        raise GitWorkspaceError("resolved checkout path escaped workspace root")

    clone_url = repo_url or f"https://github.com/{repo_full_name}.git"
    if checkout_dir.exists():
        if not (checkout_dir / ".git").exists():
            raise GitWorkspaceError(f"workspace path exists but is not a git repo: {checkout_dir}")
        _run_git(["fetch", "--prune", "origin"], checkout_dir)
        return checkout_dir

    _run_git(["clone", _with_token(clone_url), str(checkout_dir)], workspace_root)
    return checkout_dir


def configure_git_identity(repo_path: Path, *, user_name: str, user_email: str) -> None:
    _run_git(["config", "user.name", user_name], repo_path)
    _run_git(["config", "user.email", user_email], repo_path)


def checkout_base_branch(repo_path: Path, base_branch: str) -> None:
    _run_git(["checkout", base_branch], repo_path)
    _run_git(["pull", "--ff-only", "origin", base_branch], repo_path)


def create_or_reset_work_branch(repo_path: Path, work_branch: str, base_branch: str) -> None:
    if work_branch in {"main", "master", base_branch}:
        raise GitWorkspaceError("refusing to edit directly on base branch")
    _run_git(["checkout", "-B", work_branch, f"origin/{base_branch}"], repo_path)


def get_current_sha(repo_path: Path) -> str:
    return _run_git(["rev-parse", "HEAD"], repo_path).strip()


def changed_files(repo_path: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    files: list[str] = []
    for line in proc.stdout.splitlines():
        if line.strip():
            files.append(line[3:] if len(line) > 3 else line.strip())
    return files


def push_branch(repo_path: Path, work_branch: str) -> None:
    _run_git(["push", "-u", "origin", work_branch], repo_path)


def _full_name_from_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not path and repo_url.startswith("git@"):
        path = repo_url.split(":", 1)[-1]
        if path.endswith(".git"):
            path = path[:-4]
    return path


def _with_token(repo_url: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token or not repo_url.startswith("https://github.com/"):
        return repo_url
    return repo_url.replace("https://", f"https://x-access-token:{token}@", 1)


def _redact(value: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if token:
        value = value.replace(token, "***")
    return value


def _run_git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        command = "git " + " ".join(_redact(arg) for arg in args)
        raise GitWorkspaceError(
            f"{command} failed with exit code {proc.returncode}: {_redact(proc.stderr.strip())}"
        )
    return proc.stdout
