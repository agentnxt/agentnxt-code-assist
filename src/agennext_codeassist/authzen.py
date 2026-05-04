"""Generic AuthZEN authorization adapter.

This module provides provider-neutral authorization support for AGenNext Code
Assist. It does not depend on CaaS, OpenFGA, OPA, Logto, or any specific
vendor. Any authorization service that exposes an AuthZEN-style access
evaluation endpoint can be used.

Code Assist responsibility:
- build a normalized access evaluation request
- call the configured AuthZEN endpoint
- enforce the returned allow/deny decision

Authentication remains separate and should be handled by OIDC or another
configured auth provider.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


DEFAULT_AUTHZEN_EVALUATION_PATH = "/access/v1/evaluation"


@dataclass(frozen=True)
class AuthZenEntity:
    """AuthZEN-style entity for subject, action, or resource."""

    type: str | None = None
    id: str | None = None
    name: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.type:
            payload["type"] = self.type
        if self.id:
            payload["id"] = self.id
        if self.name:
            payload["name"] = self.name
        if self.properties:
            payload["properties"] = self.properties
        return payload


@dataclass(frozen=True)
class AuthZenEvaluationRequest:
    """Access evaluation request."""

    subject: AuthZenEntity
    action: AuthZenEntity
    resource: AuthZenEntity
    context: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "subject": self.subject.to_payload(),
            "action": self.action.to_payload(),
            "resource": self.resource.to_payload(),
        }
        if self.context:
            payload["context"] = self.context
        return payload


@dataclass(frozen=True)
class AuthZenDecision:
    """Normalized authorization decision."""

    allowed: bool
    reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthZenConfig:
    enabled: bool = False
    required: bool = False
    api_url: str = ""
    evaluation_path: str = DEFAULT_AUTHZEN_EVALUATION_PATH
    api_key: str | None = None
    bearer_token: str | None = None
    timeout_seconds: float = 10.0
    fail_closed: bool = True

    @classmethod
    def from_env(cls) -> "AuthZenConfig":
        provider = os.getenv("AUTHZ_PROVIDER", "").strip().lower()
        enabled = _env_bool("AUTHZEN_ENABLED", provider == "authzen")
        return cls(
            enabled=enabled,
            required=_env_bool("AUTHZ_REQUIRED", enabled),
            api_url=_trim_slash(os.getenv("AUTHZEN_API_URL", "")),
            evaluation_path=os.getenv("AUTHZEN_EVALUATION_PATH", DEFAULT_AUTHZEN_EVALUATION_PATH),
            api_key=os.getenv("AUTHZEN_API_KEY"),
            bearer_token=os.getenv("AUTHZEN_BEARER_TOKEN"),
            timeout_seconds=float(os.getenv("AUTHZEN_TIMEOUT_SECONDS", "10")),
            fail_closed=_env_bool("AUTHZEN_FAIL_CLOSED", _env_bool("AUTHZ_FAIL_CLOSED", True)),
        )


class AuthZenClient:
    """HTTP client for AuthZEN access evaluation."""

    def __init__(self, config: AuthZenConfig | None = None) -> None:
        self.config = config or AuthZenConfig.from_env()

    def evaluate(self, request: AuthZenEvaluationRequest) -> AuthZenDecision:
        if not self.config.enabled:
            return AuthZenDecision(allowed=True, reason="AuthZEN disabled", raw={"skipped": True})
        if not self.config.api_url:
            return self._unavailable("AUTHZEN_API_URL is not configured")

        endpoint = self.config.api_url + _ensure_leading_slash(self.config.evaluation_path)
        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "agennext-code-assist/authzen",
        }
        if self.config.bearer_token:
            headers["authorization"] = f"Bearer {self.config.bearer_token}"
        elif self.config.api_key:
            headers["authorization"] = f"Bearer {self.config.api_key}"
            headers["x-api-key"] = self.config.api_key

        http_request = urllib.request.Request(
            endpoint,
            data=json.dumps(request.to_payload()).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return self._unavailable(f"AuthZEN HTTP {exc.code}: {response_body[:500]}")
        except urllib.error.URLError as exc:
            return self._unavailable(f"AuthZEN request failed: {exc.reason}")
        except TimeoutError:
            return self._unavailable("AuthZEN request timed out")

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._unavailable("AuthZEN returned non-JSON response")

        return normalize_authzen_decision(payload)

    def _unavailable(self, reason: str) -> AuthZenDecision:
        if self.config.required or self.config.fail_closed:
            return AuthZenDecision(allowed=False, reason=reason)
        return AuthZenDecision(allowed=True, reason=f"{reason}; fail-open because AuthZEN is not required")


def build_code_assist_authzen_request(
    *,
    subject_id: str,
    action: str,
    repo_full_name: str,
    branch: str | None = None,
    base_branch: str | None = None,
    mode: str = "production",
    run_id: str | None = None,
    agent_did: str | None = None,
    context: dict[str, Any] | None = None,
) -> AuthZenEvaluationRequest:
    """Build a standard Code Assist AuthZEN request."""

    merged_context: dict[str, Any] = {
        "service": "agennext-code-assist",
        "mode": mode,
    }
    if branch:
        merged_context["branch"] = branch
    if base_branch:
        merged_context["base_branch"] = base_branch
    if run_id:
        merged_context["run_id"] = run_id
    if agent_did:
        merged_context["agent_did"] = agent_did
    if context:
        merged_context.update(context)

    return AuthZenEvaluationRequest(
        subject=AuthZenEntity(type="user_or_agent", id=subject_id),
        action=AuthZenEntity(name=action),
        resource=AuthZenEntity(
            type="repository",
            id=repo_full_name,
            properties={key: value for key, value in {"branch": branch, "base_branch": base_branch}.items() if value},
        ),
        context=merged_context,
    )


def normalize_authzen_decision(payload: dict[str, Any]) -> AuthZenDecision:
    """Normalize common AuthZEN decision response shapes."""

    candidate: Any = payload
    if isinstance(payload.get("result"), dict):
        candidate = payload["result"]
    elif "result" in payload:
        candidate = payload["result"]

    if isinstance(candidate, bool):
        return AuthZenDecision(allowed=candidate, raw=payload)

    if isinstance(candidate, dict):
        decision = _extract_decision(candidate)
        if decision is not None:
            return AuthZenDecision(allowed=decision, reason=_reason(candidate), raw=payload)

    decision = _extract_decision(payload)
    if decision is not None:
        return AuthZenDecision(allowed=decision, reason=_reason(payload), raw=payload)

    return AuthZenDecision(
        allowed=False,
        reason="AuthZEN response did not contain a recognizable decision",
        raw=payload,
    )


def _extract_decision(payload: dict[str, Any]) -> bool | None:
    for key in ("decision", "allowed", "allow"):
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.lower()
            if lowered in {"allow", "allowed", "permit", "true"}:
                return True
            if lowered in {"deny", "denied", "forbid", "false"}:
                return False
    return None


def _reason(payload: dict[str, Any]) -> str | None:
    for key in ("reason", "message", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    reasons = payload.get("reasons")
    if isinstance(reasons, list) and reasons:
        return "; ".join(str(item) for item in reasons[:5])
    return None


def _trim_slash(value: str) -> str:
    return value.rstrip("/")


def _ensure_leading_slash(value: str) -> str:
    return value if value.startswith("/") else f"/{value}"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
