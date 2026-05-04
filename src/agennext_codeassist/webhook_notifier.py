"""Optional generic webhook notification support."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from agennext_codeassist.schemas import AssistResult


@dataclass(frozen=True)
class WebhookNotificationResult:
    sent: bool
    error: str | None = None


def notify_webhook(webhook_url: str | None, result: AssistResult) -> WebhookNotificationResult:
    if not webhook_url:
        return WebhookNotificationResult(sent=False, error="Webhook URL is not configured")

    payload = {
        "event": "agennext_code_assist.run.completed",
        "ok": result.ok,
        "repo_path": result.repo_path,
        "repo_full_name": result.repo_full_name,
        "target_url": result.target_url,
        "target_kind": result.target_kind,
        "base_branch": result.base_branch,
        "work_branch": result.work_branch,
        "before_sha": result.before_sha,
        "after_sha": result.after_sha,
        "changed_files": result.changed_files,
        "checks": [check.model_dump() for check in result.checks],
        "anomalies": [anomaly.model_dump() for anomaly in result.anomalies],
        "pushed": result.pushed,
        "error": result.error,
        "change_log_path": result.change_log_path,
        "slack": result.slack.model_dump() if result.slack else None,
    }

    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "agennext-code-assist"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                return WebhookNotificationResult(sent=False, error=f"Webhook returned HTTP {response.status}")
            return WebhookNotificationResult(sent=True)
    except urllib.error.URLError as exc:
        return WebhookNotificationResult(sent=False, error=str(exc))
