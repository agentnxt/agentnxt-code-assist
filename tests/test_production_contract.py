from agennext_codeassist.authzen import normalize_authzen_decision
from agennext_codeassist.agent_id_protocol import parse_agent_id_record
from agennext_codeassist.protocols import ProtocolConfig, build_interop_metadata, build_openfga_metadata, build_opa_metadata
from agennext_codeassist.runner_client import normalize_runner_decision
from agennext_codeassist.schemas import AssistRequest


def test_authzen_normalization():
    assert normalize_authzen_decision({"decision": "allow"}).allowed
    assert not normalize_authzen_decision({"result": {"allowed": False}}).allowed


def test_agent_id_parse():
    rec = parse_agent_id_record({"agent": {"did": "did:web:example.com:agents:code-assist"}})
    assert rec.agent.did.startswith("did:web")


def test_runner_normalization():
    assert normalize_runner_decision({"allow": True}).allowed
    assert not normalize_runner_decision({"result": {"decision": "deny"}}).allowed


def test_protocol_config_and_metadata():
    cfg = ProtocolConfig()
    assert not cfg.authzen.enabled
    assert build_openfga_metadata("agent:did:x", "AGenNext/CodeAssist", "main", "repo.write")["resource"].startswith("repository:")
    assert build_opa_metadata(run_mode="dry_run", base_branch="main", work_branch=None, update_mode="local", security_gate_status="skipped", audit_complete=False)["run_mode"] == "dry_run"
    assert build_interop_metadata("agennext-code-assist", "1.0", None, ["repo.write"])["agent_name"] == "agennext-code-assist"


def test_run_mode_validation():
    req = AssistRequest(instruction="x", repo_path=".", run_mode="dry_run")
    assert req.run_mode == "dry_run"
