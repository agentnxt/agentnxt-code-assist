import inspect
import os
from pathlib import Path

import pytest

from agentnxt_code_assist.aider_runner import AiderCodeAssist
from agentnxt_code_assist.schemas import AssistRequest


def test_resolve_files_keeps_relative_files_inside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    files = AiderCodeAssist._resolve_files(repo.resolve(), ["src/app.py"])

    assert files == [(repo / "src/app.py").resolve()]


def test_resolve_files_rejects_path_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError):
        AiderCodeAssist._resolve_files(repo.resolve(), ["../outside.py"])


def test_filter_kwargs_preserves_supported_arguments() -> None:
    def create(*, fnames: list[str], io: object, main_model: object) -> None:
        return None

    filtered = AiderCodeAssist._filter_kwargs(
        {"fnames": [], "io": object(), "main_model": object(), "dry_run": True},
        dict(inspect.signature(create).parameters.items()),
    )

    assert set(filtered) == {"fnames", "io", "main_model"}


def test_environment_for_openai_compatible_request(tmp_path: Path) -> None:
    request = AssistRequest(
        instruction="test",
        repo_path=tmp_path,
        provider="openai-compatible",
        api_key="test-key",
        api_base="https://llm.example.com/v1",
        env_vars={"LITELLM_USER": "agentnxt"},
    )

    env = AiderCodeAssist._environment_for_request(request)

    assert env == {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_API_BASE": "https://llm.example.com/v1",
        "LITELLM_USER": "agentnxt",
    }


def test_environment_for_anthropic_request(tmp_path: Path) -> None:
    request = AssistRequest(
        instruction="test",
        repo_path=tmp_path,
        provider="anthropic",
        api_key="test-key",
        api_base="https://llm.example.com/anthropic",
    )

    env = AiderCodeAssist._environment_for_request(request)

    assert env == {
        "ANTHROPIC_API_KEY": "test-key",
        "ANTHROPIC_BASE_URL": "https://llm.example.com/anthropic",
    }


def test_temporary_env_restores_previous_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTNXT_TEST_ENV", "before")

    with AiderCodeAssist._temporary_env({"AGENTNXT_TEST_ENV": "during", "AGENTNXT_NEW_ENV": "new"}):
        assert os.environ["AGENTNXT_TEST_ENV"] == "during"
        assert os.environ["AGENTNXT_NEW_ENV"] == "new"

    assert os.environ["AGENTNXT_TEST_ENV"] == "before"
    assert "AGENTNXT_NEW_ENV" not in os.environ
