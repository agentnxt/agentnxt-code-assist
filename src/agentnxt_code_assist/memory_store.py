"""Lightweight project memory for Code Assist runs.

Memory is intentionally stored as reviewable Markdown inside the repository or
workspace. It must not contain secrets, tokens, credentials, or private keys.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agentnxt_code_assist.schemas import AssistResult

_DEFAULT_MEMORY_PATH = ".agennext/memory.md"
_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "private_key",
    "secret",
    "token",
)


def default_memory_path() -> str:
    return _DEFAULT_MEMORY_PATH


def read_memory(repo_path: Path, relative_path: str = _DEFAULT_MEMORY_PATH) -> str | None:
    memory_path = _safe_path(repo_path, relative_path)
    if not memory_path.exists():
        return None
    text = memory_path.read_text(encoding="utf-8")
    return text.strip() or None


def append_memory(repo_path: Path, relative_path: str, result: AssistResult) -> Path:
    memory_path = _safe_path(repo_path, relative_path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    previous = memory_path.read_text(encoding="utf-8") if memory_path.exists() else _header()
    entry = _entry(result)
    memory_path.write_text(previous.rstrip() + "\n\n" + entry + "\n", encoding="utf-8")
    return memory_path


def memory_prompt_block(memory: str | None) -> str:
    if not memory:
        return ""
    return (
        "## Project memory\n"
        "Use this memory as durable project context. Do not treat it as a source of secrets.\n\n"
        f"{memory[-6000:]}"
    )


def _header() -> str:
    return (
        "# AGenNext Code Assist Memory\n\n"
        "Persistent, reviewable project memory for Code Assist runs.\n\n"
        "Do not store secrets, tokens, passwords, private keys, or credentials here.\n"
    )


def _entry(result: AssistResult) -> str:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        f"## Run memory — {timestamp}",
        "",
        f"- Repository: {result.repo_full_name or result.repo_path}",
        f"- Target: {result.target_url or 'local checkout'}",
        f"- Branch: {result.work_branch or 'local checkout'}",
        f"- Status: {'ok' if result.ok else 'needs attention'}",
        f"- Changed files: {', '.join(result.changed_files) if result.changed_files else 'none'}",
        f"- Checks: {len(result.checks)} total, {sum(1 for check in result.checks if check.exit_code != 0)} failed",
        f"- Anomalies: {len(result.anomalies)}",
        f"- Error: {_sanitize(result.error or 'none')}",
    ]
    if result.change_log:
        lines.extend(["", "### Summary", _sanitize(result.change_log[-3000:])])
    return "\n".join(lines)


def _safe_path(repo_path: Path, relative_path: str) -> Path:
    output_path = (repo_path / relative_path).resolve()
    if not output_path.is_relative_to(repo_path.resolve()):
        raise ValueError(f"memory_path escapes repo: {relative_path}")
    return output_path


def _sanitize(value: str) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in _SECRET_MARKERS):
            lines.append("[redacted potential secret]")
        else:
            lines.append(line)
    return "\n".join(lines)
