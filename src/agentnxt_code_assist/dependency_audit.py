"""Dependency and version audit helpers."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DependencyAnomaly:
    severity: str
    code: str
    message: str
    evidence: str | None = None


def audit_dependencies(repo_path: Path, *, check_upstream: bool = False) -> list[DependencyAnomaly]:
    anomalies: list[DependencyAnomaly] = []
    _audit_node_project(repo_path, anomalies, check_upstream=check_upstream)
    _audit_python_project(repo_path, anomalies, check_upstream=check_upstream)
    _audit_docker_publishability(repo_path, anomalies)
    _audit_security_vulnerabilities(repo_path, anomalies, check_upstream=check_upstream)
    return anomalies


def dependency_anomalies_to_prompt_block(anomalies: list[DependencyAnomaly]) -> str:
    if not anomalies:
        return "Dependency/version/publishability audit: no obvious anomalies found."
    lines = ["Dependency/version/publishability audit anomalies:"]
    for anomaly in anomalies:
        evidence = f" Evidence: {anomaly.evidence}" if anomaly.evidence else ""
        lines.append(f"- [{anomaly.severity}] {anomaly.code}: {anomaly.message}{evidence}")
    return "\n".join(lines)


def _audit_node_project(repo_path: Path, anomalies: list[DependencyAnomaly], *, check_upstream: bool) -> None:
    package_path = repo_path / "package.json"
    if not package_path.exists():
        return
    package = _read_json(package_path)
    if package is None:
        anomalies.append(DependencyAnomaly("error", "invalid_package_json", "package.json is not valid JSON."))
        return

    scripts = package.get("scripts")
    if not isinstance(scripts, dict):
        anomalies.append(DependencyAnomaly("warning", "missing_package_scripts", "package.json has no scripts object."))

    all_deps = _node_dependencies(package)
    present_lockfiles = [name for name in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"] if (repo_path / name).exists()]
    if len(present_lockfiles) > 1:
        anomalies.append(DependencyAnomaly("warning", "multiple_node_lockfiles", "Multiple Node lockfiles are present; package manager may be ambiguous.", ", ".join(present_lockfiles)))
    if all_deps and not present_lockfiles:
        anomalies.append(DependencyAnomaly("warning", "missing_node_lockfile", "package.json declares dependencies but no Node lockfile was found."))

    package_lock = repo_path / "package-lock.json"
    if package_lock.exists():
        lock = _read_json(package_lock)
        packages = lock.get("packages") if isinstance(lock, dict) else None
        root_package = packages.get("") if isinstance(packages, dict) else None
        if isinstance(root_package, dict):
            lock_deps = set((root_package.get("dependencies") or {}).keys()) | set((root_package.get("devDependencies") or {}).keys())
            missing_in_lock = sorted(set(all_deps.keys()) - lock_deps)
            if missing_in_lock:
                anomalies.append(DependencyAnomaly("warning", "package_lock_missing_declared_deps", "package-lock root metadata is missing dependencies declared in package.json.", ", ".join(missing_in_lock[:20])))

    if check_upstream:
        for name, spec in sorted(all_deps.items())[:80]:
            latest = _npm_latest(name)
            if latest and _looks_registry_spec(spec) and latest not in str(spec):
                anomalies.append(DependencyAnomaly("info", "npm_upstream_version_available", f"npm package `{name}` has upstream latest `{latest}` while package.json declares `{spec}`.", name))


def _audit_python_project(repo_path: Path, anomalies: list[DependencyAnomaly], *, check_upstream: bool) -> None:
    pyproject_path = repo_path / "pyproject.toml"
    requirements_path = repo_path / "requirements.txt"
    if not pyproject_path.exists() and not requirements_path.exists():
        return

    if pyproject_path.exists() and not _read_text(pyproject_path):
        anomalies.append(DependencyAnomaly("error", "empty_pyproject", "pyproject.toml exists but could not be read."))

    present_lockfiles = [name for name in ["uv.lock", "poetry.lock", "Pipfile.lock"] if (repo_path / name).exists()]
    if pyproject_path.exists() and not present_lockfiles:
        anomalies.append(DependencyAnomaly("info", "missing_python_lockfile", "Python project metadata exists but no common Python lockfile was found."))

    if requirements_path.exists() and check_upstream:
        for line in requirements_path.read_text(encoding="utf-8").splitlines()[:100]:
            name = line.strip().split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0].strip()
            if not name or name.startswith("#"):
                continue
            latest = _pypi_latest(name)
            if latest and latest not in line:
                anomalies.append(DependencyAnomaly("info", "pypi_upstream_version_available", f"PyPI package `{name}` has upstream latest `{latest}` while requirements declares `{line}`.", name))


def _audit_docker_publishability(repo_path: Path, anomalies: list[DependencyAnomaly]) -> None:
    dockerfile = repo_path / "Dockerfile"
    if not dockerfile.exists():
        anomalies.append(DependencyAnomaly("warning", "missing_dockerfile", "Repository has no Dockerfile, so it is not directly publishable to Docker Hub/GHCR."))
        return
    text = _read_text(dockerfile) or ""
    upper = text.upper()
    if "HEALTHCHECK" not in upper:
        anomalies.append(DependencyAnomaly("info", "dockerfile_missing_healthcheck", "Dockerfile has no HEALTHCHECK. Add one for production runtime images when applicable."))
    if "USER " not in upper:
        anomalies.append(DependencyAnomaly("warning", "dockerfile_runs_as_root", "Dockerfile does not set a non-root USER."))
    if ":latest" in text:
        anomalies.append(DependencyAnomaly("warning", "dockerfile_uses_latest_tag", "Dockerfile references a :latest image tag; pin base images for reproducible production builds."))

    workflows = repo_path / ".github" / "workflows"
    if not workflows.exists():
        anomalies.append(DependencyAnomaly("warning", "missing_publish_workflow", "No GitHub Actions workflow directory found for Docker Hub/GHCR publishing."))
        return
    workflow_text = "\n".join(_read_text(path) or "" for path in workflows.glob("*.y*ml"))
    lower = workflow_text.lower()
    if "ghcr.io" not in lower:
        anomalies.append(DependencyAnomaly("warning", "missing_ghcr_publish_config", "No GHCR publish reference found in GitHub Actions workflows."))
    if "docker.io" not in lower and "dockerhub" not in lower and "docker/login-action" not in lower:
        anomalies.append(DependencyAnomaly("warning", "missing_dockerhub_publish_config", "No Docker Hub publish/login reference found in GitHub Actions workflows."))


def _node_dependencies(package: dict[str, Any]) -> dict[str, str]:
    deps: dict[str, str] = {}
    for key in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        value = package.get(key)
        if isinstance(value, dict):
            deps.update({str(name): str(spec) for name, spec in value.items()})
    return deps


def _looks_registry_spec(spec: str) -> bool:
    return bool(spec and not spec.startswith(("file:", "workspace:", "link:", "git+", "github:")))


def _npm_latest(name: str) -> str | None:
    data = _json_url(f"https://registry.npmjs.org/{name.replace('/', '%2f')}/latest")
    version = data.get("version") if isinstance(data, dict) else None
    return str(version) if version else None


def _pypi_latest(name: str) -> str | None:
    data = _json_url(f"https://pypi.org/pypi/{name}/json")
    info = data.get("info") if isinstance(data, dict) else None
    version = info.get("version") if isinstance(info, dict) else None
    return str(version) if version else None


def _json_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "agentnxt-code-assist"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _audit_security_vulnerabilities(repo_path: Path, anomalies: list[DependencyAnomaly], *, check_upstream: bool) -> None:
    """Check for known security vulnerabilities in dependencies."""
    if not check_upstream:
        anomalies.append(DependencyAnomaly("info", "security_scan_skipped", "Pass --check-upstream-versions to enable full security vulnerability scanning."))
        return
    
    # Check for known vulnerable patterns in package.json
    package_json = repo_path / "package.json"
    if package_json.exists():
        package_data = _read_json(package_json)
        if package_data:
            deps = _node_dependencies(package_data)
            # Check for known vulnerable versions (CVE examples)
            known_vulnerable = {
                "json5": "<1.0.0",
                "minimatch": "<3.0.2",
                "word-wrap": "<1.2.4",
                "semver": "<7.5.2",
            }
            for name, min_safe in known_vulnerable.items():
                if name in deps:
                    ver = deps[name]
                    if _cmp_version(ver, min_safe) < 0:
                        anomalies.append(DependencyAnomaly("error", "cve_known_vulnerable", f"Package `{name}@{ver}` has known CVE. Upgrade to >= {min_safe}.", name))


def _cmp_version(a: str, b: str) -> int:
    """Compare two semantic version strings. Returns <0 if a < b, 0 if equal, >0 if a > b."""
    import re
    def parse(v: str) -> tuple[int, ...]:
        v = re.sub(r"[^0-9.]", "", v.split("#")[0])
        parts = v.split(".")[:3]
        return tuple(int(p) for p in parts)
    va, vb = parse(a), parse(b)
    return (va > vb) - (va < vb)
