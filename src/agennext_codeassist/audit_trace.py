from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_audit_trace(repo_path: Path, run_id: str, trace: dict[str, Any]) -> tuple[str, str]:
    root = repo_path / ".agennext" / "audit"
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    started = trace.get("timestamp_start") or datetime.now(UTC).isoformat()
    ended = datetime.now(UTC).isoformat()
    trace = {**trace, "run_id": run_id, "timestamp_start": started, "timestamp_end": ended}
    json_path = runs / f"{run_id}.json"
    md_path = runs / f"{run_id}.md"
    json_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(trace), encoding="utf-8")
    with (root / "index.ndjson").open("a", encoding="utf-8") as fp:
        fp.write(json.dumps({"run_id": run_id, "timestamp_end": ended, "result": trace.get("result")}) + "\n")
    return str(json_path.relative_to(repo_path)), str(md_path.relative_to(repo_path))


def _to_markdown(trace: dict[str, Any]) -> str:
    return "\n".join([
        f"# Audit Trace {trace.get('run_id','')}",
        f"- run_mode: {trace.get('run_mode')}",
        f"- result: {trace.get('result')}",
        f"- repo_target: {trace.get('repo_target')}",
        f"- base_branch: {trace.get('base_branch')}",
        f"- work_branch: {trace.get('work_branch')}",
    ]) + "\n"
