# AGenNext Runner enforcement architecture

AGenNext Code Assist is an agent. It must not be treated as the ultimate policy enforcement point.

**AGenNext Runner is the runtime enforcement point.**

## Correct responsibility split

```text
User / Operator
  -> authenticates with OIDC
  -> gives intent and explicit authorization flags

AGenNext Code Assist Agent
  -> proposes and prepares actions
  -> requests capabilities from AGenNext Runner
  -> never self-authorizes privileged actions

Agent ID Protocol
  -> provides optional agent identity, DID, delegation, and governance context

AuthZEN-compatible Authorization Service
  -> evaluates access request
  -> can be backed by CAAS, OpenFGA, OPA, SpiceDB, or another policy engine
  -> returns allow / deny / reason

AGenNext Runner
  -> runtime enforcement point
  -> blocks or allows tool execution
  -> owns fail-closed behavior
  -> owns scoped execution capabilities
  -> controls GitHub API / Git CLI access
  -> records or forwards audit evidence

GitHub API / Git CLI / Sandbox
  -> performs the actual repository operation only after AGenNext Runner allows it
```

## Roles

| Component | Role |
|---|---|
| Code Assist | Agent / requester / planner |
| AGenNext Runner | Runtime / policy enforcement point |
| OIDC provider | Authentication provider |
| Agent ID registry | Agent identity and governance context provider |
| AuthZEN service | Policy decision point |
| GitHub API / Git CLI | Resource operation backend controlled by Runner |
| Audit service | Evidence and trace ledger |

## Design rule

Code Assist may build authorization requests and propose changes, but it must not be trusted to enforce its own permissions.

The enforcement boundary is **AGenNext Runner**.

Runner should own:

```text
- GitHub write tokens / app credentials
- Git CLI worktree permissions
- filesystem write permissions
- network/tool permissions
- sandbox lifecycle
- short-lived scoped capabilities
- fail-closed behavior
- audit trace capture or audit forwarding
```

## AuthZEN request flow

```text
1. Code Assist receives user intent.
2. Code Assist identifies desired action: run, write, commit, push, open_pr, notify, etc.
3. Code Assist requests a scoped capability from AGenNext Runner.
4. AGenNext Runner builds/sends subject/action/resource/context to an AuthZEN-compatible service.
5. AuthZEN-compatible service returns allow/deny and reason.
6. AGenNext Runner enforces the decision.
7. If allowed, AGenNext Runner performs or grants the operation through GitHub API or Git CLI.
8. Audit service records the request, decision, operation, and result.
```

## Capability request shape

Code Assist should ask Runner for capabilities, not directly execute privileged operations.

Example:

```json
{
  "agent": "agennext-code-assist",
  "action": "repo.write",
  "resource": "repository:AGenNext/CodeAssist",
  "branch": "code-assist/example",
  "reason": "implement requested code change",
  "requested_update_mode": "github-api",
  "context": {
    "run_id": "...",
    "agent_did": "did:web:example.com:agents:code-assist"
  }
}
```

Runner returns a decision/capability result:

```json
{
  "allowed": true,
  "capability_id": "cap_...",
  "expires_at": "2026-05-02T04:00:00Z",
  "constraints": {
    "repo": "AGenNext/CodeAssist",
    "branch": "code-assist/example",
    "update_mode": "github-api",
    "max_operations": 10
  }
}
```

## Fail-closed rule

In production:

```text
AuthZEN unavailable = Runner denies
Agent required but Agent ID unavailable = Runner denies
Audit trace unavailable = Runner denies
Security gate unavailable = Runner denies when required
Unknown update path = Runner denies
Code Assist self-approval = Runner denies
Expired capability = Runner denies
Capability constraint mismatch = Runner denies
```

## What Code Assist can do

Code Assist can:

- describe the requested action
- build an AuthZEN-compatible access evaluation request shape for Runner
- attach OIDC subject context when supplied by Runner/session
- attach Agent ID context when available
- propose code changes
- request tool execution from AGenNext Runner
- report policy decision results to the user
- include sanitized policy context in change logs

## What Code Assist must not do

Code Assist must not:

- self-authorize privileged actions
- bypass AGenNext Runner
- own long-lived GitHub write credentials in production
- mutate repositories outside Runner-approved GitHub API / Git CLI execution paths
- mark itself production-ready without Runner/gate decisions
- hide policy denials behind successful generation

## Correct terminology

Use these terms in code and docs:

```text
Code Assist Agent / requester
AGenNext Runner / runtime enforcement point
AuthZEN Decision Point
Audit Trace Service
Repository Operation Backend
Scoped Capability
```

Avoid describing Code Assist itself as the final enforcer. Local development code may have lightweight guardrail checks, but production enforcement belongs to AGenNext Runner.

## Practical deployment

Recommended production deployment:

```text
Browser / CLI
  -> AGenNext Runner
  -> AGenNext Code Assist Agent
  -> Agent ID registry
  -> AuthZEN-compatible authorization service
  -> Audit Trace Service
  -> GitHub API / Git CLI sandbox
```

AGenNext Runner owns credentials and execution rights. Code Assist only receives the capabilities Runner grants for that run.
