# Generic OIDC Agent ID Protocol support

AGenNext Code Assist supports a provider-neutral Agent ID Protocol integration.

The integration is intentionally separate from login and authorization:

```text
OIDC                 -> authenticates the user/operator
Agent ID Protocol    -> enriches runs with agent DID, delegation, governance, and binding metadata
AuthZEN/OpenFGA/OPA  -> authorizes and evaluates policy decisions
Code Assist          -> enforces decisions and records context
```

Any Agent ID-compatible registry/control plane can be used. The registry should expose Agent ID records over HTTP.

## Environment variables

Preferred names:

```env
AGENT_ID_ENABLED=false
AGENT_ID_REQUIRED=false
AGENT_ID_REGISTRY_URL=https://agent-id.example.com
AGENT_ID_API_KEY=
AGENT_ID_BEARER_TOKEN=
AGENT_ID_RECORD_ID=
AGENT_ID_DID=
AGENT_ID_TIMEOUT_SECONDS=10
AGENT_ID_FAIL_CLOSED=false
```

Backward-compatible aliases are also accepted:

```env
AGENT_DID_ENABLED=false
AGENT_DID_REQUIRED=false
AGENT_DID_REGISTRY_URL=
AGENT_DID_API_KEY=
AGENT_DID_BEARER_TOKEN=
AGENT_DID_RECORD_ID=
AGENT_DID_VALUE=
AGENT_DID_FAIL_CLOSED=false
```

## Behavior

```text
AGENT_ID_ENABLED=false
  -> no Agent ID lookup; OIDC/login can still work normally.

AGENT_ID_ENABLED=true + AGENT_ID_REQUIRED=false
  -> attempt to resolve Agent ID context; warn/continue if unavailable.

AGENT_ID_ENABLED=true + AGENT_ID_REQUIRED=true
  -> fail governed agent operations if Agent ID context cannot be resolved.
```

## Expected registry endpoints

The generic client expects these endpoint shapes:

```text
GET /v1/agent-records/{record_id}
GET /v1/agent-records/by-did/{did}
```

Authentication can use either:

```text
X-API-Key: <AGENT_ID_API_KEY>
Authorization: Bearer <AGENT_ID_BEARER_TOKEN>
```

## Supported record shape

The adapter supports the Agent ID Protocol style envelope:

```yaml
agent_id_protocol_version: "0.2.0"
agent:
  did: did:web:example.com:agents:code-assist
  display_name: AGenNext Code Assist
  owner: AGenNext
  role: code-assist
  environment: production
  version: 1.0.0
  status: active
  trust_level: internal
  capabilities:
    - repo.read
    - repo.write
    - checks.run
authorization:
  mode: hybrid
  subject_context: on_behalf_of_user
  delegation_proof_formats:
    - oidc_identity_assertion
  scope_reference: agennext:code-assist:default
  expires_at: null
  max_delegation_depth: 1
  attenuation_required: true
  human_approval_required: true
governance:
  provisioning: internal_iam
  audit_endpoint: https://agent-id.example.com/v1/audit-events
  status_endpoint: https://agent-id.example.com/v1/agent-records/by-did/did:web:example.com:agents:code-assist
  deprovisioning_endpoint: https://agent-id.example.com/v1/agent-records/deprovision
  identity_chain_preserved: true
bindings:
  a2a:
    endpoint_url: https://example.com/a2a
  acp:
    endpoint_url: https://example.com/acp
  anp:
    did: did:web:example.com:agents:code-assist
    endpoint_url: https://example.com/anp/message
```

The client also accepts wrapped responses such as:

```json
{ "record": { } }
{ "agent_record": { } }
{ "data": { } }
```

## What Code Assist should use from Agent ID

Code Assist should consume Agent ID context for:

```text
agent DID
agent display name
owner/team
role
environment
status
trust level
capabilities
authorization mode
subject context
delegation proof formats
scope reference
human approval requirement
audit endpoint
status endpoint
deprovision endpoint
A2A/ACP/ANP bindings
```

## What Agent ID should not replace

Agent ID does not replace:

```text
OIDC login
AuthZEN authorization decisions
OpenFGA/ReBAC relationship checks
OPA policy decisions
security/vulnerability gates
Code Assist local guardrails
```

## Recommended combined flow

```text
1. Authenticate operator through OIDC.
2. Resolve optional Agent ID context for the Code Assist agent.
3. Send subject + action + resource + Agent ID context to AuthZEN-compatible authorization backend.
4. Run Code Assist only if authorization and local guardrails allow.
5. Record Agent ID context in audit/change logs when safe.
```

## Production rule

```text
If AGENT_ID_REQUIRED=true and no valid Agent ID record is found, fail closed.
If AGENT_ID_REQUIRED=false and lookup fails, warn and continue.
Never persist Agent ID API keys or bearer tokens into logs, memory, prompts, or audit traces.
```
