"""Lightweight project memory for Code Assist runs.

Memory is intentionally stored as reviewable Markdown inside the repository or
workspace. It must not contain secrets, tokens, credentials, or private keys.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agennext_codeassist.schemas import AssistResult

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


# === Memory Compaction ===

_MAX_MEMORY_BYTES = 100_000
_SUMMARY_MAX_CHARS = 2_000


def compact_memory(repo_path: Path, relative_path: str = _DEFAULT_MEMORY_PATH) -> int:
    """Compress memory if it exceeds MAX_MEMORY_BYTES.
    
    Returns number of entries removed, 0 if no compaction needed.
    """
    memory_path = _safe_path(repo_path, relative_path)
    if not memory_path.exists():
        return 0
    
    size = memory_path.stat().st_size
    if size < _MAX_MEMORY_BYTES:
        return 0
    
    # Read existing memory
    text = memory_path.read_text(encoding="utf-8")
    entries = text.split("### Run at ")
    
    if len(entries) <= 2:
        return 0  # Can't compact much
    
    # Keep first entry (header) + last 10 runs
    kept = ["### Run at ".join(entries[:1] + entries[-10:])]
    summary = f"\n\n### Earlier runs summarized ({len(entries) - 11} runs omitted)\n"
    summary += f"- Previous runs truncated for brevity. Full audit traces in `.agennext/audit/runs/`\n"
    kept.append(summary)
    
    compacted = "### Run at ".join(kept)
    memory_path.write_text(compacted, encoding="utf-8")
    
    removed = len(entries) - 11
    print(f"Memory compacted: {removed} earlier runs omitted")
    return removed


def summarize_memory_entries(entries: list[str]) -> str:
    """Create condensed summary of memory entries.
    
    Extracts operation types and outcomes without full context.
    """
    if not entries:
        return "No previous runs."
    
    ops: list[str] = []
    for entry in entries[:20]:  # Last 20 runs
        lines = entry.splitlines()
        for line in lines:
            if line.startswith("- "):
                ops.append(line[:100])  # Truncate long details
        if len(ops) >= 10:
            break
    
    summary = f"### Last {len(ops)} operations"
    if ops:
        summary += "\n" + "\n".join(ops)
    return summary
