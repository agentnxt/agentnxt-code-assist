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


# === Cloud RAG Backend Integration ===

_CLOUD_RAG_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/rag/retrieve",
    "anthropic": "https://api.anthropic.com/v1/rag",
    "custom": None,  # Set via RAG_API_BASE env var
}


def get_rag_endpoint() -> str | None:
    """Get the configured RAG API endpoint."""
    custom = _CLOUD_RAG_ENDPOINTS.get("custom")
    if custom:
        return custom
    # Default to custom env var if set
    return __import__("os").getenv("RAG_API_BASE") or _CLOUD_RAG_ENDPOINTS.get("openai")


def query_cloud_rag(
    query: str,
    *,
    repo_name: str | None = None,
    top_k: int = 4,
    filter_tags: list[str] | None,
) -> list[str]:
    """Query cloud RAG backend for relevant knowledge.
    
    Args:
        query: Search query string
        repo_name: Optional repository name to filter by
        top_k: Number of results to return
        filter_tags: Optional tags to filter by
    
    Returns:
        List of relevant knowledge snippets
    """
    import os
    endpoint = get_rag_endpoint()
    if not endpoint:
        return []
    
    payload: dict[str, Any] = {
        "query": query,
        "top_k": top_k,
    }
    if repo_name:
        payload["repo_name"] = repo_name
    if filter_tags:
        payload["filters"] = {"tags": filter_tags}
    
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "agennext-code-assist",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []
    
    results: list[str] = []
    items = data.get("results") or data.get("documents") or data.get("chunks") or []
    if isinstance(items, list):
        for item in items[:top_k]:
            if isinstance(item, str):
                results.append(item)
            elif isinstance(item, dict):
                text = item.get("content") or item.get("text") or item.get("snippet")
                if isinstance(text, str) and text.strip():
                    results.append(text)
    return results


# === Cross-Repo Memory ===

_CROSS_REPO_MEMORY_PATHS = [
    ".agennext/memory.md",
    ".agennext/audit/index.ndjson",
]


def load_cross_repo_memory(
    workspace_root: Path,
    repo_name: str,
    query: str | None = None,
) -> list[RagSourceResult]:
    """Load memory from other repos in the workspace.
    
    Useful for cross-repo context and tribal knowledge.
    """
    results: list[RagSourceResult] = []
    if not workspace_root.exists():
        return results
    
    for other in workspace_root.iterdir():
        if not other.is_dir() or other.name == repo_name:
            continue
        if other.name.startswith("."):
            continue
        
        for mem_path in _CROSS_REPO_MEMORY_PATHS:
            mem_file = other / mem_path
            if not mem_file.exists():
                continue
            
            try:
                text = mem_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            
            # If query provided, filter entries
            if query and query.lower() not in text.lower():
                continue
            
            results.append(RagSourceResult(
                source=f"{other.name}/{mem_path}",
                content=text[:5000],  # Limit each to 5KB
            ))
    
    return results[:5]  # Max 5 cross-repo sources
