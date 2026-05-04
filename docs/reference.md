# AGenNext CodeAssist Documentation

## Overview

AGenNext CodeAssist is built on a modular architecture with clear separation between infrastructure, runtime, and agent layers.

## Framework & Technology Stack

### Core Framework
- **Aider**: Python scripting API for code editing and repository interaction
- **FastAPI**: Web framework for HTTP API endpoints
- **Pydantic**: Data validation using Python type annotations

### Runtime Requirements
- **Python**: 3.10, 3.11, 3.12
- **Node.js**: 20+ (for Web UI)
- **Docker**: 24.0+ (for containerized deployments)

### Infrastructure Components
| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | Python + FastAPI | API server |
| Web UI | Next.js 14 | React-based operator interface |
| Database | File-based (JSON/Markdown) | Memory and RAG storage |
| Container | Docker + Caddy | Production deployment |
| Orchestration | Docker Compose | Local development/simulation |

## Architecture Layers

### 1. Agent Layer (CodeAssist)
- Aider-backed code editing
- Repository map and context
- Edit engine with skills and memory

### 2. Runtime Layer (Runner)
- Policy enforcement point
- Guardrails and authorization
- Audit logging

### 3. Infrastructure Layer (Kernel)
- Workspace management
- Git operations
- Notification delivery
- RAG knowledge backend

## Runtime Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | For OpenAI models | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | For Claude models | - | Anthropic API key |
| `AIDER_MODEL` | No | `gpt-4o` | Model to use |
| `AGENNEXT_CODE_ASSIST_PORT` | No | `8090` | API server port |
| `PRODUCTION` | No | `false` | Enable production mode |
| `API_KEY_REQUIRED` | No | `false` | Require API key auth |

## Security Requirements

### Development
- Local-only operations by default
- No automatic commits/pushes
- Explicit flag required for destructive actions

### Production
```bash
PRODUCTION=true
API_KEY_REQUIRED=true
REQUIRED_API_KEY=<your-api-key>
ALLOWED_ORIGINS=https://your-domain.com
```

### Network
- Bind to `127.0.0.1` or private network
- Use HTTPS in production (Caddy)
- Rate limiting: 60 req/min per IP

## Deployment Modes

### 1. Python CLI
```bash
pip install -e .
agennext-code-assist run "fix issue" --repo /path/to/repo
```

### 2. FastAPI Server
```bash
agennext-code-assist serve --host 127.0.0.1 --port 8090
```

### 3. Docker
```bash
docker compose up -d
```

### 4. Docker Compose + Web UI
```bash
docker compose --profile web up -d
```

## Testing

### Unit Tests
```bash
pytest tests/ -v
```

### E2E Tests
```bash
cd web && npm install && npx playwright test
```

### Security Scanning
```bash
# Bandit SAST
pip install bandit && bandit -r src/

# Dependency audit
pip install pip-audit && pip-audit
```

## Performance Considerations

- Workspace per checkout in `/srv/agennext/code-assist/workspaces`
- RAG context limited to 24,000 chars default
- Memory compaction available
- Rate limiting prevents abuse

## Support

- GitHub Issues: https://github.com/AGenNext/CodeAssist/issues
- Discussions: https://github.com/AGenNext/CodeAssist/discussions