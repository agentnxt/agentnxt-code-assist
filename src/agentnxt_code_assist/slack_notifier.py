"""Optional Slack notification support."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from agentnxt_code_assist.schemas import AssistResult


@dataclass(frozen=True)
class SlackNotificationResult:
    sent: bool
    error: str | None = None


def notify_slack(webhook_url: str | None, result: AssistResult) -> SlackNotificationResult:
    if not webhook_url:
        return SlackNotificationResult(sent=False, error="Slack webhook URL is not configured")

    status = "passed" if result.ok else "needs attention"
    failed_checks = [check for check in result.checks if check.exit_code != 0]
    anomaly_count = len(result.anomalies)
    changed_count = len(result.changed_files)

    text = (
        f"AGenNext Code Assist run {status}\n"
        f"Repository: {result.repo_full_name or result.repo_path}\n"
        f"Branch: {result.work_branch or 'local checkout'}\n"
        f"Changed files: {changed_count}\n"
        f"Checks: {len(result.checks)} total, {len(failed_checks)} failed\n"
        f"Anomalies: {anomaly_count}\n"
        f"Pushed: {'yes' if result.pushed else 'no'}"
    )

    payload = {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*AGenNext Code Assist run {status}*"}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Repo:*\n{result.repo_full_name or result.repo_path}"},
                    {"type": "mrkdwn", "text": f"*Branch:*\n{result.work_branch or 'local checkout'}"},
                    {"type": "mrkdwn", "text": f"*Changed files:*\n{changed_count}"},
                    {"type": "mrkdwn", "text": f"*Failed checks:*\n{len(failed_checks)}"},
                    {"type": "mrkdwn", "text": f"*Anomalies:*\n{anomaly_count}"},
                    {"type": "mrkdwn", "text": f"*Pushed:*\n{'yes' if result.pushed else 'no'}"},
                ],
            },
        ],
    }

    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                return SlackNotificationResult(sent=False, error=f"Slack returned HTTP {response.status}")
            return SlackNotificationResult(sent=True)
    except urllib.error.URLError as exc:
        return SlackNotificationResult(sent=False, error=str(exc))
