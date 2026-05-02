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
from agentnxt_code_assist.git_workspace import (
    changed_files as git_changed_files,
    checkout_base_branch,
    configure_git_identity,
    create_or_reset_work_branch,
    ensure_repo_checkout,
    get_current_sha,
    push_branch,
)
from agentnxt_code_assist.schemas import AssistRequest, AssistResult, CheckResult


class AiderCodeAssist:
    """Run one-shot coding instructions through Aider's Python API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        self._run_lock = threading.Lock()

    def run(self, request: AssistRequest) -> AssistResult:
        repo_path = self._prepare_repo(request)
        files = self._resolve_files(repo_path, request.files)
        output = io.StringIO()
        env = self._environment_for_request(request)
        before_sha = self._safe_current_sha(repo_path)
        checks: list[CheckResult] = []
        pushed = False

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

            checks = self._run_checks(repo_path, request.checks)
            checks_ok = all(check.exit_code == 0 for check in checks)
            if request.push and checks_ok and request.work_branch:
                push_branch(repo_path, request.work_branch)
                pushed = True
            elif request.push and not checks_ok:
                output.write("Skipping push because one or more checks failed.\n")

            return AssistResult(
                ok=checks_ok,
                repo_path=str(repo_path),
                files=[str(path) for path in files],
                changed_files=self._changed_files(repo_path),
                output=output.getvalue(),
                error=None if checks_ok else "one or more checks failed",
                base_branch=request.base_branch if self._is_managed_checkout(request) else None,
                work_branch=request.work_branch,
                before_sha=before_sha,
                after_sha=self._safe_current_sha(repo_path),
                checks=checks,
                pushed=pushed,
                pr_url=None,
            )
        except Exception as exc:
            return AssistResult(
                ok=False,
                repo_path=str(repo_path),
                files=[str(path) for path in files],
                changed_files=self._changed_files(repo_path),
                output=output.getvalue(),
                error=str(exc),
                base_branch=request.base_branch if self._is_managed_checkout(request) else None,
                work_branch=request.work_branch,
                before_sha=before_sha,
                after_sha=self._safe_current_sha(repo_path),
                checks=checks,
                pushed=pushed,
                pr_url=None,
            )

    def _prepare_repo(self, request: AssistRequest) -> Path:
        if self._is_managed_checkout(request):
            workspace_root = request.workspace_root or self.settings.workspace_root
            repo_path = ensure_repo_checkout(
                repo_url=request.repo_url,
                repo_full_name=request.repo_full_name,
                workspace_root=workspace_root,
            )
            configure_git_identity(
                repo_path,
                user_name=self.settings.git_user_name,
                user_email=self.settings.git_user_email,
            )
            checkout_base_branch(repo_path, request.base_branch)
            if not request.work_branch:
                raise ValueError("managed checkout requires work_branch")
            create_or_reset_work_branch(repo_path, request.work_branch, request.base_branch)
            return repo_path

        if request.repo_path is None:
            raise ValueError("repo_path is required in local mode")
        return self._resolve_repo(request.repo_path)

    @staticmethod
    def _is_managed_checkout(request: AssistRequest) -> bool:
        return bool(request.repo_url or request.repo_full_name)

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
        return git_changed_files(repo_path)

    @staticmethod
    def _safe_current_sha(repo_path: Path) -> str | None:
        try:
            return get_current_sha(repo_path)
        except Exception:
            return None

    @staticmethod
    def _run_checks(repo_path: Path, checks: list[str]) -> list[CheckResult]:
        results: list[CheckResult] = []
        for command in checks:
            proc = subprocess.run(
                command,
                cwd=repo_path,
                shell=True,
                check=False,
                capture_output=True,
                text=True,
            )
            results.append(
                CheckResult(
                    command=command,
                    exit_code=proc.returncode,
                    stdout_tail=proc.stdout[-4000:],
                    stderr_tail=proc.stderr[-4000:],
                )
            )
        return results

    @staticmethod
    @contextlib.contextmanager
    def _pushd(path: Path) -> Iterator[None]:
        previous = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(previous)
