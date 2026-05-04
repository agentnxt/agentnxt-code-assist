# Setup Guide

This guide covers local development, Docker, and production deployment.

## Prerequisites

- Python 3.10-3.12
- Node.js 18+ (for web UI)
- Docker & Docker Compose (optional)
- Git

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/AGenNext/CodeAssist.git
cd CodeAssist
python3.12 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required: LLM Provider
OPENAI_API_KEY=sk-...

# Optional: Other providers
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: GitHub for repo operations  
GITHUB_TOKEN=ghp_...

# Optional: Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Optional: SMTP for email notifications
AGENNEXT_CODE_ASSIST_SMTP_URL=smtp.example.com
AGENNEXT_CODE_ASSIST_SMTP_FROM_EMAIL=codeassist@example.com
AGENNEXT_CODE_ASSIST_SMTP_TO_EMAIL=team@example.com

# Optional: Jira integration
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJECT
```

### 3. Run

**CLI:**
```bash
agennext-code-assist run "Add a health check endpoint" --repo /path/to/repo
```

**API Server:**
```bash
agennext-code-assist serve --host 127.0.0.1 --port 8090
```

Server runs at: `http://localhost:8090`

API docs at: `http://localhost:8090/docs`

---

## Docker Deployment

### Backend Only

```bash
docker-compose up -d --build
```

Access at: `http://localhost:8090`

### With Web UI

```bash
docker-compose --profile web up -d --build
```

- Backend: `http://localhost:8090`
- Web UI: `http://localhost:3000`

### Full Stack (with Caddy, Monitoring)

```bash
docker-compose --profile web --profile edge --profile ops up -d --build
```

Services:
| Service | URL |
|---------|-----|
| API | http://localhost:8090 |
| Web UI | http://localhost:3000 |
| Caddy HTTP | http://localhost:8088 |
| Caddy HTTPS | https://localhost:8443 |
| Uptime Kuma | http://localhost:3001 |
| Healthchecks | http://localhost:8000 |
| GlitchTip | http://localhost:8081 |
| SigNoz | http://localhost:3301 |
| Infisical | http://localhost:8082 |

---

## Development

### Python Backend

```bash
# Activate virtualenv
source .venv/bin/activate

# Run server
agennext-code-assist serve

# Run tests
pytest

# Format code
ruff check --fix
ruff format
```

### Web UI

```bash
cd web
npm install

# Development
NEXT_PUBLIC_AGENNEXT_CODE_ASSIST_API_URL=http://localhost:8090 npm run dev

# Build
npm run build

# Run E2E tests
npx playwright test
```

### Docker Development

```bash
# Rebuild containers
docker-compose build --no-cache

# View logs
docker-compose logs -f

# Stop all
docker-compose down
```

---

## Production

### Environment Variables

Required for production:

```env
# Security
AGENNEXT_CODE_ASSIST_SECRET_KEY=your-secret-key-min-32-chars

# Database (optional)
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis (optional)  
REDIS_URL=redis://localhost:6379

# SSL/TLS
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Deploy Options

**Railway:**
```bash
railbox deploy
```

**Render:**
```bash
render deploy
```

**Cloud Run:**
```bash
gcloud run deploy codeassist \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8090
```

**Kubernetes:**
```bash
kubectl apply -f k8s/
```

---

## API Usage

### CLI

```bash
# Local repo
agennext-code-assist run "Add tests" --repo /path/to/repo --file src/main.py

# GitHub URL
agennext-code-assist run "Fix login bug" \
  --target-url https://github.com/owner/repo/issues/1 \
  --work-branch fix/login \
  --check production
```

### HTTP

```bash
curl -X POST http://localhost:8090/assist \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Add health endpoint",
    "repo_path": "/path/to/repo",
    "files": ["server.py"],
    "dry_run": false
  }'
```

### Python SDK

```python
from agennext_codeassist import AiderCodeAssist, AssistRequest

assistant = AiderCodeAssist()
result = assistant.run(
    AssistRequest(
        instruction="Add login",
        repo_path="/path/to/repo",
        files=["auth.py"],
    )
)
print(result.output)
```

---

## New Modules

### Continuous Improvement

Track bugs and get improvement recommendations.

```python
from agennext_codeassist.continuous_improvement import get_improver

bug_id = get_improver().log_bug(
    exception_type="ValueError",
    context={"file": "auth.py"},
    severity="high"
)
```

### Process Excellence

Track task performance.

```python
from agennext_codeassist.process_excellence import start_task, complete_task

task_id = start_task("process_video", {"format": "mp4"})
# ... work ...
complete_task(task_id)
```

### Project Management

```python
from agennext_codeassist.project_management import get_manager

manager = get_manager()
project_id = manager.create_project("Feature X", "Description")
task_id = manager.add_task(project_id, "Implement X", priority="high")
```

### Daily Status

```python
from agennext_codeassist.daily_status import get_reporter

reporter = get_reporter()
reporter.add_completed_task("Feature X complete")
reporter.add_plan("QA testing")
reporter.send_all()  # Email + Slack
```

### Jira Integration

```python
from agennext_codeassist.jira_integration import get_jira

jira = get_jira()
jira.create_issue("Fix bug", "High priority", JiraPriority.HIGH)
```

---

## Troubleshooting

### Common Issues

**API errors:**
```bash
# Check server logs
docker-compose logs -f server
```

**Model not available:**
```bash
# List available models
agennext-code-assist list-models
```

**Port in use:**
```bash
# Find and kill process
lsof -ti:8090 | xargs kill -9
```

**Permission denied:**
```bash
# Fix permissions
chmod -R 755 .
```

---

## Next Steps

- Read [Architecture](architecture.md)
- Check [API Reference](reference.md)
- Review [Security](security-gates.md)