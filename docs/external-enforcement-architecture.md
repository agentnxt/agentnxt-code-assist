# External enforcement architecture

AGenNext Code Assist is an agent. It must not be treated as the ultimate policy enforcement point.

## Correct responsibility split

```text
User / Operator
  -> authenticates with OIDC
  -> gives intent and explicit authorization flags

Code Assist Agent
  -> proposes and prepares actions
  -> requests authorization decisions
  -> never self-authorizes privileged actions

Agent ID Protocol
  -> provides optional agent identity, DID, delegation, and governance context

AuthZEN-compatible Authorization Service
  -> evaluates access request
  -> can be backed by CAAS, OpenFGA, OPA, SpiceDB, or another policy engine
  -> returns allow / deny / reason

Execution Controller / Runner Gateway
  -> policy enforcement point
  -> blocks or allows tool execution
  -> owns fail-closed behavior
  -> records audit evidence

GitHub API / Git CLI / Sandbox
  -> performs the actual repository operation only after enforcement allows it
```

## Roles

| Component | Role |
|---|---|
| Code Assist | Agent / requester / planner |
| OIDC provider | Authentication provider |
| Agent ID registry | Agent identity and governance context provider |
| AuthZEN service | Policy decision point |
| Execution Controller / Runner Gateway | Policy enforcement point |
| GitHub API / Git CLI | Resource operation backend |
| Audit service | Evidence and trace ledger |

## Design rule

Code Assist may build authorization requests, but it must not be trusted to enforce its own permissions.

The enforcement boundary should be outside the agent, for example:

```text
1. API gateway in front of Code Assist
2. Runner service that owns GitHub tokens and filesystem access
3. Sidecar/tool proxy that intercepts tool calls
4. GitHub App backend that performs all repo writes
5. Sandbox controller that grants or denies file/network/process capabilities
```

## AuthZEN request flow

```text
1. Code Assist receives user intent.
2. Code Assist identifies desired action: run, write, commit, push, open_pr, notify, etc.
3. Code Assist sends subject/action/resource/context to an AuthZEN-compatible service.
4. AuthZEN-compatible service returns allow/deny and reason.
5. Execution Controller enforces the decision.
6. If allowed, Execution Controller performs the operation through GitHub API or Git CLI.
7. Audit service records the request, decision, operation, and result.
```

## Fail-closed rule

In production:

```text
AuthZEN unavailable = deny
Agent required but Agent ID unavailable = deny
Audit trace unavailable = deny
Security gate unavailable = deny when required
Unknown update path = deny
Code Assist self-approval = deny
```

## What Code Assist can do

Code Assist can:

- build an AuthZEN-compatible access evaluation request
- attach OIDC subject context
- attach Agent ID context when available
- propose code changes
- request tool execution from the Execution Controller
- report policy decision results to the user
- include sanitized policy context in change logs

## What Code Assist must not do

Code Assist must not:

- self-authorize privileged actions
- directly bypass the Execution Controller
- own long-lived GitHub write credentials in production
- mutate repositories outside approved GitHub API / Git CLI execution paths
- mark itself production-ready without external gate decisions
- hide policy denials behind successful generation

## Correct terminology

Use these terms in code and docs:

```text
Code Assist Agent / requester
AuthZEN Decision Point
Execution Controller / Runner Gateway / Policy Enforcement Point
Audit Trace Service
Repository Operation Backend
```

Avoid describing Code Assist itself as the final enforcer. At most, local development code may have a lightweight guardrail check, but production enforcement belongs outside the agent.

## Practical deployment

Recommended production deployment:

```text
Browser / CLI
  -> API Gateway
  -> Execution Controller
  -> Code Assist Agent runtime
  -> AuthZEN-compatible authorization service
  -> Agent ID registry
  -> Audit Trace Service
  -> GitHub App / Git CLI sandbox
```

The Execution Controller owns credentials and execution rights. Code Assist only receives the capabilities the controller grants for that run.
