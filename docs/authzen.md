# Generic AuthZEN support

<<<<<<< HEAD
AGenNext CodeAssist supports a provider-neutral AuthZEN authorization adapter.
=======
AGenNext Code Assist supports a provider-neutral AuthZEN authorization adapter.
>>>>>>> origin/main

AuthZEN is used for externalized authorization decisions. It is separate from authentication.

```text
OIDC or another auth provider -> authenticates the user/operator
AuthZEN-compatible service    -> evaluates access decisions
<<<<<<< HEAD
CodeAssist                   -> enforces allow/deny before protected actions
=======
Code Assist                   -> enforces allow/deny before protected actions
>>>>>>> origin/main
```

## Environment variables

```env
AUTHZ_PROVIDER=authzen
AUTHZ_REQUIRED=true
AUTHZ_FAIL_CLOSED=true

AUTHZEN_ENABLED=true
AUTHZEN_API_URL=https://authz.example.com
AUTHZEN_EVALUATION_PATH=/access/v1/evaluation
AUTHZEN_API_KEY=
AUTHZEN_BEARER_TOKEN=
AUTHZEN_TIMEOUT_SECONDS=10
AUTHZEN_FAIL_CLOSED=true
```

## Request shape

The adapter sends an access evaluation request with:

```json
{
  "subject": {
    "type": "user_or_agent",
    "id": "user:<issuer>|<sub>"
  },
  "action": {
    "name": "push"
  },
  "resource": {
    "type": "repository",
    "id": "AGenNext/CodeAssist",
    "properties": {
      "branch": "code-assist/example",
      "base_branch": "main"
    }
  },
  "context": {
    "service": "agennext-code-assist",
    "mode": "production",
    "run_id": "...",
    "agent_did": "did:web:example.com:agents:code-assist"
  }
}
```

## Accepted response shapes

Boolean result:

```json
{ "result": true }
```

Rich result:

```json
{
  "result": {
    "allow": false,
    "reason": "push requires approval"
  }
}
```

The adapter also accepts `allowed`, `allow`, or `decision` fields with boolean or string values such as `allow`, `deny`, `permit`, or `forbid`.

## Production behavior

```text
AUTHZ_REQUIRED=true + AuthZEN unavailable = deny
AUTHZEN_FAIL_CLOSED=true + invalid response = deny
AuthZEN deny = deny
<<<<<<< HEAD
AuthZEN allow = CodeAssist may continue to local guardrails/checks
=======
AuthZEN allow = Code Assist may continue to local guardrails/checks
>>>>>>> origin/main
```

## Example actions

<<<<<<< HEAD
Recommended CodeAssist action names:
=======
Recommended Code Assist action names:
>>>>>>> origin/main

```text
view
run
dry_run
write
commit
push
open_pr
merge
notify
view_audit
read_secret
admin_gate
```

## Design note

<<<<<<< HEAD
CodeAssist should stay generic. CaaS, OpenFGA, OPA, SpiceDB, or any other authorization platform can implement the AuthZEN-compatible evaluation endpoint outside this repo.
=======
Code Assist should stay generic. CaaS, OpenFGA, OPA, SpiceDB, or any other authorization platform can implement the AuthZEN-compatible evaluation endpoint outside this repo.
>>>>>>> origin/main
