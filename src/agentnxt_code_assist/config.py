"""Runtime configuration for AgentNXT Code Assist."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    model: str = "gpt-4o"
    host: str = "127.0.0.1"
    port: int = 8090
    auto_yes: bool = True
    auto_commits: bool = False
    dry_run: bool = False
    workspace_root: Path = Path("/srv/agennext/code-assist/workspaces")
    git_user_name: str = "agennext-code-assist"
    git_user_email: str = "code-assist@agennext.local"
    slack_webhook_url: str | None = None
    enable_slack: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            model=os.getenv("AGENTNXT_CODE_ASSIST_MODEL", os.getenv("AIDER_MODEL", cls.model)),
            host=os.getenv("AGENTNXT_CODE_ASSIST_HOST", cls.host),
            port=int(os.getenv("AGENTNXT_CODE_ASSIST_PORT", str(cls.port))),
            auto_yes=_env_bool("AGENTNXT_CODE_ASSIST_AUTO_YES", cls.auto_yes),
            auto_commits=_env_bool("AGENTNXT_CODE_ASSIST_AUTO_COMMITS", cls.auto_commits),
            dry_run=_env_bool("AGENTNXT_CODE_ASSIST_DRY_RUN", cls.dry_run),
            workspace_root=Path(
                os.getenv("AGENTNXT_CODE_ASSIST_WORKSPACE", str(cls.workspace_root))
            ),
            git_user_name=os.getenv(
                "AGENTNXT_CODE_ASSIST_GIT_USER_NAME", cls.git_user_name
            ),
            git_user_email=os.getenv(
                "AGENTNXT_CODE_ASSIST_GIT_USER_EMAIL", cls.git_user_email
            ),
            slack_webhook_url=os.getenv("AGENTNXT_CODE_ASSIST_SLACK_WEBHOOK_URL"),
            enable_slack=_env_bool("AGENTNXT_CODE_ASSIST_ENABLE_SLACK", cls.enable_slack),
        )

