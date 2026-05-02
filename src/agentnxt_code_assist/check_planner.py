"""Plan standard validation commands for a checked-out repository."""

from __future__ import annotations

import json
from pathlib import Path


def planned_checks(repo_path: Path, requested: list[str]) -> list[str]:
    """Expand check presets into concrete commands.

    Supported presets:
    - dependency
    - typecheck
    - lint
    - unit
    - integration
    - smoke
    - docker
    - docker-smoke
    - publishable
    - production
    - all

    Unknown values are treated as literal shell commands for backwards compatibility.
    """

    commands: list[str] = []
    for item in requested:
        normalized = item.strip().lower()
        if normalized == "all":
            normalized = "production"
        if normalized == "production":
            for preset in [
                "dependency",
                "typecheck",
                "lint",
                "unit",
                "integration",
                "smoke",
                "docker",
                "docker-smoke",
                "publishable",
            ]:
                commands.extend(_preset_commands(repo_path, preset))
            continue
        preset = _preset_commands(repo_path, normalized)
        commands.extend(preset if preset else [item])
    return _dedupe(commands)


def _preset_commands(repo_path: Path, preset: str) -> list[str]:
    package = _read_package_json(repo_path)
    scripts = set(package.get("scripts", {}).keys()) if package else set()

    if preset == "dependency":
        return _dependency_commands(repo_path)
    if preset == "typecheck":
        return _script_or_empty(scripts, "type-check") or _script_or_empty(scripts, "typecheck")
    if preset == "lint":
        return _script_or_empty(scripts, "lint")
    if preset == "build":
        return _script_or_empty(scripts, "build")
    if preset == "unit":
        return _first_existing_script(scripts, ["test:unit", "unit", "test"])
    if preset == "integration":
        return _first_existing_script(scripts, ["test:integration", "integration", "e2e", "test:e2e"])
    if preset == "smoke":
        return _first_existing_script(scripts, ["smoke", "test:smoke", "build"])
    if preset == "docker":
        return _docker_commands(repo_path)
    if preset == "docker-smoke":
        return _docker_smoke_commands(repo_path)
    if preset == "publishable":
        return _publishable_commands(repo_path)
    return []


def _dependency_commands(repo_path: Path) -> list[str]:
    if (repo_path / "package-lock.json").exists():
        return ["npm ci --dry-run"]
    if (repo_path / "pnpm-lock.yaml").exists():
        return ["pnpm install --frozen-lockfile --offline"]
    if (repo_path / "yarn.lock").exists():
        return ["yarn install --frozen-lockfile --offline"]
    if (repo_path / "pyproject.toml").exists() or (repo_path / "requirements.txt").exists():
        return ["python -m pip check"]
    return []


def _docker_commands(repo_path: Path) -> list[str]:
    if (repo_path / "Dockerfile").exists():
        return ["docker build --pull -t agennext-code-assist-local:ci ."]
    if (repo_path / "docker-compose.yml").exists() or (repo_path / "compose.yml").exists():
        return ["docker compose config"]
    return []


def _docker_smoke_commands(repo_path: Path) -> list[str]:
    commands: list[str] = []
    if (repo_path / "Dockerfile").exists():
        commands.append(
            "docker run --rm --name agennext-code-assist-smoke agennext-code-assist-local:ci --help"
        )
    if (repo_path / "docker-compose.yml").exists() or (repo_path / "compose.yml").exists():
        commands.append("docker compose config --quiet")
    return commands


def _publishable_commands(repo_path: Path) -> list[str]:
    commands: list[str] = []
    if (repo_path / "Dockerfile").exists():
        commands.extend(
            [
                "docker image inspect agennext-code-assist-local:ci >/dev/null",
                "docker tag agennext-code-assist-local:ci agennext/code-assist:ci-smoke",
                "docker tag agennext-code-assist-local:ci ghcr.io/agennext/code-assist:ci-smoke",
            ]
        )
    return commands


def _script_or_empty(scripts: set[str], name: str) -> list[str]:
    return [f"npm run {name}"] if name in scripts else []


def _first_existing_script(scripts: set[str], names: list[str]) -> list[str]:
    for name in names:
        if name in scripts:
            return [f"npm run {name}"]
    return []


def _read_package_json(repo_path: Path) -> dict[str, object] | None:
    path = repo_path / "package.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _dedupe(commands: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for command in commands:
        if command and command not in seen:
            seen.add(command)
            deduped.append(command)
    return deduped
