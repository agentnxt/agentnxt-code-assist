# AgentNXT Code Assist

AgentNXT Code Assist is a small service and CLI that wraps Aider's Python scripting API for focused code changes inside a target repository.

It can:

- run a coding instruction against a repo and selected files
- use Aider's repository map and edit engine
- run against an existing local checkout
- clone/fetch a target repo into a managed workspace
- accept GitHub repo, branch, pull request, issue, or discussion URLs as input
- create/reset a safe work branch for each task
- run post-edit checks such as `npm run type-check` and `npm run lint`
- expose the same behavior through a FastAPI endpoint
- support dry runs, automatic confirmations, optional Aider auto-commits, and optional branch push

The Aider Python scripting API is documented by Aider as useful but not a stable compatibility contract, so the wrapper keeps Aider usage isolated in one module.

---

## Quick start

```bash
git clone https://github.com/AGenNext/agentnxt-code-assist.git
cd agentnxt-code-assist
python3.12 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

Set the provider API key in `.env`, then run a task.

---

## Local checkout mode

Use this when the target repo already exists on disk:

```bash
.venv/bin/agentnxt-code-assist run \
  "add input validation to the login handler" \
  --repo /path/to/repo \
  --file app/auth.py
```

Use `--dry-run` to ask Aider for the patch without writing files:

```bash
.venv/bin/agentnxt-code-assist run \
  "explain and simplify this module" \
  --repo /path/to/repo \
  --file app/service.py \
  --dry-run
```

---

## Managed checkout mode

Use this when Code Assist should clone/fetch the target repo itself.

```bash
.venv/bin/agentnxt-code-assist run \
  "Phase 1 only: fix app shell/build issues" \
  --repo-url https://github.com/AGenNext/Platform.git \
  --base-branch main \
  --work-branch code-assist/issue-1-phase-1 \
  --file src/app/layout.tsx \
  --file src/app/page.tsx \
  --check "npm run type-check" \
  --check "npm run lint" \
  --json
```

You can also use a GitHub full name:

```bash
.venv/bin/agentnxt-code-assist run \
  "Phase 1 only: fix app shell/build issues" \
  --repo-full-name AGenNext/Platform \
  --base-branch main \
  --work-branch code-assist/issue-1-phase-1
```

Managed checkouts go under:

```text
/srv/agennext/code-assist/workspaces
```

Override with:

```bash
--workspace-root /custom/workspace/root
```

---

## Target URL mode

Use one `--target-url` instead of manually passing repo metadata.

Supported GitHub URL types:

```text
https://github.com/AGenNext/Platform
https://github.com/AGenNext/Platform/tree/my-branch
https://github.com/AGenNext/Platform/pull/12
https://github.com/AGenNext/Platform/issues/1
https://github.com/AGenNext/Platform/discussions/3
```

Examples:

```bash
.venv/bin/agentnxt-code-assist run \
  "Implement the first phase described in this issue. Keep the change focused." \
  --target-url https://github.com/AGenNext/Platform/issues/1 \
  --work-branch code-assist/issue-1-phase-1 \
  --file src/app/layout.tsx \
  --file src/app/page.tsx \
  --file src/components/LogPanel.tsx \
  --check "npm run type-check" \
  --check "npm run lint" \
  --json
```

Branch URL example:

```bash
.venv/bin/agentnxt-code-assist run \
  "Update this branch with a focused fix" \
  --target-url https://github.com/AGenNext/Platform/tree/main \
  --work-branch code-assist/focused-fix
```

Pull request URL example:

```bash
.venv/bin/agentnxt-code-assist run \
  "Address the review feedback for this pull request" \
  --target-url https://github.com/AGenNext/Platform/pull/12 \
  --work-branch code-assist/pr-12-followup
```

Issue and discussion URLs resolve repo metadata and default branch naming, but they do not yet fetch issue/discussion body text into the instruction. Paste the relevant task text into the instruction until GitHub issue/discussion body hydration is added.

---

## Branch guardrails

Managed checkout mode refuses to edit directly on `main`, `master`, or the selected base branch.

Use one work branch per focused pass:

```text
code-assist/issue-1-phase-1
code-assist/issue-1-phase-2
code-assist/pr-12-followup
```

Recommended workflow:

```text
one instruction -> one phase -> one branch -> checks -> review -> next phase
```

---

## HTTP API

Start the server:

```bash
.venv/bin/agentnxt-code-assist serve --host 127.0.0.1 --port 8090
```

Call it with local checkout mode:

```bash
curl -X POST http://127.0.0.1:8090/assist \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "add tests for the parser edge cases",
    "repo_path": "/path/to/repo",
    "files": ["src/parser.py", "tests/test_parser.py"],
    "dry_run": false
  }'
```

Call it with target URL mode:

```bash
curl -X POST http://127.0.0.1:8090/assist \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Phase 1 only: fix app shell/build issues",
    "target_url": "https://github.com/AGenNext/Platform/issues/1",
    "work_branch": "code-assist/issue-1-phase-1",
    "files": [
      "src/app/layout.tsx",
      "src/app/page.tsx",
      "src/components/LogPanel.tsx"
    ],
    "checks": ["npm run type-check", "npm run lint"],
    "dry_run": false,
    "push": false
  }'
```

---

## Configuration

Environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `AGENTNXT_CODE_ASSIST_MODEL` | `gpt-4o` | Model name passed to Aider/LiteLLM |
| `AGENTNXT_CODE_ASSIST_AUTO_YES` | `true` | Auto-confirm Aider prompts |
| `AGENTNXT_CODE_ASSIST_AUTO_COMMITS` | `false` | Let Aider commit its edits |
| `AGENTNXT_CODE_ASSIST_DRY_RUN` | `false` | Run without writing files |
| `AGENTNXT_CODE_ASSIST_HOST` | `127.0.0.1` | API host |
| `AGENTNXT_CODE_ASSIST_PORT` | `8090` | API port |
| `AGENTNXT_CODE_ASSIST_WORKSPACE` | `/srv/agennext/code-assist/workspaces` | Managed checkout workspace root |
| `AGENTNXT_CODE_ASSIST_GIT_USER_NAME` | `agennext-code-assist` | Git author name for managed checkouts |
| `AGENTNXT_CODE_ASSIST_GIT_USER_EMAIL` | `code-assist@agennext.local` | Git author email for managed checkouts |
| `GITHUB_TOKEN` | unset | Optional token for private repos and pushing HTTPS branches |

Provider credentials such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and OpenAI-compatible gateway variables are read by Aider/LiteLLM.

---

## Python usage

```python
from agentnxt_code_assist import AiderCodeAssist, AssistRequest

assistant = AiderCodeAssist()
result = assistant.run(
    AssistRequest(
        instruction="add a /health endpoint",
        repo_url="https://github.com/AGenNext/Platform.git",
        work_branch="code-assist/add-health",
        files=["server.py"],
        checks=["npm run type-check"],
    )
)

print(result.output)
```

---

## Notes

- `files` are resolved relative to the checkout and cannot escape the repo.
- If `files` is empty, Aider can still use the repo map, but targeted files usually produce better edits.
- Aider requires Python 3.10-3.12 at the time this wrapper was created.
- Keep the HTTP API bound to `127.0.0.1` or a private network unless authentication is added.
