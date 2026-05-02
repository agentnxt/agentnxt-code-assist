"""Runtime configuration for AGenNext Code Assist."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _env(name: str, default: str | None = None) -> str | None:
    """Read AGenNext env vars with backward-compatible AgentNXT fallback."""

    value = os.getenv(name)
    if value is not None:
        return value
    legacy_name = name.replace("AGENNEXT_", "AGENTNXT_", 1)
    if legacy_name != name:
        return os.getenv(legacy_name, default)
    return default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name)
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
    webhook_url: str | None = None
    enable_webhook: bool = False
    smtp_url: str | None = None
    smtp_from_email: str = "agennext-code-assist@localhost"
    smtp_to_email: str | None = None
    enable_smtp: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            model=_env("AGENNEXT_CODE_ASSIST_MODEL", os.getenv("AIDER_MODEL", cls.model)) or cls.model,
            host=_env("AGENNEXT_CODE_ASSIST_HOST", cls.host) or cls.host,
            port=int(_env("AGENNEXT_CODE_ASSIST_PORT", str(cls.port)) or cls.port),
            auto_yes=_env_bool("AGENNEXT_CODE_ASSIST_AUTO_YES", cls.auto_yes),
            auto_commits=_env_bool("AGENNEXT_CODE_ASSIST_AUTO_COMMITS", cls.auto_commits),
            dry_run=_env_bool("AGENNEXT_CODE_ASSIST_DRY_RUN", cls.dry_run),
            workspace_root=Path(
                _env("AGENNEXT_CODE_ASSIST_WORKSPACE", str(cls.workspace_root))
                or str(cls.workspace_root)
            ),
            git_user_name=_env(
                "AGENNEXT_CODE_ASSIST_GIT_USER_NAME", cls.git_user_name
            ) or cls.git_user_name,
            git_user_email=_env(
                "AGENNEXT_CODE_ASSIST_GIT_USER_EMAIL", cls.git_user_email
            ) or cls.git_user_email,
            slack_webhook_url=_env("AGENNEXT_CODE_ASSIST_SLACK_WEBHOOK_URL"),
            enable_slack=_env_bool("AGENNEXT_CODE_ASSIST_ENABLE_SLACK", cls.enable_slack),
            webhook_url=_env("AGENNEXT_CODE_ASSIST_WEBHOOK_URL"),
            enable_webhook=_env_bool("AGENNEXT_CODE_ASSIST_ENABLE_WEBHOOK", cls.enable_webhook),
            smtp_url=_env("AGENNEXT_CODE_ASSIST_SMTP_URL"),
            smtp_from_email=_env("AGENNEXT_CODE_ASSIST_SMTP_FROM_EMAIL", cls.smtp_from_email)
            or cls.smtp_from_email,
            smtp_to_email=_env("AGENNEXT_CODE_ASSIST_SMTP_TO_EMAIL"),
            enable_smtp=_env_bool("AGENNEXT_CODE_ASSIST_ENABLE_SMTP", cls.enable_smtp),
        )

