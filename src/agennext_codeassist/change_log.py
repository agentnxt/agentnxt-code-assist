"""Per-run change log generation for Code Assist."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from agennext_codeassist.schemas import CheckResult, RepoAnomalyResult


def build_change_log(
    *,
    objective: str,
    repo_full_name: str | None,
    target_url: str | None,
    target_kind: str | None,
    base_branch: str | None,
    work_branch: str | None,
    before_sha: str | None,
    after_sha: str | None,
    changed_files: list[str],
    checks: list[CheckResult],
    anomalies: list[RepoAnomalyResult],
    error: str | None,
    pushed: bool,
) -> str:
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        f"## Code Assist Run — {timestamp}",
        "",
        "### Objective",
        objective.strip(),
        "",
        "### Target",
        f"- Repository: {repo_full_name or 'local checkout'}",
        f"- Target URL: {target_url or 'not provided'}",
        f"- Target kind: {target_kind or 'local'}",
        f"- Base branch: {base_branch or 'not managed'}",
        f"- Work branch: {work_branch or 'not managed'}",
        f"- Before SHA: {before_sha or 'unknown'}",
        f"- After SHA: {after_sha or 'unknown'}",
        "",
        "### Actions taken",
    ]

    if changed_files:
        lines.append("- Updated files:")
        lines.extend(f"  - `{path}`" for path in changed_files)
    else:
        lines.append("- No file changes detected.")

    lines.append(f"- Pushed branch: {'yes' if pushed else 'no'}")
    lines.append("- Merge: not performed by Code Assist")
    lines.append("")

    lines.append("### Validation and checks")
    if checks:
        for check in checks:
            status = "passed" if check.exit_code == 0 else "failed"
            lines.append(f"- `{check.command}`: {status} (exit {check.exit_code})")
    else:
        lines.append("- No checks were run.")
    lines.append("")

    lines.append("### Anomalies and risks")
    if anomalies:
        for anomaly in anomalies:
            evidence = f" Evidence: {anomaly.evidence}" if anomaly.evidence else ""
            lines.append(f"- [{anomaly.severity}] {anomaly.code}: {anomaly.message}{evidence}")
    else:
        lines.append("- No anomalies were reported by Code Assist.")
    lines.append("")

    lines.append("### Result")
    if error:
        lines.append(f"- Status: failed or needs attention — {error}")
    else:
        failed_checks = [check for check in checks if check.exit_code != 0]
        if failed_checks:
            lines.append("- Status: needs attention — one or more checks failed.")
        else:
            lines.append("- Status: completed locally. Review diff before commit/push/PR.")
    lines.append("")

    lines.append("### Next steps")
    if anomalies:
        lines.append("- Review and resolve reported anomalies before publishing or merging.")
    failed_checks = [check for check in checks if check.exit_code != 0]
    if failed_checks:
        lines.append("- Fix failing checks and rerun validation.")
    if changed_files:
        lines.append("- Review `git diff` for all changed files.")
        lines.append("- Commit, push, or open a PR only after explicit human authorization.")
    else:
        lines.append("- Refine the instruction or file list if code changes were expected.")
    lines.append("- Code Assist must not merge changes; merge requires external human approval.")
    lines.append("")

    return "\n".join(lines).strip() + "\n"


def append_change_log(repo_path: Path, relative_path: str, entry: str) -> Path:
    output_path = (repo_path / relative_path).resolve()
    if not output_path.is_relative_to(repo_path):
        raise ValueError(f"change_log_path escapes repo: {relative_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    previous = output_path.read_text(encoding="utf-8") if output_path.exists() else "# Code Assist Change Log\n\n"
    output_path.write_text(previous.rstrip() + "\n\n" + entry, encoding="utf-8")
    return output_path
