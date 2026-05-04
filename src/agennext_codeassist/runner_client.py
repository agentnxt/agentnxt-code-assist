from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RunnerConfig:
    url: str = ""
    api_key: str | None = None
    timeout_seconds: float = 30.0
    required: bool = False
    fail_closed: bool = True

    @classmethod
    def from_env(cls) -> "RunnerConfig":
        return cls(
            url=(os.getenv("AGNX_RUNNER_URL") or "").rstrip("/"),
            api_key=os.getenv("AGNX_RUNNER_API_KEY"),
            timeout_seconds=float(os.getenv("AGNX_RUNNER_TIMEOUT_SECONDS", "30")),
            required=_env_bool("AGNX_RUNNER_REQUIRED", False),
            fail_closed=_env_bool("AGNX_RUNNER_FAIL_CLOSED", True),
        )


@dataclass(frozen=True)
class RunnerDecision:
    allowed: bool
    capability_id: str | None = None
    reason: str | None = None
    expires_at: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class RunnerClient:
    def __init__(self, config: RunnerConfig | None = None) -> None:
        self.config = config or RunnerConfig.from_env()

    def request_capability(self, payload: dict[str, Any]) -> RunnerDecision:
        if not self.config.url:
            return self._unavailable("AGNX_RUNNER_URL is not configured")
        endpoint = f"{self.config.url}/v1/capabilities/request"
        headers = {"content-type": "application/json", "accept": "application/json"}
        if self.config.api_key:
            headers["authorization"] = f"Bearer {self.config.api_key}"
            headers["x-api-key"] = self.config.api_key
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except Exception as exc:
            return self._unavailable(f"Runner request failed: {exc}")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._unavailable("Runner returned non-JSON response")
        decision = normalize_runner_decision(data)
        if decision is None:
            return self._unavailable("Runner response did not contain recognizable decision")
        return decision

    def _unavailable(self, reason: str) -> RunnerDecision:
        if self.config.required or self.config.fail_closed:
            return RunnerDecision(allowed=False, reason=reason)
        return RunnerDecision(allowed=True, reason=f"{reason}; fail-open because runner is optional")


def normalize_runner_decision(payload: dict[str, Any]) -> RunnerDecision | None:
    candidate: Any = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    allowed = _extract_decision(candidate)
    if allowed is None:
        allowed = _extract_decision(payload)
    if allowed is None:
        return None
    source = candidate if isinstance(candidate, dict) else payload
    return RunnerDecision(
        allowed=allowed,
        capability_id=source.get("capability_id") if isinstance(source, dict) else None,
        reason=(source.get("reason") if isinstance(source, dict) else None),
        expires_at=(source.get("expires_at") if isinstance(source, dict) else None),
        constraints=(source.get("constraints") if isinstance(source, dict) and isinstance(source.get("constraints"), dict) else {}),
        raw=payload,
    )


def _extract_decision(payload: Any) -> bool | None:
    if not isinstance(payload, dict):
        return None
    for key in ("allowed", "allow", "decision"):
        value = payload.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"allow", "allowed", "true", "permit"}:
                return True
            if lowered in {"deny", "denied", "false", "forbid"}:
                return False
    return None
