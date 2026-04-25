# AgentNXT Code Assist

AgentNXT Code Assist is a small service and CLI that wraps Aider's Python scripting API for one-shot code changes inside a target repository.

It can:

- run a coding instruction against a repo and selected files
- use Aider's repository map and edit engine
- expose the same behavior through a FastAPI endpoint
- support dry runs, automatic confirmations, and optional Aider auto-commits

The Aider Python scripting API is documented by Aider as useful but not a stable compatibility contract, so the wrapper keeps Aider usage isolated in one module.

## Quick Start

```bash
cd /Users/apple/organization/products/agentnxt-code-assist/repo
python3.12 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

Set the provider API key in `.env`, then run a task:

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

## HTTP API

Start the server:

```bash
.venv/bin/agentnxt-code-assist serve --host 127.0.0.1 --port 8090
```

Call it:

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

Provider credentials such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and OpenAI-compatible gateway variables are read by Aider/LiteLLM.

## Python Usage

```python
from agentnxt_code_assist import AiderCodeAssist, AssistRequest

assistant = AiderCodeAssist()
result = assistant.run(
    AssistRequest(
        instruction="add a /health endpoint",
        repo_path="/path/to/repo",
        files=["server.py"],
    )
)

print(result.output)
```

## Notes

- `files` are resolved relative to `repo_path` and cannot escape the repo.
- If `files` is empty, Aider can still use the repo map, but targeted files usually produce better edits.
- Aider requires Python 3.10-3.12 at the time this wrapper was created.
