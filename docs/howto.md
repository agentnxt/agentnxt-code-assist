# How to Use CodeAssist

This guide covers practical usage patterns for developers.

## Basic Usage

### CLI

```bash
# Simple task on local repo
agennext-code-assist run "Add input validation" --repo /path/to/repo

# With specific files
agennext-code-assist run "Refactor auth module" --repo /path/to/repo --file auth.py

# GitHub issue
agennext-code-assist run "Fix login bug" \
  --target-url https://github.com/owner/repo/issues/45 \
  --work-branch fix/login-bug \
  --check production

# Dry run (preview only)
agennext-code-assist run "Add tests" --repo /path/to/repo --dry-run
```

### HTTP API

```bash
# Health check
curl http://localhost:8090/health

# Run task
curl -X POST http://localhost:8090/assist \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Add health endpoint",
    "repo_path": "/path/to/repo",
    "files": ["server.py"],
    "dry_run": false
  }'
```

### Python

```python
from agennext_codeassist import AiderCodeAssist, AssistRequest

assistant = AiderCodeAssist()

result = assistant.run(
    AssistRequest(
        instruction="Add login endpoint",
        repo_path="/path/to/repo",
        files=["auth.py", "routes.py"],
        checks=["unit", "lint"],
    )
)

print(result.output)
print(result.change_log)
```

---

## Advanced Patterns

### Multi-file Changes

```python
result = assistant.run(
    AssistRequest(
        instruction="Add user profile with preferences",
        files=[
            "models/user.py",
            "routes/users.py", 
            "templates/profile.html",
            "tests/test_users.py",
        ],
    )
)
```

### Conditional Logic

```python
# Only run if files changed
if files_modified:
    result = assistant.run(
        AssistRequest(
            instruction="Update tests for changed files",
            files=list(files_modified),
        )
    )
```

### Error Handling

```python
from agennext_codeassist import AiderCodeAssist, AssistRequest
from agennext_codeassist.exceptions import ValidationError, ExecutionError

try:
    result = assistant.run(request)
except ValidationError as e:
    print(f"Invalid request: {e}")
except ExecutionError as e:
    print(f"Execution failed: {e}")
```

---

## New Modules

### Bug Tracking

```python
from agennext_codeassist.continuous_improvement import get_improver

improver = get_improver()

# Log a bug
bug_id = improver.log_bug(
    exception_type="ValueError",
    context={
        "file": "auth.py",
        "function": "validate_token",
        "input": {"token": "expired"},
    },
    severity="high",
)

# Get recommendations
recommendations = improver.get_recommendations()
for rec in recommendations:
    print(f"- {rec.description}")

# Mark as implemented
improver.implement_recommendation(rec.recommendation_id, notes="Added caching")
```

### Process Excellence

```python
from agennext_codeassist.process_excellence import start_task, complete_task

# Start tracking
task_id = start_task("export_csv", {"format": "utf-8", "columns": ["name", "email"]})

# ... do work ...

duration = complete_task(task_id)
print(f"Completed in {duration}ms")

# If slower than before, get suggestions
improvements = get_excellence().get_pending_improvements()
for imp in improvements:
    print(f"Try {imp.improvement_type}: {imp.description}")

# Approve and implement
get_excellence().approve_improvement(imp.improvement_id)
get_excellence().implement_improvement(imp.improvement_id, notes="Added index caching")
```

### Project Management

```python
from agennext_codeassist.project_management import get_manager
from agennext_codeassist.project_management import TaskStatus, Priority

manager = get_manager()

# Create project
project_id = manager.create_project(
    "New Feature",
    "Description of the feature",
    due_date="2026-06-01",
)

# Add tasks
task1 = manager.add_task(
    project_id,
    "Design API schema",
    priority=Priority.HIGH,
)
task2 = manager.add_task(
    project_id,
    "Implement endpoints", 
    priority=Priority.MEDIUM,
)
task3 = manager.add_task(
    project_id,
    "Add tests",
    priority=Priority.MEDIUM,
)

# Add dependency (task3 blocked by task2)
manager.add_dependency(task2, task3, "blocks")

# Update progress
manager.update_task(project_id, task1, TaskStatus.COMPLETED)
manager.update_task(project_id, task2, TaskStatus.IN_PROGRESS)

# Add milestone
milestone_id = manager.add_milestone(
    project_id,
    "Beta Release",
    "Enable feature flag for beta users",
)

# Check blocked tasks
blocked = manager.get_blocked_tasks(project_id, task1)
print(f"Tasks waiting on task1: {len(blocked)}")

# Get report
print(manager.generate_report())
```

### Daily Status

```python
from agennext_codeassist.daily_status import get_reporter

reporter = get_reporter()

# Log completed work
reporter.add_completed_task("Login OAuth", "Google + GitHub providers")
reporter.add_completed_task("User profiles", "Name, avatar, settings")

# Plan tomorrow
reporter.add_plan("Add logout", "high")
reporter.add_plan("Session cleanup", "medium")

# Add blockers
reporter.add_blocker("API rate limits hit", "high")
reporter.add_blocker("Missing test data", "low")

# Generate reports
subject, body = reporter.generate_email_report()
print(f"Subject: {subject}")
print(body)

slack = reporter.generate_slack_report()
print(slack)

# Send notifications
results = reporter.send_all()
print(results)
```

### Jira Integration

```python
from agennext_codeassist.jira_integration import get_jira
from agennext_codeassist.jira_integration import JiraIssueType, JiraPriority, JiraStatus

jira = get_jira()

# Create issue
result = jira.create_issue(
    summary="Add user authentication",
    description="Implement OAuth login",
    issue_type=JiraIssueType.TASK,
    priority=JiraPriority.HIGH,
)
print(f"Created {result['jira_key']}")

# Update issue
jira.update_issue(
    "PROJECT-123",
    status=JiraStatus.IN_PROGRESS,
)

# Link issues
jira.link_issue("PROJECT-120", "PROJECT-123", "blocks")

# Search
issues = jira.search_issues("assignee=currentUser() ORDER BY created DESC")
for issue in issues:
    print(f"{issue['jira_key']}: {issue['summary']}")

# Sync from Jira to local
sync_result = jira.sync_from_jira(project_id)
print(f"Synced {sync_result['created']} tasks")

# Sync to Jira
sync_result = jira.sync_to_jira(project_id)
print(f"Created {sync_result['created']} issues")
```

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| POST | /assist | Run coding task |
| GET | /providers | List LLM providers |
| POST | /run | Execute code |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /projects | List projects |
| POST | /projects | Create project |
| GET | /projects/{id} | Get project |
| PUT | /projects/{id} | Update project |
| POST | /projects/{id}/tasks | Add task |
| PUT | /projects/{id}/tasks/{tid} | Update task |
| POST | /projects/{id}/milestones | Add milestone |
| POST | /projects/{id}/dependencies | Add dependency |

### Improvements

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /improvements/bugs | List bugs |
| POST | /improvements/bugs | Log bug |
| POST | /improvements/bugs/{id}/fix | Mark fixed |
| GET | /improvements/report | Summary report |

### Process

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /processes/tasks/start | Start tracking |
| POST | /processes/tasks/{id}/complete | Complete & analyze |
| GET | /processes/improvements | Pending improvements |
| POST | /processes/improvements/{id}/approve | Approve |
| POST | /processes/improvements/{id}/implement | Implement |

### Daily

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /daily/summary | Today's summary |
| POST | /daily/completed | Log completed task |
| POST | /daily/plan | Add plan |
| POST | /daily/blockers | Add blocker |
| POST | /daily/send | Send reports |

### Jira

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /jira/issues | Search issues |
| POST | /jira/issues | Create issue |
| PUT | /jira/issues/{key} | Update issue |
| POST | /jira/sync/{project_id}/to | Sync to Jira |
| POST | /jira/sync/{project_id}/from | Sync from Jira |

---

## Web UI

Access at `http://localhost:3000`:

1. **Homepage** - Enter instructions, select files, run tasks
2. **Projects** - View projects, tasks, milestones
3. **Daily** - Daily status summary
4. **Jira** - Issue search (coming soon)

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GITHUB_TOKEN` | GitHub token |
| `JIRA_URL` | Jira instance URL |
| `JIRA_EMAIL` | Jira email |
| `JIRA_API_TOKEN` | Jira API token |
| `SLACK_WEBHOOK_URL` | Slack webhook |