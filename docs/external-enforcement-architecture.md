# AGenNext Kernel, Runner, and CodeAssist architecture

AGenNext CodeAssist is an agent. It must not be treated as the ultimate policy enforcement point.

**AGenNext Kernel is the infrastructure abstraction layer.**

**AGenNext Runner is the runtime enforcement point.**

## Stack responsibility model

```text
AGenNext Kernel
  -> infrastructure abstraction layer
  -> makes deployments infra-agnostic
  -> abstracts compute, filesystem, network, secrets, sandbox, container, and execution backends
  -> provides low-level primitives to Runner

AGenNext Runner
  -> runtime enforcement layer
  -> makes agent execution framework-agnostic
  -> grants/denies scoped capabilities
  -> enforces AuthZEN decisions and runtime guardrails
  -> invokes Kernel primitives for actual infrastructure operations

AGenNext CodeAssist
  -> agent / requester / planner
  -> proposes code changes
  -> requests capabilities from Runner
  -> never self-authorizes privileged actions
```

## Correct responsibility split

```text
User / Operator
  -> authenticates with OIDC
  -> gives intent and explicit authorization flags

AGenNext CodeAssist Agent
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
  -> controls access to Kernel infrastructure primitives
  -> records or forwards audit evidence

AGenNext Kernel
  -> infra abstraction point
  -> executes allowed low-level operations across local, VM, container, cloud, or Kubernetes targets
  -> keeps Runner and agents deployment/infra agnostic

GitHub API / Git CLI / Sandbox / Containers / Cloud
  -> concrete execution backends reached through Runner + Kernel
  -> perform actual operations only after Runner allows them
```

## Roles

| Component | Role |
|---|---|
| CodeAssist | Agent / requester / planner |
| AGenNext Runner | Runtime / policy enforcement point |
| AGenNext Kernel | Infrastructure abstraction layer |
| OIDC provider | Authentication provider |
| Agent ID registry | Agent identity and governance context provider |
| AuthZEN service | Policy decision point |
| GitHub API / Git CLI | Resource operation backend controlled by Runner through Kernel |
| Audit service | Evidence and trace ledger |

## Design rule

CodeAssist may build authorization requests and propose changes, but it must not be trusted to enforce its own permissions.

The enforcement boundary is **AGenNext Runner**.

The infrastructure boundary is **AGenNext Kernel**.

Runner should own:

```text
- scoped capabilities
- fail-closed behavior
- AuthZEN decision enforcement
- runtime guardrails
- audit trace capture or audit forwarding
- when and how Kernel primitives may be invoked
```

Kernel should own abstractions for:

```text
- filesystem operations
- network operations
- process execution
- sandbox lifecycle
- container lifecycle
- secret access primitives
- GitHub API / Git CLI backend adapters
- local / VM / cloud / Kubernetes deployment targets
```

## AuthZEN and capability request flow

```text
1. CodeAssist receives user intent.
2. CodeAssist identifies desired action: run, write, commit, push, open_pr, notify, etc.
3. CodeAssist requests a scoped capability from AGenNext Runner.
4. AGenNext Runner builds/sends subject/action/resource/context to an AuthZEN-compatible service.
5. AuthZEN-compatible service returns allow/deny and reason.
6. AGenNext Runner enforces the decision.
7. If allowed, AGenNext Runner invokes AGenNext Kernel primitives.
8. AGenNext Kernel executes the concrete operation through GitHub API, Git CLI, sandbox, container, local runtime, VM, cloud, or Kubernetes target.
9. Audit service records the request, decision, operation, and result.
```

## Capability request shape

CodeAssist should ask Runner for capabilities, not directly execute privileged operations.

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
    "max_operations": 10,
    "kernel_backends": ["github-api"]
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
CodeAssist self-approval = Runner denies
Expired capability = Runner denies
Capability constraint mismatch = Runner denies
Unauthorized Kernel primitive = Runner denies
Kernel backend unavailable for required operation = Runner denies or fails closed
```

## What CodeAssist can do

CodeAssist can:

- describe the requested action
- build an AuthZEN-compatible access evaluation request shape for Runner
- attach OIDC subject context when supplied by Runner/session
- attach Agent ID context when available
- propose code changes
- request tool execution from AGenNext Runner
- report policy decision results to the user
- include sanitized policy context in change logs

## What CodeAssist must not do

CodeAssist must not:

- self-authorize privileged actions
- bypass AGenNext Runner
- bypass AGenNext Kernel for infrastructure operations
- own long-lived GitHub write credentials in production
- mutate repositories outside Runner-approved GitHub API / Git CLI execution paths
- mark itself production-ready without Runner/gate decisions
- hide policy denials behind successful generation

## Correct terminology

Use these terms in code and docs:

```text
AGenNext Kernel / infra abstraction layer
AGenNext Runner / runtime enforcement point
CodeAssist Agent / requester
AuthZEN Decision Point
Audit Trace Service
Repository Operation Backend
Scoped Capability
Kernel Primitive
```

Avoid describing CodeAssist itself as the final enforcer. Local development code may have lightweight guardrail checks, but production enforcement belongs to AGenNext Runner, and concrete infrastructure execution belongs behind AGenNext Kernel.

## Practical deployment

Recommended production deployment:

```text
Browser / CLI
  -> AGenNext Runner
  -> AGenNext CodeAssist Agent
  -> Agent ID registry
  -> AuthZEN-compatible authorization service
  -> Audit Trace Service
  -> AGenNext Kernel
  -> GitHub API / Git CLI / Sandbox / Container / Cloud / Kubernetes backend
```

AGenNext Runner owns capabilities and enforcement. AGenNext Kernel owns infrastructure abstraction. CodeAssist only receives the capabilities Runner grants for that run.
