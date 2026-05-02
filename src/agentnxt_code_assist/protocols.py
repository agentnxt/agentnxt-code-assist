from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProtocolBinding(BaseModel):
    enabled: bool = False
    required: bool = False
    provider: str | None = None
    endpoint_or_binding: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None
    security_requirements: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float | None = None
    fail_closed: bool = True


class ProtocolConfig(BaseModel):
    authzen: ProtocolBinding = Field(default_factory=ProtocolBinding)
    openfga: ProtocolBinding = Field(default_factory=ProtocolBinding)
    opa: ProtocolBinding = Field(default_factory=ProtocolBinding)
    agent_id: ProtocolBinding = Field(default_factory=ProtocolBinding)
    anp: ProtocolBinding = Field(default_factory=ProtocolBinding)
    acp: ProtocolBinding = Field(default_factory=ProtocolBinding)
    agent_client_protocol: ProtocolBinding = Field(default_factory=ProtocolBinding)
    a2a: ProtocolBinding = Field(default_factory=ProtocolBinding)


def build_openfga_metadata(subject: str, repo: str, branch: str, action: str) -> dict[str, Any]:
    return {
        "subject": subject,
        "resource": f"repository:{repo}",
        "branch": f"branch:{repo}#{branch}",
        "action": action,
        "relations": ["can_read", "can_run", "can_write", "can_commit", "can_push", "can_open_pr", "can_merge", "can_view_audit"],
    }


def build_opa_metadata(*, run_mode: str, base_branch: str, work_branch: str | None, update_mode: str, security_gate_status: str, audit_complete: bool) -> dict[str, Any]:
    return {
        "run_mode": run_mode,
        "base_branch": base_branch,
        "work_branch": work_branch,
        "requested_update_mode": update_mode,
        "allow_commits": False,
        "allow_push": False,
        "allow_pr": False,
        "allow_merge": False,
        "security_gate_status": security_gate_status,
        "audit_completion": audit_complete,
    }


def build_interop_metadata(agent_name: str, version: str, did: str | None, capabilities: list[str]) -> dict[str, Any]:
    return {
        "agent_name": agent_name,
        "display_name": "AGenNext Code Assist",
        "version": version,
        "agent_did": did,
        "capabilities": capabilities,
        "supported_actions": ["repo.read", "repo.propose_change", "repo.write"],
        "input_schema": "schemas/assist-request-v2",
        "output_schema": "schemas/assist-result-v2",
    }
