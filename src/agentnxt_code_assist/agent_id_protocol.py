"""Generic OIDC Agent ID Protocol support.

This module provides provider-neutral support for resolving an Agent ID record
that follows the OIDC + W3C DID style Agent ID Protocol shape.

It intentionally does not depend on a specific Agent DID implementation. Any
Agent ID-compatible control plane can expose compatible JSON over HTTP.

Responsibilities:
- discover/load an agent identity record
- normalize DID, authorization, governance, and protocol binding metadata
- provide prompt/audit-safe context for Code Assist runs

Authentication remains separate and can be handled by any OIDC provider.
Authorization remains separate and can be handled by AuthZEN/OpenFGA/OPA/etc.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentIdentity:
    did: str
    display_name: str | None = None
    owner: str | None = None
    role: str | None = None
    environment: str | None = None
    version: str | None = None
    status: str | None = None
    trust_level: str | None = None
    capabilities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentAuthorization:
    mode: str | None = None
    subject_context: str | None = None
    delegation_proof_formats: list[str] = field(default_factory=list)
    scope_reference: str | None = None
    expires_at: str | None = None
    max_delegation_depth: int | None = None
    attenuation_required: bool | None = None
    human_approval_required: bool | None = None


@dataclass(frozen=True)
class AgentGovernance:
    provisioning: str | None = None
    audit_endpoint: str | None = None
    status_endpoint: str | None = None
    deprovisioning_endpoint: str | None = None
    identity_chain_preserved: bool | None = None


@dataclass(frozen=True)
class AgentBindings:
    a2a: dict[str, Any] = field(default_factory=dict)
    acp: dict[str, Any] = field(default_factory=dict)
    anp: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentIdRecord:
    protocol_version: str | None
    agent: AgentIdentity
    authorization: AgentAuthorization = field(default_factory=AgentAuthorization)
    governance: AgentGovernance = field(default_factory=AgentGovernance)
    bindings: AgentBindings = field(default_factory=AgentBindings)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_audit_context(self) -> dict[str, Any]:
        """Return sanitized identity/governance metadata safe for audit logs."""
        return {
            "agent_id_protocol_version": self.protocol_version,
            "agent": {
                "did": self.agent.did,
                "display_name": self.agent.display_name,
                "owner": self.agent.owner,
                "role": self.agent.role,
                "environment": self.agent.environment,
                "version": self.agent.version,
                "status": self.agent.status,
                "trust_level": self.agent.trust_level,
                "capabilities": self.agent.capabilities,
            },
            "authorization": {
                "mode": self.authorization.mode,
                "subject_context": self.authorization.subject_context,
                "delegation_proof_formats": self.authorization.delegation_proof_formats,
                "scope_reference": self.authorization.scope_reference,
                "expires_at": self.authorization.expires_at,
                "max_delegation_depth": self.authorization.max_delegation_depth,
                "attenuation_required": self.authorization.attenuation_required,
                "human_approval_required": self.authorization.human_approval_required,
            },
            "governance": {
                "provisioning": self.governance.provisioning,
                "audit_endpoint": self.governance.audit_endpoint,
                "status_endpoint": self.governance.status_endpoint,
                "deprovisioning_endpoint": self.governance.deprovisioning_endpoint,
                "identity_chain_preserved": self.governance.identity_chain_preserved,
            },
            "bindings": {
                "a2a": self.bindings.a2a,
                "acp": self.bindings.acp,
                "anp": self.bindings.anp,
            },
        }

    def to_prompt_block(self) -> str:
        """Return concise run context for model prompts."""
        lines = [
            "## Agent ID Protocol context",
            f"- DID: {self.agent.did}",
        ]
        optional = {
            "Display name": self.agent.display_name,
            "Owner": self.agent.owner,
            "Role": self.agent.role,
            "Environment": self.agent.environment,
            "Status": self.agent.status,
            "Trust level": self.agent.trust_level,
            "Authorization mode": self.authorization.mode,
            "Subject context": self.authorization.subject_context,
            "Scope reference": self.authorization.scope_reference,
        }
        for label, value in optional.items():
            if value:
                lines.append(f"- {label}: {value}")
        if self.agent.capabilities:
            lines.append("- Capabilities: " + ", ".join(self.agent.capabilities))
        if self.authorization.human_approval_required is not None:
            lines.append(f"- Human approval required: {self.authorization.human_approval_required}")
        if self.governance.audit_endpoint:
            lines.append(f"- Audit endpoint: {self.governance.audit_endpoint}")
        if self.governance.status_endpoint:
            lines.append(f"- Status endpoint: {self.governance.status_endpoint}")
        return "\n".join(lines)


@dataclass(frozen=True)
class AgentIdConfig:
    enabled: bool = False
    required: bool = False
    registry_url: str = ""
    record_id: str | None = None
    did: str | None = None
    api_key: str | None = None
    bearer_token: str | None = None
    timeout_seconds: float = 10.0
    fail_closed: bool = False

    @classmethod
    def from_env(cls) -> "AgentIdConfig":
        return cls(
            enabled=_env_bool("AGENT_ID_ENABLED", _env_bool("AGENT_DID_ENABLED", False)),
            required=_env_bool("AGENT_ID_REQUIRED", _env_bool("AGENT_DID_REQUIRED", False)),
            registry_url=_trim_slash(os.getenv("AGENT_ID_REGISTRY_URL") or os.getenv("AGENT_DID_REGISTRY_URL") or ""),
            record_id=os.getenv("AGENT_ID_RECORD_ID") or os.getenv("AGENT_DID_RECORD_ID"),
            did=os.getenv("AGENT_ID_DID") or os.getenv("AGENT_DID_VALUE"),
            api_key=os.getenv("AGENT_ID_API_KEY") or os.getenv("AGENT_DID_API_KEY"),
            bearer_token=os.getenv("AGENT_ID_BEARER_TOKEN") or os.getenv("AGENT_DID_BEARER_TOKEN"),
            timeout_seconds=float(os.getenv("AGENT_ID_TIMEOUT_SECONDS", "10")),
            fail_closed=_env_bool("AGENT_ID_FAIL_CLOSED", _env_bool("AGENT_DID_FAIL_CLOSED", False)),
        )


class AgentIdClient:
    """HTTP client for an Agent ID-compatible registry/control plane."""

    def __init__(self, config: AgentIdConfig | None = None) -> None:
        self.config = config or AgentIdConfig.from_env()

    def resolve(self) -> AgentIdRecord | None:
        if not self.config.enabled:
            return None
        if not self.config.registry_url:
            return self._handle_unavailable("AGENT_ID_REGISTRY_URL is not configured")
        if self.config.record_id:
            return self.resolve_by_record_id(self.config.record_id)
        if self.config.did:
            return self.resolve_by_did(self.config.did)
        return self._handle_unavailable("AGENT_ID_RECORD_ID or AGENT_ID_DID is required when Agent ID is enabled")

    def resolve_by_record_id(self, record_id: str) -> AgentIdRecord | None:
        encoded = urllib.parse.quote(record_id, safe="")
        return self._get_record(f"/v1/agent-records/{encoded}")

    def resolve_by_did(self, did: str) -> AgentIdRecord | None:
        encoded = urllib.parse.quote(did, safe="")
        return self._get_record(f"/v1/agent-records/by-did/{encoded}")

    def _get_record(self, path: str) -> AgentIdRecord | None:
        endpoint = self.config.registry_url + path
        headers = {
            "accept": "application/json",
            "user-agent": "agennext-code-assist/agent-id-protocol",
        }
        if self.config.bearer_token:
            headers["authorization"] = f"Bearer {self.config.bearer_token}"
        elif self.config.api_key:
            headers["x-api-key"] = self.config.api_key

        request = urllib.request.Request(endpoint, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            return self._handle_unavailable(f"Agent ID HTTP {exc.code}: {response_body[:500]}")
        except urllib.error.URLError as exc:
            return self._handle_unavailable(f"Agent ID request failed: {exc.reason}")
        except TimeoutError:
            return self._handle_unavailable("Agent ID request timed out")

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self._handle_unavailable("Agent ID registry returned non-JSON response")
        return parse_agent_id_record(payload)

    def _handle_unavailable(self, reason: str) -> None:
        if self.config.required or self.config.fail_closed:
            raise RuntimeError(reason)
        return None


def parse_agent_id_record(payload: dict[str, Any]) -> AgentIdRecord:
    """Parse a protocol record from a registry payload.

    Accepts both direct protocol records and wrapper payloads such as
    {"record": {...}} or {"agent_record": {...}}.
    """

    record = _unwrap_record(payload)
    agent = record.get("agent") or {}
    authorization = record.get("authorization") or {}
    governance = record.get("governance") or {}
    bindings = record.get("bindings") or {}

    did = _string(agent.get("did") or record.get("did"))
    if not did:
        raise ValueError("Agent ID record is missing agent.did")

    return AgentIdRecord(
        protocol_version=_string(record.get("agent_id_protocol_version") or record.get("protocol_version")),
        agent=AgentIdentity(
            did=did,
            display_name=_string(agent.get("display_name")),
            owner=_string(agent.get("owner")),
            role=_string(agent.get("role")),
            environment=_string(agent.get("environment")),
            version=_string(agent.get("version")),
            status=_string(agent.get("status")),
            trust_level=_string(agent.get("trust_level")),
            capabilities=_string_list(agent.get("capabilities")),
        ),
        authorization=AgentAuthorization(
            mode=_string(authorization.get("mode")),
            subject_context=_string(authorization.get("subject_context")),
            delegation_proof_formats=_string_list(authorization.get("delegation_proof_formats")),
            scope_reference=_string(authorization.get("scope_reference")),
            expires_at=_string(authorization.get("expires_at")),
            max_delegation_depth=_optional_int(authorization.get("max_delegation_depth")),
            attenuation_required=_optional_bool(authorization.get("attenuation_required")),
            human_approval_required=_optional_bool(authorization.get("human_approval_required")),
        ),
        governance=AgentGovernance(
            provisioning=_string(governance.get("provisioning")),
            audit_endpoint=_string(governance.get("audit_endpoint")),
            status_endpoint=_string(governance.get("status_endpoint")),
            deprovisioning_endpoint=_string(governance.get("deprovisioning_endpoint")),
            identity_chain_preserved=_optional_bool(governance.get("identity_chain_preserved")),
        ),
        bindings=AgentBindings(
            a2a=_dict(bindings.get("a2a")),
            acp=_dict(bindings.get("acp")),
            anp=_dict(bindings.get("anp")),
        ),
        raw=record,
    )


def _unwrap_record(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("record", "agent_record", "agentIdRecord", "data"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _trim_slash(value: str) -> str:
    return value.rstrip("/")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
