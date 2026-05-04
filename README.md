# AGenNext CodeAssist

AGenNext CodeAssist is a small service, CLI, and optional web UI that wraps Aider's Python scripting API for focused code changes inside a target repository.

It can:

- run a coding instruction against a repo and selected files
- use Aider's repository map and edit engine
- run against an existing local checkout
- clone/fetch a target repo into a managed workspace
- accept GitHub repo, branch, pull request, issue, or discussion URLs as input
- hydrate GitHub issue and pull request context into the coding instruction
- create/reset a safe work branch for each task
- flag README/code, dependency, upstream-version, Docker, and publishability anomalies
- run post-edit validation using presets such as `production`, `smoke`, `unit`, `integration`, `docker`, and `publishable`
- write a per-run `CODE_ASSIST_CHANGELOG.md` entry with objective, actions, checks, anomalies, and next steps
- optionally notify Slack, SMTP, or generic webhooks after a run
- expose the same behavior through a FastAPI endpoint
- provide an optional Next.js chat UI for operators
- run a Docker Desktop production-simulation stack locally
- support dry runs, automatic confirmations, optional Aider auto-commits, and optional branch push

### Advanced Agent Capabilities

- **Empathy System**: Understands user emotions and adapts communication style based on emotional state, frustration/satisfaction signals, and help-seeking behavior
- **Self-Respect Framework**: Maintains agent autonomy and healthy boundaries in interactions
- **Trust Building Framework**: Establishes and maintains trust through consistent action and transparency
- **Situation Awareness**: Real-time context monitoring and environmental awareness
- **Self-Improvement Engine**: Continuous learning and skill enhancement based on execution feedback
- **Decision Logging**: Structured logging of task execution decisions and reasoning

### Tool Ecosystem

- **Travel Tools**: TripAdvisor-style travel discovery with destination research, itinerary planning, and travel recommendations
- **Weather Tool**: Real-time weather information for planning and logistics
- **Map Tool**: Location-based services and geographic context
- **News Tool**: Current news and information retrieval
- **User Profile**: Personalized interactions based on user preferences and history
- **Skill Registry**: Dynamic skill and tool registration with fallback mechanisms
- **RAG Knowledge**: Retrieval-augmented generation for knowledge-based queries

The Aider Python scripting API is documented by Aider as useful but not a stable compatibility contract, so the wrapper keeps Aider usage isolated in one module.

---

## Distribution modes

| Mode | Command / entry point | Purpose |
|---|---|---|
| Python CLI | `agennext-code-assist run ...` | Local/operator coding tasks |
| FastAPI backend | `agennext-code-assist serve ...` | HTTP API for automation and UIs |
| Static fallback UI | `GET /` from FastAPI | Minimal bundled UI for local testing |
| Optional Next.js UI | `cd web && npm run dev` | Rich chat/operator UI |
| Docker backend | root `Dockerfile` | Backend container |
| Docker Compose | `docker compose up -d` | Backend local deployment |
| Docker Compose + web | `docker compose --profile web up -d` | Backend + Next.js UI locally |
| Docker Desktop simulation | `bash scripts/simulate-production.sh up` | Local production-like end-to-end simulation |
| Optional edge | `docker compose --profile edge up -d` | Caddy reverse proxy and automatic HTTPS |
| Optional ops stack | `docker compose --profile ops up -d` | Uptime, error tracking, observability, and secrets services |
| Cloud Run | GitHub Actions workflow | Managed backend deployment |
| GHCR/Docker Hub | CI/CD after approval | Publishable image targets, not pushed by CodeAssist |

Primary CLI:

```bash
agennext-code-assist
```

Backward-compatible alias:

```bash
agentnxt-code-assist
```

Primary environment prefix:

```env
AGENNEXT_CODE_ASSIST_*
```

Backward-compatible legacy prefix:

```env
AGENTNXT_CODE_ASSIST_*
```

---

## Safety defaults

CodeAssist is local-first and review-first.

By default it does **not**:

- commit
- push
- open pull requests
- merge
- publish images
- send Slack, SMTP, or webhook notifications

Explicit authorization is required:

```bash
--auto-commits --allow-commits
--push --allow-push
--open-pr --allow-pr --push --allow-push
--notify-slack
--notify-webhook
--notify-smtp
```

Merge is not supported by CodeAssist. Merge must happen outside this tool after human approval.

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

## Docker Desktop production simulation

Use this when you want to test AGenNext CodeAssist locally in containers before deploying.

The simulation script:

- verifies Docker Desktop / Docker Engine is running
- creates a temporary target repository under `tmp/simulation-target`
- builds the backend image
- builds the optional Next.js web UI image
- starts the backend and web containers with Docker Compose
- waits for `/healthz` and the web UI to become reachable
- sends a real `POST /assist` dry-run request to the containerized backend
- writes the response to `tmp/simulation-result.json`

Run backend + web simulation:

```bash
bash scripts/simulate-production.sh up
```

Run a fuller local simulation with web, Caddy edge, Uptime Kuma, Healthchecks, GlitchTip, SigNoz, and Infisical:

```bash
bash scripts/simulate-production.sh full
```

Stop containers:

```bash
bash scripts/simulate-production.sh down
```

Remove containers, volumes, and generated simulation files:

```bash
bash scripts/simulate-production.sh clean
```

Default local URLs:

| Service | URL |
|---|---|
| API | `http://localhost:8090` |
| Web UI | `http://localhost:3000` |
| Caddy HTTP | `http://localhost:8088` |
| Caddy HTTPS | `https://localhost:8443` |
| Uptime Kuma | `http://localhost:3001` |
| Healthchecks | `http://localhost:8000` |
| GlitchTip | `http://localhost:8081` |
| SigNoz | `http://localhost:3301` |
| Infisical | `http://localhost:8082` |

Use env vars from `.env.example` to move ports if there are conflicts.

---

## Local checkout mode

Use this when the target repo already exists on disk:

```bash
.venv/bin/agennext-code-assist run \
  "add input validation to the login handler" \
  --repo /path/to/repo \
  --file app/auth.py
```

Use `--dry-run` to ask Aider for the patch without writing files:

```bash
.venv/bin/agennext-code-assist run \
  "explain and simplify this module" \
  --repo /path/to/repo \
  --file app/service.py \
  --dry-run
```

---

## Managed checkout mode

Use this when CodeAssist should clone/fetch the target repo itself.

```bash
.venv/bin/agennext-code-assist run \
  "Phase 1 only: fix app shell/build issues" \
  --repo-url https://github.com/AGenNext/Platform.git \
  --base-branch main \
  --work-branch code-assist/issue-1-phase-1 \
  --file src/app/layout.tsx \
  --file src/app/page.tsx \
  --check production \
  --json
```

You can also use a GitHub full name:

```bash
.venv/bin/agennext-code-assist run \
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
.venv/bin/agennext-code-assist run \
  "Implement the first phase described in this issue. Keep the change focused." \
  --target-url https://github.com/AGenNext/Platform/issues/1 \
  --work-branch code-assist/issue-1-phase-1 \
  --file src/app/layout.tsx \
  --file src/app/page.tsx \
  --file src/components/LogPanel.tsx \
  --check production \
  --json
```

Branch URL example:

```bash
.venv/bin/agennext-code-assist run \
  "Update this branch with a focused fix" \
  --target-url https://github.com/AGenNext/Platform/tree/main \
  --work-branch code-assist/focused-fix
```

Pull request URL example:

```bash
.venv/bin/agennext-code-assist run \
  "Address the review feedback for this pull request" \
  --target-url https://github.com/AGenNext/Platform/pull/12 \
  --work-branch code-assist/pr-12-followup
```

Issue and PR URLs hydrate title/body/state into the coding instruction. Discussion URLs currently resolve metadata but still require the relevant discussion text to be pasted into the instruction.

---

## Optional Next.js chat UI

The rich web UI lives in:

```text
web/
```

Run the backend:

```bash
.venv/bin/agennext-code-assist serve --host 127.0.0.1 --port 8090
```

Run the web UI:

```bash
cd web
npm install
NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL=http://localhost:8090 npm run dev
```

Open:

```text
http://localhost:3000
```

The Next.js UI supports:

- chat-style instruction input
- target URL or local repo path
- work branch
- file list
- check presets
- dry-run toggle
- upstream dependency check toggle
- Slack notification toggle
- commit/push/PR guardrail toggles, all off by default
- changed files
- check results
- anomaly report
- change log preview
- raw output

Run backend + web with Docker Compose:

```bash
docker compose --profile web up -d --build
```

Backend:

```text
http://localhost:8090
```

Web UI:

```text
http://localhost:3000
```

---

## Optional edge and ops stack

Caddy edge proxy with automatic HTTPS:

```bash
docker compose --profile web --profile edge up -d --build
```

Optional ops stack:

```bash
docker compose --profile ops up -d
```

Ops profiles include:

- Uptime Kuma for uptime dashboards
- Healthchecks for heartbeat monitoring
- GlitchTip for error tracking
- SigNoz for OpenTelemetry observability
- Infisical for secret management

SMTP and generic webhook notifications are optional:

```bash
.venv/bin/agennext-code-assist run \
  "Run production readiness checks" \
  --repo /path/to/repo \
  --check production \
  --notify-webhook \
  --webhook-url https://example.com/webhook \
  --notify-smtp \
  --smtp-url 'smtp://user:password@smtp.example.com:587?starttls=true' \
  --smtp-to-email ops@example.com
```

---

## Production-readiness checks

Use `--check` with a preset or a literal shell command.

Presets:

| Preset | Purpose |
|---|---|
| `dependency` | Dependency install/lock validation where possible |
| `typecheck` | TypeScript/Python type-check script if present |
| `lint` | Lint script if present |
| `unit` | Unit test script if present |
| `integration` | Integration/e2e test script if present |
| `smoke` | Smoke test or build script if present |
| `docker` | Docker build / compose config simulation |
| `docker-smoke` | Docker container smoke run / compose quiet config |
| `publishable` | Local image inspect/tag simulation for Docker Hub and GHCR |
| `production` | Runs dependency, typecheck, lint, unit, integration, smoke, docker, docker-smoke, and publishable checks where applicable |
| `all` | Alias for `production` |

Example:

```bash
.venv/bin/agennext-code-assist run \
  "Make this repo production-ready and flag anything blocking publishing" \
  --target-url https://github.com/AGenNext/Platform/issues/1 \
  --work-branch code-assist/issue-1-production-readiness \
  --check production \
  --fail-on-anomaly-severity error \
  --json
```

The `publishable` preset only simulates local Docker image readiness and tagging. It does not push images to Docker Hub or GHCR.

---

## Audits and anomalies

Each run can report anomalies for:

- README claims not matching repo files
- missing scripts documented in README
- missing SDK/model/framework/Runner/Kernel implementation markers
- old branding references
- dependency/lockfile mismatch
- available upstream package versions when enabled
- Dockerfile production concerns
- missing Docker Hub/GHCR publish workflow configuration

Upstream dependency checks are disabled by default because they require network calls:

```bash
--check-upstream-versions
```

---

## Change log

By default each run appends a reviewable entry to:

```text
CODE_ASSIST_CHANGELOG.md
```

The entry documents:

- objective
- target repo / URL / branch / SHA
- actions taken
- changed files
- checks and pass/fail status
- anomalies and risks
- result
- next steps

Disable it with:

```bash
--no-change-log
```

or choose a path:

```bash
--change-log-path docs/code-assist-log.md
```

---

## Slack notifications

Slack is optional and disabled by default.

Configure a webhook:

```env
AGENNEXT_CODE_ASSIST_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Send a notification for one run:

```bash
.venv/bin/agennext-code-assist run \
  "Phase 1 only: fix app shell/build issues" \
  --target-url https://github.com/AGenNext/Platform/issues/1 \
  --work-branch code-assist/issue-1-phase-1 \
  --check production \
  --notify-slack
```

Or enable globally:

```env
AGENNEXT_CODE_ASSIST_ENABLE_SLACK=true
```

Slack notifications include status, repo, branch, changed-file count, failed-check count, anomaly count, and whether anything was pushed.

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
.venv/bin/agennext-code-assist serve --host 127.0.0.1 --port 8090
```

If the preferred port is unavailable, the server automatically uses the next available port. Use `--fixed-port` to fail instead.

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
    "checks": ["production"],
    "dry_run": false,
    "push": false,
    "notify_slack": false
  }'
```

---

## Configuration

Environment variables are documented in `.env.example`.

Provider credentials such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and OpenAI-compatible gateway variables are read by Aider/LiteLLM.

Legacy `AGENTNXT_CODE_ASSIST_*` variables are still accepted as compatibility fallbacks.

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
        checks=["production"],
    )
)

print(result.output)
print(result.change_log)
```

---

## Notes

- `files` are resolved relative to the checkout and cannot escape the repo.
- If `files` is empty, Aider can still use the repo map, but targeted files usually produce better edits.
- Aider requires Python 3.10-3.12 at the time this wrapper was created.
- Keep the HTTP API bound to `127.0.0.1` or a private network unless authentication is added.

---

## Optional macOS Desktop App (DMG)

The Next.js web UI can be packaged as a native macOS desktop application using Electron and electron-builder.

### Prerequisites

```bash
cd web
npm install
```

### Development Mode

Run the Electron app in development mode:

```bash
npm run electron:dev
```

### Build DMG

Package the web UI as a macOS disk image:

```bash
npm run electron:build:dmg
```

The DMG will be created in `web/release/CodeAssist-0.1.0.dmg`.

Note: DMG creation requires macOS because `dmg-builder` has native dependencies. On Linux, you can build the `.app` bundle:

```bash
npm run electron:build
```

This creates `web/release/mac/CodeAssist.app`.

---

## End-to-End Testing

The web UI includes Playwright end-to-end tests for quality assurance.

### Prerequisites

```bash
cd web
npm install
npx playwright install chromium
```

### Run Tests

Execute the E2E test suite:

```bash
cd web
npx playwright test
```

### Test Configuration

The test configuration is in `web/playwright.config.ts` and includes:
- Chromium, Firefox, and WebKit browser testing
- HTML test reporting
- Automatic server startup during tests
