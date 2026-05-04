# Architecture Overview

CodeAssist follows a modular architecture with skill-based agents, tool registries, and extensible components.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CodeAssist CLI                         │
│                 (agennext_codeassist)                     │
└─────────────────────┬─────────────────────────────────────┘
                      │
        ┌───────────┴───────────┐
        │                       │
   ┌────▼────┐           ┌──────▼─────┐
   │  CLI   │           │   REST API  │
   └────┬───┘           └──────┬──────┘
        │                      │
        │              ┌───────▼───────┐
        │              │               │
   ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐
   │ Runner  │   │ Skills  │   │  Tools   │
   └─────────┘   └────────┘   └──────────┘
        │
   ┌────▼──────────────────────────────┐
   │     Aider Integration             │
   └──────────────────────────────────┘
```

## Core Components

### 1. Agent Core (`agent_id_protocol.py`)
- Agent identification protocol
- Session management
- Request/response handling

### 2. Skills System (`skill_registry.py`)
- Skill loading and registration
- Skill execution context
- Skill-to-skill communication

**Built-in Skills:**
- `Empathy` - Emotional state adaptation
- `Self-Respect` - Boundary maintenance  
- `Trust Building` - Transparency and reliability
- `Situation Awareness` - Context monitoring
- `Self-Improvement` - Continuous learning
- `Decision Logging` - Execution reasoning

### 3. Tool Registry (`tool_registry.py`)
- Tool discovery and invocation
- Tool metadata management
- Tool security validation

**Built-in Tools:**
- `TravelTool` - Flight/hotel search
- `WeatherTool` - Weather data
- `RAGKnowledge` - Knowledge retrieval
- `EmailNotifier` - Email notifications
- `SlackNotifier` - Slack messages

### 4. Runner (`aider_runner.py`)
- Aider subprocess management
- Code execution sandboxing
- Change tracking

### 5. Context System
- `context_aware.py` - Context tracking
- `context_fetcher.py` - External context

### 6. Authentication (`auth.py`, `authzen.py`)
- OAuth/JWT support
- Permission enforcement

### 7. Process Excellence
- `process_excellence.py` - Task timing
- `continuous_improvement.py` - Bug logging

### 8. Project Management
- `project_management.py` - Projects/tasks
- `jira_integration.py` - Jira sync
- `daily_status.py` - Status reports

## API Server Architecture

```
FastAPI
  │
  ├── /health           → Health check
  ├── /agents           → Agent operations
  ├── /skills          → Skill operations
  ├── /tools           → Tool operations
  ├── /run              → Code execution
  ├── /projects        → Project management
  ├── /improvements    → Bug tracking
  ├── /processes       → Process excellence
  ├── /daily           → Status reports
  └── /jira            → Jira integration
```

## Data Flow

1. **Request Received** → Auth middleware validates
2. **Skill Router** → Determines applicable skills
3. **Tool Executor** → Processes tool calls
4. **Aider Runner** → Executes code changes
5. **Response** → Aggregated results returned

## Extensibility

### Adding Skills
```python
# Create skill file in skills/
class MySkill:
    name = "my_skill"
    
    async def execute(self, context):
        # Skill logic
        return result
```

### Adding Tools
```python
# Register in tool_registry.py
registry.register(
    name="my_tool",
    func=my_function,
    security_level="low"
)
```

### Adding API Endpoints
```python
# Add to server.py
@app.get("/my/endpoint")
def my_endpoint():
    return {"result": "ok"}
```

## Security Layers

1. **Authentication** - JWT/OAuth tokens
2. **AuthZen** - Permission enforcement  
3. **Tool Security** - Risk-level validation
4. **Execution Sandbox** - Aider subprocess isolation
5. **Audit Trail** - All operations logged

## Deployment

### Local
```bash
pip install -e .
agennext-code-assist run
```

### Docker
```bash
docker-compose up -f docker-compose.yml
```

### Production
```bash
uvicorn agennext_codeassist.server:app --workers 4
```