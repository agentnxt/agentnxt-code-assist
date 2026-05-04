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

from agennext_codeassist.change_log import append_change_log, build_change_log
from agennext_codeassist.check_planner import planned_checks
from agennext_codeassist.config import Settings
from agennext_codeassist.context_fetcher import fetch_target_context
from agennext_codeassist.dependency_audit import audit_dependencies
from agennext_codeassist.email_notifier import notify_email
from agennext_codeassist.git_workspace import (
    changed_files as git_changed_files,
    checkout_base_branch,
    configure_git_identity,
    create_or_reset_work_branch,
    ensure_repo_checkout,
    get_current_sha,
    push_branch,
)
from agennext_codeassist.memory_store import append_memory, memory_prompt_block, read_memory
from agennext_codeassist.rag_knowledge import load_rag_context
from agennext_codeassist.runner_client import RunnerClient
from agennext_codeassist.audit_trace import write_audit_trace
from agennext_codeassist.repo_audit import audit_repo
from agennext_codeassist.schemas import AssistRequest, AssistResult, CheckResult, NotificationResult, RepoAnomalyResult
from agennext_codeassist.skill_registry import skill_prompt_block
from agennext_codeassist.slack_notifier import notify_slack
from agennext_codeassist.webhook_notifier import notify_webhook


_SEVERITY_RANK = {"info": 1, "warning": 2, "error": 3}


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
        anomalies = self._collect_anomalies(repo_path, request)
        hydrated_context = self._hydrate_context(request, output)
        memory_context = self._memory_context(repo_path, request, output)
        rag_context = self._rag_context(repo_path, request, output)
        instruction = self._compose_instruction(
            request.instruction,
            hydrated_context,
            anomalies,
            skill_prompt_block(request.skills),
            memory_context,
            rag_context,
        )

        run_id = request.runner_run_id or f"run-{os.getpid()}-{threading.get_ident()}"
        runner_decision = None
        if request.run_mode == "production_change":
            payload = {"agent":"agennext-code-assist","action":"repo.write","resource":f"repository:{request.repo_full_name or repo_path.name}","branch":request.work_branch,"reason":"implement requested code change","requested_update_mode":"github-api","context":{"run_id":run_id}}
            runner_decision = RunnerClient().request_capability(payload)
            if not runner_decision.allowed:
                result = self._result(request=request, repo_path=repo_path, files=files, output=output.getvalue(), error=runner_decision.reason or "runner denied capability", before_sha=before_sha, checks=checks, anomalies=anomalies, pushed=pushed, ok=False, hydrated_context=hydrated_context, rag_context=rag_context)
                result.status="denied"
                result.run_id=run_id
                result.capability_id=runner_decision.capability_id
                result.run_id = run_id
            if runner_decision:
                result.capability_id = runner_decision.capability_id
            if request.run_mode == "production_change":
                try:
                    j,m=write_audit_trace(repo_path, run_id, {"run_mode": request.run_mode, "repo_target": request.repo_full_name or str(repo_path), "base_branch": request.base_branch, "work_branch": request.work_branch, "result": "ok" if result.ok else "failed", "changed_files": result.changed_files})
                    result.audit_trace_json=j
                    result.audit_trace_md=m
                except Exception as exc:
                    result.ok=False
                    result.error=result.error or f"audit trace write failed: {exc}"
            return self._finalize(request, repo_path, result)

        try:
            if self._fails_anomaly_gate(anomalies, request.fail_on_anomaly_severity):
                result = self._result(
                    request=request,
                    repo_path=repo_path,
                    files=files,
                    output=output.getvalue(),
                    error=f"anomaly gate failed at severity {request.fail_on_anomaly_severity}",
                    before_sha=before_sha,
                    checks=checks,
                    anomalies=anomalies,
                    pushed=pushed,
                    ok=False,
                    hydrated_context=hydrated_context,
                    rag_context=rag_context,
                )
                return self._finalize(request, repo_path, result)

            with self._run_lock:
                with (
                    self._temporary_env(env),
                    self._pushd(repo_path),
                    contextlib.redirect_stdout(output),
                    contextlib.redirect_stderr(output),
                ):
                    coder = self._create_coder(request, files)
                    result = coder.run(instruction)
                    if result:
                        output.write(str(result))
                        output.write("\n")

            check_commands = planned_checks(repo_path, request.checks)
            checks = self._run_checks(repo_path, check_commands)
            checks_ok = all(check.exit_code == 0 for check in checks)
            if request.push and checks_ok and request.work_branch:
                push_branch(repo_path, request.work_branch)
                pushed = True
            elif request.push and not checks_ok:
                output.write("Skipping push because one or more checks failed.\n")

            result = self._result(
                request=request,
                repo_path=repo_path,
                files=files,
                output=output.getvalue(),
                error=None if checks_ok else "one or more checks failed",
                before_sha=before_sha,
                checks=checks,
                anomalies=anomalies,
                pushed=pushed,
                ok=checks_ok,
                hydrated_context=hydrated_context,
                rag_context=rag_context,
            )
            return self._finalize(request, repo_path, result)
        except Exception as exc:
            result = self._result(
                request=request,
                repo_path=repo_path,
                files=files,
                output=output.getvalue(),
                error=str(exc),
                before_sha=before_sha,
                checks=checks,
                anomalies=anomalies,
                pushed=pushed,
                ok=False,
                hydrated_context=hydrated_context,
                rag_context=rag_context,
            )
            return self._finalize(request, repo_path, result)

    def _result(
        self,
        *,
        request: AssistRequest,
        repo_path: Path,
        files: list[Path],
        output: str,
        error: str | None,
        before_sha: str | None,
        checks: list[CheckResult],
        anomalies: list[RepoAnomalyResult],
        pushed: bool,
        ok: bool,
        hydrated_context: str | None,
        rag_context: str | None,
    ) -> AssistResult:
        changed_files = self._changed_files(repo_path)
        after_sha = self._safe_current_sha(repo_path)
        change_log = build_change_log(
            objective=request.instruction,
            repo_full_name=request.repo_full_name,
            target_url=request.target_url,
            target_kind=request.target_kind,
            base_branch=request.base_branch if self._is_managed_checkout(request) else None,
            work_branch=request.work_branch,
            before_sha=before_sha,
            after_sha=after_sha,
            changed_files=changed_files,
            checks=checks,
            anomalies=anomalies,
            error=error,
            pushed=pushed,
        )
        change_log_path: str | None = None
        result_output = output
        if request.write_change_log:
            try:
                written_path = append_change_log(repo_path, request.change_log_path, change_log)
                change_log_path = str(written_path.relative_to(repo_path))
                if change_log_path not in changed_files:
                    changed_files = self._changed_files(repo_path)
            except Exception as exc:
                result_output = result_output + f"\nFailed to write change log: {exc}\n"
                error = error or f"failed to write change log: {exc}"
                ok = False

        memory_path = request.memory_path if request.enable_memory else None
        return AssistResult(
            ok=ok,
            repo_path=str(repo_path),
            files=[str(path) for path in files],
            changed_files=changed_files,
            output=result_output,
            error=error,
            base_branch=request.base_branch if self._is_managed_checkout(request) else None,
            work_branch=request.work_branch,
            before_sha=before_sha,
            after_sha=after_sha,
            checks=checks,
            pushed=pushed,
            pr_url=None,
            target_url=request.target_url,
            target_kind=request.target_kind,
            repo_full_name=request.repo_full_name,
            issue_number=request.issue_number,
            pull_number=request.pull_number,
            discussion_number=request.discussion_number,
            hydrated_context=hydrated_context,
            rag_context=rag_context,
            memory_path=memory_path,
            anomalies=anomalies,
            change_log=change_log,
            change_log_path=change_log_path,
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
        return bool(request.repo_url or request.repo_full_name or request.target_url)

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
    def _collect_anomalies(repo_path: Path, request: AssistRequest) -> list[RepoAnomalyResult]:
        anomalies: list[RepoAnomalyResult] = []
        if request.audit_repo:
            anomalies.extend(
                RepoAnomalyResult(
                    severity=item.severity,
                    code=item.code,
                    message=item.message,
                    evidence=item.evidence,
                )
                for item in audit_repo(repo_path)
            )
        if request.audit_dependencies:
            anomalies.extend(
                RepoAnomalyResult(
                    severity=item.severity,
                    code=item.code,
                    message=item.message,
                    evidence=item.evidence,
                )
                for item in audit_dependencies(repo_path, check_upstream=request.check_upstream_versions)
            )
        return anomalies

    @staticmethod
    def _hydrate_context(request: AssistRequest, output: io.StringIO) -> str | None:
        if not request.hydrate_context:
            return None
        try:
            context = fetch_target_context(
                repo_full_name=request.repo_full_name,
                target_kind=request.target_kind,
                issue_number=request.issue_number,
                pull_number=request.pull_number,
                discussion_number=request.discussion_number,
                target_url=request.target_url,
            )
        except Exception as exc:
            output.write(f"Failed to hydrate target context: {exc}\n")
            return None
        return context.to_prompt_block() if context else None

    @staticmethod
    def _memory_context(repo_path: Path, request: AssistRequest, output: io.StringIO) -> str | None:
        if not request.enable_memory:
            return None
        try:
            return memory_prompt_block(read_memory(repo_path, request.memory_path))
        except Exception as exc:
            output.write(f"Failed to read memory: {exc}\n")
            return None

    @staticmethod
    def _rag_context(repo_path: Path, request: AssistRequest, output: io.StringIO) -> str | None:
        if not request.rag_paths and not request.rag_urls:
            return None
        try:
            return load_rag_context(
                repo_path=repo_path,
                query=request.instruction,
                paths=request.rag_paths,
                remote_urls=request.rag_urls,
                max_chars=request.rag_max_chars,
            )
        except Exception as exc:
            output.write(f"Failed to load RAG context: {exc}\n")
            return None

    @staticmethod
    def _compose_instruction(
        instruction: str,
        hydrated_context: str | None,
        anomalies: list[RepoAnomalyResult],
        skills_context: str | None,
        memory_context: str | None,
        rag_context: str | None,
    ) -> str:
        parts = [instruction.strip()]
        if skills_context:
            parts.append("\n\n" + skills_context)
        if memory_context:
            parts.append("\n\n" + memory_context)
        if rag_context:
            parts.append("\n\n" + rag_context)
        if hydrated_context:
            parts.append("\n\n## Hydrated target context\n" + hydrated_context)
        if anomalies:
            lines = ["\n\n## Repository/dependency anomalies to consider"]
            for anomaly in anomalies:
                evidence = f" Evidence: {anomaly.evidence}" if anomaly.evidence else ""
                lines.append(f"- [{anomaly.severity}] {anomaly.code}: {anomaly.message}{evidence}")
            parts.append("\n".join(lines))
        return "".join(parts)

    @staticmethod
    def _fails_anomaly_gate(anomalies: list[RepoAnomalyResult], threshold: str | None) -> bool:
        if threshold is None:
            return False
        threshold_rank = _SEVERITY_RANK[threshold]
        return any(_SEVERITY_RANK.get(anomaly.severity, 0) >= threshold_rank for anomaly in anomalies)

    def _finalize(self, request: AssistRequest, repo_path: Path, result: AssistResult) -> AssistResult:
        if request.enable_memory and request.update_memory:
            try:
                written_path = append_memory(repo_path, request.memory_path, result)
                result.memory_path = str(written_path.relative_to(repo_path))
                if result.memory_path not in result.changed_files:
                    result.changed_files = self._changed_files(repo_path)
            except Exception as exc:
                result.output = result.output + f"\nFailed to update memory: {exc}\n"
                result.error = result.error or f"failed to update memory: {exc}"
                result.ok = False
        return self._maybe_notify(request, result)

    def _maybe_notify(self, request: AssistRequest, result: AssistResult) -> AssistResult:
        result = self._maybe_notify_slack(request, result)
        result = self._maybe_notify_webhook(request, result)
        result = self._maybe_notify_smtp(request, result)
        return result

    def _maybe_notify_slack(self, request: AssistRequest, result: AssistResult) -> AssistResult:
        if not (request.notify_slack or self.settings.enable_slack):
            return result
        notification = notify_slack(request.slack_webhook_url or self.settings.slack_webhook_url, result)
        result.slack = NotificationResult(sent=notification.sent, error=notification.error)
        if notification.error:
            result.output = result.output + f"\nSlack notification failed: {notification.error}\n"
        return result

    def _maybe_notify_webhook(self, request: AssistRequest, result: AssistResult) -> AssistResult:
        if not (request.notify_webhook or self.settings.enable_webhook):
            return result
        notification = notify_webhook(request.webhook_url or self.settings.webhook_url, result)
        result.webhook = NotificationResult(sent=notification.sent, error=notification.error)
        if notification.error:
            result.output = result.output + f"\nWebhook notification failed: {notification.error}\n"
        return result

    def _maybe_notify_smtp(self, request: AssistRequest, result: AssistResult) -> AssistResult:
        if not (request.notify_smtp or self.settings.enable_smtp):
            return result
        notification = notify_email(
            smtp_url=request.smtp_url or self.settings.smtp_url,
            from_email=request.smtp_from_email or self.settings.smtp_from_email,
            to_email=request.smtp_to_email or self.settings.smtp_to_email,
            result=result,
        )
        result.smtp = NotificationResult(sent=notification.sent, error=notification.error)
        if notification.error:
            result.output = result.output + f"\nSMTP notification failed: {notification.error}\n"
        return result

    @staticmethod
    @contextlib.contextmanager
    def _pushd(path: Path) -> Iterator[None]:
        previous = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(previous)
