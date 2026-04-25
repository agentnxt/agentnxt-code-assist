"""Aider-backed code assist runner."""

from __future__ import annotations

import contextlib
import inspect
import io
import os
import re
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from agentnxt_code_assist.config import Settings
from agentnxt_code_assist.schemas import AssistRequest, AssistResult


class AiderCodeAssist:
    """Run one-shot coding instructions through Aider's Python API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._run_lock = threading.Lock()

    def run(self, request: AssistRequest) -> AssistResult:
        repo_path = self._resolve_repo(request.repo_path)
        files = self._resolve_files(repo_path, request.files)
        output = io.StringIO()
        env = self._environment_for_request(request)

        try:
            with self._run_lock:
                with (
                    self._temporary_env(env),
                    self._pushd(repo_path),
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(output),
                ):
                    coder = self._create_coder(request, files)
                    result = coder.run(request.instruction)
                    if result:
                        output.write(str(result))
                        output.write("\n")

            return AssistResult(
                ok=True,
                repo_path=str(repo_path),
                files=[str(path) for path in files],
                changed_files=self._changed_files(repo_path),
                output=output.getvalue(),
            )
        except Exception as exc:
            return AssistResult(
                ok=False,
                repo_path=str(repo_path),
                files=[str(path) for path in files],
                changed_files=self._changed_files(repo_path),
                output=output.getvalue(),
                error=str(exc),
            )

    def _create_coder(self, request: AssistRequest, files: list[Path]) -> Any:
        try:
            from aider.coders import Coder
            from aider.io import InputOutput
            from aider.models import Model
        except ImportError as exc:
            raise RuntimeError(
                "aider-chat is not installed. Install this package with `pip install -e .` "
                "or install `aider-chat` in the current environment."
            ) from exc

        model_name = request.model or self.settings.model
        model = Model(model_name)
        io_obj = InputOutput(yes=self._coalesce(request.auto_yes, self.settings.auto_yes))

        requested_kwargs: dict[str, Any] = {
            "fnames": [str(path) for path in files],
            "io": io_obj,
            "auto_commits": self._coalesce(request.auto_commits, self.settings.auto_commits),
            "dry_run": self._coalesce(request.dry_run, self.settings.dry_run),
            "stream": request.stream,
        }

        create_sig = inspect.signature(Coder.create)
        parameters = create_sig.parameters
        if "main_model" in parameters:
            requested_kwargs["main_model"] = model
        else:
            requested_kwargs["model"] = model

        kwargs = self._filter_kwargs(requested_kwargs, parameters)
        return Coder.create(**kwargs)

    @staticmethod
    def _filter_kwargs(kwargs: dict[str, Any], parameters: dict[str, inspect.Parameter]) -> dict[str, Any]:
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()):
            return kwargs
        return {key: value for key, value in kwargs.items() if key in parameters}

    @staticmethod
    def _coalesce(value: bool | None, default: bool) -> bool:
        return default if value is None else value

    @classmethod
    def _environment_for_request(cls, request: AssistRequest) -> dict[str, str]:
        env: dict[str, str] = {}
        provider = (request.provider or "").strip().lower()

        if request.api_key:
            if provider == "anthropic":
                env["ANTHROPIC_API_KEY"] = request.api_key
            else:
                env["OPENAI_API_KEY"] = request.api_key

        if request.api_base:
            if provider == "anthropic":
                env["ANTHROPIC_BASE_URL"] = request.api_base
            else:
                env["OPENAI_API_BASE"] = request.api_base

        for key, value in request.env_vars.items():
            normalized_key = key.strip()
            if not normalized_key:
                continue
            if not cls._is_safe_env_key(normalized_key):
                raise ValueError(f"unsupported environment variable name: {normalized_key}")
            env[normalized_key] = value

        return env

    @staticmethod
    def _is_safe_env_key(key: str) -> bool:
        return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is not None

    @staticmethod
    @contextlib.contextmanager
    def _temporary_env(values: dict[str, str]) -> Iterator[None]:
        previous: dict[str, str | None] = {key: os.environ.get(key) for key in values}
        try:
            for key, value in values.items():
                os.environ[key] = value
            yield
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    @staticmethod
    def _resolve_repo(repo_path: Path) -> Path:
        resolved = repo_path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"repo_path does not exist: {resolved}")
        if not resolved.is_dir():
            raise NotADirectoryError(f"repo_path is not a directory: {resolved}")
        return resolved

    @staticmethod
    def _resolve_files(repo_path: Path, files: list[str]) -> list[Path]:
        resolved_files: list[Path] = []
        for file_name in files:
            candidate = (repo_path / file_name).resolve() if not Path(file_name).is_absolute() else Path(file_name).resolve()
            if not candidate.is_relative_to(repo_path):
                raise ValueError(f"file is outside repo_path: {file_name}")
            resolved_files.append(candidate)
        return resolved_files

    @staticmethod
    def _changed_files(repo_path: Path) -> list[str]:
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return []

        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return []

        changed: list[str] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            changed.append(line[3:] if len(line) > 3 else line.strip())
        return changed

    @staticmethod
    @contextlib.contextmanager
    def _pushd(path: Path) -> Iterator[None]:
        previous = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(previous)
