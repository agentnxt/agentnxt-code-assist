"""Optional SMTP email notification support."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from urllib.parse import parse_qs, unquote, urlparse

from agennext_codeassist.schemas import AssistResult


@dataclass(frozen=True)
class EmailNotificationResult:
    sent: bool
    error: str | None = None


def notify_email(
    *,
    smtp_url: str | None,
    from_email: str,
    to_email: str | None,
    result: AssistResult,
) -> EmailNotificationResult:
    if not smtp_url:
        return EmailNotificationResult(sent=False, error="SMTP URL is not configured")
    if not to_email:
        return EmailNotificationResult(sent=False, error="SMTP recipient email is not configured")

    try:
        settings = _parse_smtp_url(smtp_url)
        message = EmailMessage()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = _subject(result)
        message.set_content(_body(result))

        if settings["scheme"] == "smtps":
            client: smtplib.SMTP = smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=15)
        else:
            client = smtplib.SMTP(settings["host"], settings["port"], timeout=15)
        try:
            if settings["scheme"] == "smtp" and settings["starttls"]:
                client.starttls()
            if settings["username"]:
                client.login(settings["username"], settings["password"] or "")
            client.send_message(message)
        finally:
            client.quit()
        return EmailNotificationResult(sent=True)
    except Exception as exc:
        return EmailNotificationResult(sent=False, error=str(exc))


def _subject(result: AssistResult) -> str:
    status = "passed" if result.ok else "needs attention"
    repo = result.repo_full_name or result.repo_path
    return f"AGenNext Code Assist run {status}: {repo}"


def _body(result: AssistResult) -> str:
    failed_checks = [check for check in result.checks if check.exit_code != 0]
    lines = [
        f"Status: {'passed' if result.ok else 'needs attention'}",
        f"Repository: {result.repo_full_name or result.repo_path}",
        f"Target URL: {result.target_url or 'not provided'}",
        f"Branch: {result.work_branch or 'local checkout'}",
        f"Changed files: {len(result.changed_files)}",
        f"Checks: {len(result.checks)} total, {len(failed_checks)} failed",
        f"Anomalies: {len(result.anomalies)}",
        f"Pushed: {'yes' if result.pushed else 'no'}",
        f"Error: {result.error or 'none'}",
        "",
        "Changed files:",
    ]
    lines.extend(f"- {path}" for path in result.changed_files) or lines.append("- none")
    lines.append("")
    lines.append("Checks:")
    if result.checks:
        lines.extend(f"- {check.command}: exit {check.exit_code}" for check in result.checks)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Anomalies:")
    if result.anomalies:
        lines.extend(f"- [{item.severity}] {item.code}: {item.message}" for item in result.anomalies)
    else:
        lines.append("- none")
    if result.change_log:
        lines.extend(["", "Change log:", result.change_log])
    return "\n".join(lines)


def _parse_smtp_url(smtp_url: str) -> dict[str, object]:
    parsed = urlparse(smtp_url)
    if parsed.scheme not in {"smtp", "smtps"}:
        raise ValueError("SMTP URL must use smtp:// or smtps://")
    if not parsed.hostname:
        raise ValueError("SMTP URL must include a host")
    query = parse_qs(parsed.query)
    default_port = 465 if parsed.scheme == "smtps" else 587
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": parsed.port or default_port,
        "username": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "starttls": query.get("starttls", ["true"])[0].lower() in {"1", "true", "yes", "on"},
    }
