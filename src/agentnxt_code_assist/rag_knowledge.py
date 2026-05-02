"""RAG knowledge base context loader.

This module intentionally provides a lightweight, deterministic context loader.
It does not implement vector search itself; it prepares local knowledge snippets
and optional remote retrieval results for the coding prompt.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_ALLOWED_SUFFIXES = {".md", ".mdx", ".txt", ".rst", ".json", ".yaml", ".yml"}
_MAX_FILE_BYTES = 80_000
_MAX_TOTAL_CHARS = 24_000


@dataclass(frozen=True)
class RagSourceResult:
    source: str
    content: str


def load_rag_context(
    *,
    repo_path: Path,
    query: str,
    paths: list[str],
    remote_urls: list[str],
    max_chars: int = _MAX_TOTAL_CHARS,
) -> str | None:
    snippets: list[RagSourceResult] = []
    for raw_path in paths:
        snippets.extend(_load_path(repo_path, raw_path))
    for url in remote_urls:
        remote = _load_remote(url, query=query)
        if remote:
            snippets.append(remote)

    if not snippets:
        return None

    lines = [
        "## RAG knowledge base context",
        "Use this as read-only project knowledge. Prefer repository code over stale knowledge when they conflict.",
        "Do not copy secrets from knowledge-base content into code, logs, memory, or change logs.",
        "",
    ]
    remaining = max_chars
    for snippet in snippets:
        if remaining <= 0:
            break
        content = snippet.content.strip()
        if not content:
            continue
        content = content[:remaining]
        lines.extend([f"### Source: {snippet.source}", content, ""])
        remaining -= len(content)
    return "\n".join(lines).strip() or None


def _load_path(repo_path: Path, raw_path: str) -> list[RagSourceResult]:
    if not raw_path.strip():
        return []
    path = (repo_path / raw_path).resolve()
    if not path.is_relative_to(repo_path.resolve()):
        raise ValueError(f"rag path escapes repo: {raw_path}")
    if not path.exists():
        return []
    if path.is_file():
        loaded = _load_file(path, repo_path)
        return [loaded] if loaded else []
    results: list[RagSourceResult] = []
    for candidate in sorted(path.rglob("*")):
        if len(results) >= 50:
            break
        loaded = _load_file(candidate, repo_path)
        if loaded:
            results.append(loaded)
    return results


def _load_file(path: Path, repo_path: Path) -> RagSourceResult | None:
    if not path.is_file() or path.suffix.lower() not in _ALLOWED_SUFFIXES:
        return None
    if path.stat().st_size > _MAX_FILE_BYTES:
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return RagSourceResult(source=str(path.relative_to(repo_path)), content=content)


def _load_remote(url: str, *, query: str) -> RagSourceResult | None:
    if not url or not url.startswith(("http://", "https://")):
        return None
    request = urllib.request.Request(
        url,
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "agennext-code-assist"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    if isinstance(payload, dict):
        for key in ("context", "content", "text", "answer"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return RagSourceResult(source=url, content=value)
        docs = payload.get("documents") or payload.get("results")
        if isinstance(docs, list):
            parts: list[str] = []
            for item in docs[:8]:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("content") or item.get("text") or item.get("page_content")
                    if isinstance(text, str):
                        parts.append(text)
            if parts:
                return RagSourceResult(source=url, content="\n\n".join(parts))
    return None
