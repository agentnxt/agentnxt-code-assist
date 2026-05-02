"""Command line interface for AgentNXT Code Assist."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from agentnxt_code_assist.aider_runner import AiderCodeAssist
from agentnxt_code_assist.config import Settings
from agentnxt_code_assist.schemas import AssistRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentnxt-code-assist")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one code-assist instruction")
    run_parser.add_argument("instruction", help="Natural language coding instruction")
    repo_group = run_parser.add_mutually_exclusive_group(required=True)
    repo_group.add_argument("--repo", dest="repo_path", type=Path, help="Existing target repository path")
    repo_group.add_argument("--repo-url", help="Git repository URL to clone/fetch into the managed workspace")
    repo_group.add_argument("--repo-full-name", help="GitHub repository full name, for example AGenNext/Platform")
    run_parser.add_argument("--base-branch", default="main", help="Base branch for managed checkout mode")
    run_parser.add_argument("--work-branch", help="Work branch for managed checkout mode")
    run_parser.add_argument("--workspace-root", type=Path, help="Managed checkout workspace root")
    run_parser.add_argument("--issue", dest="issue_number", type=int, help="Issue number for default branch naming")
    run_parser.add_argument("--push", action="store_true", help="Push the managed checkout work branch after successful checks")
    run_parser.add_argument("--open-pr", action="store_true", help="Reserved for future PR creation support; requires --push")
    run_parser.add_argument("--check", action="append", default=[], help="Post-edit check command to run inside the repo")
    run_parser.add_argument("--file", action="append", default=[], help="File to add to Aider chat")
    run_parser.add_argument("--model", help="Aider/LiteLLM model name")
    run_parser.add_argument("--dry-run", action="store_true", help="Ask Aider to avoid writing files")
    run_parser.add_argument("--auto-commits", action="store_true", help="Allow Aider to commit edits")
    run_parser.add_argument("--no-auto-yes", action="store_true", help="Do not auto-confirm Aider prompts")
    run_parser.add_argument("--stream", action="store_true", help="Stream model output when supported by Aider")
    run_parser.add_argument("--json", action="store_true", help="Print the full JSON result")

    serve_parser = subparsers.add_parser("serve", help="Start the HTTP API")
    serve_parser.add_argument("--host", help="Bind host")
    serve_parser.add_argument("--port", type=int, help="Bind port")

    return parser


def run_command(args: argparse.Namespace, settings: Settings) -> int:
    assistant = AiderCodeAssist(settings)
    result = assistant.run(
        AssistRequest(
            instruction=args.instruction,
            repo_path=args.repo_path,
            repo_url=args.repo_url,
            repo_full_name=args.repo_full_name,
            base_branch=args.base_branch,
            work_branch=args.work_branch,
            workspace_root=args.workspace_root,
            issue_number=args.issue_number,
            push=args.push,
            open_pr=args.open_pr,
            checks=args.check,
            files=args.file,
            model=args.model,
            dry_run=True if args.dry_run else None,
            auto_commits=True if args.auto_commits else None,
            auto_yes=False if args.no_auto_yes else None,
            stream=args.stream,
        )
    )

    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        if result.output:
            print(result.output.rstrip())
        if result.repo_path:
            print(f"Repository: {result.repo_path}")
        if result.work_branch:
            print(f"Work branch: {result.work_branch}")
        if result.changed_files:
            print("Changed files:")
            for path in result.changed_files:
                print(f"  {path}")
        if result.checks:
            print("Checks:")
            for check in result.checks:
                print(f"  {check.command}: exit {check.exit_code}")
        if result.pushed:
            print("Pushed branch: yes")
        if result.error:
            print(f"Error: {result.error}")

    return 0 if result.ok else 1


def serve_command(args: argparse.Namespace, settings: Settings) -> int:
    host = args.host or settings.host
    port = args.port or settings.port
    uvicorn.run("agentnxt_code_assist.server:app", host=host, port=port, reload=False)
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "run":
        return run_command(args, settings)
    if args.command == "serve":
        return serve_command(args, settings)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
