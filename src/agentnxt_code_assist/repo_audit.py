"""Lightweight repository audit helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoAnomaly:
    severity: str
    code: str
    message: str
    evidence: str | None = None


def audit_repo(repo_path: Path) -> list[RepoAnomaly]:
    anomalies: list[RepoAnomaly] = []
    readme = _read_text(repo_path / "README.md")
    package_json = _read_json(repo_path / "package.json")

    if not readme:
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="missing_readme",
                message="README.md is missing or empty.",
            )
        )
        return anomalies

    lower_readme = readme.lower()

    _check_path_claims(repo_path, readme, anomalies)
    _check_script_claims(package_json, readme, anomalies)
    _check_nextjs_claims(repo_path, lower_readme, anomalies)
    _check_platform_architecture_claims(repo_path, lower_readme, anomalies)
    _check_old_branding(repo_path, readme, anomalies)
    _check_secrets(repo_path, anomalies)

    return anomalies


def anomalies_to_prompt_block(anomalies: list[RepoAnomaly]) -> str:
    if not anomalies:
        return "Repository audit: no obvious README/code anomalies found."
    lines = ["Repository audit anomalies:"]
    for anomaly in anomalies:
        evidence = f" Evidence: {anomaly.evidence}" if anomaly.evidence else ""
        lines.append(
            f"- [{anomaly.severity}] {anomaly.code}: {anomaly.message}{evidence}"
        )
    return "\n".join(lines)


def _check_path_claims(repo_path: Path, readme: str, anomalies: list[RepoAnomaly]) -> None:
    claimed_paths = sorted(set(_extract_backtick_paths(readme)))
    for claimed_path in claimed_paths:
        if claimed_path.startswith(("http://", "https://", "npm ", "git ")):
            continue
        if any(char in claimed_path for char in ["*", "{", "}", "$", "<", ">"]):
            continue
        if claimed_path.endswith(("/", ".ts", ".tsx", ".py", ".json", ".md", ".js", ".jsx")):
            candidate = (repo_path / claimed_path.strip("/ ")).resolve()
            if candidate.is_relative_to(repo_path) and not candidate.exists():
                anomalies.append(
                    RepoAnomaly(
                        severity="warning",
                        code="readme_path_missing",
                        message=f"README references `{claimed_path}` but it does not exist.",
                        evidence=claimed_path,
                    )
                )


def _check_script_claims(package_json: dict[str, object] | None, readme: str, anomalies: list[RepoAnomaly]) -> None:
    if package_json is None:
        return
    scripts = package_json.get("scripts")
    if not isinstance(scripts, dict):
        scripts = {}
    for script_name in ["dev", "build", "start", "lint", "type-check", "test", "format"]:
        if f"npm run {script_name}" in readme and script_name not in scripts:
            anomalies.append(
                RepoAnomaly(
                    severity="error",
                    code="readme_script_missing",
                    message=f"README documents `npm run {script_name}` but package.json has no `{script_name}` script.",
                )
            )


def _check_nextjs_claims(repo_path: Path, lower_readme: str, anomalies: list[RepoAnomaly]) -> None:
    if "next.js" not in lower_readme and "nextjs" not in lower_readme:
        return
    if not (repo_path / "src" / "app" / "layout.tsx").exists():
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="next_layout_missing",
                message="README claims a Next.js app but src/app/layout.tsx is missing.",
            )
        )
    if not (repo_path / "src" / "app" / "page.tsx").exists():
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="next_page_missing",
                message="README claims a Next.js app but src/app/page.tsx is missing.",
            )
        )


def _check_platform_architecture_claims(repo_path: Path, lower_readme: str, anomalies: list[RepoAnomaly]) -> None:
    if "sdk agnostic" in lower_readme and not _any_exists(
        repo_path,
        ["src/types/platformConfig.ts", "src/config/sdkCatalog.ts", "src/stores/platformConfigStore.ts"],
    ):
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="sdk_agnostic_claim_unimplemented",
                message="README claims SDK-agnostic Platform behavior, but no PlatformConfig/sdkCatalog/platformConfigStore implementation was found.",
            )
        )

    if "model gateway" in lower_readme and not _any_exists(
        repo_path,
        ["src/config/modelProviderCatalog.ts", "src/components/config/ModelGatewaySelector.tsx"],
    ):
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="model_gateway_claim_unimplemented",
                message="README claims model gateway behavior, but no model provider catalog or selector was found.",
            )
        )

    if "runner" in lower_readme and not _any_exists(
        repo_path,
        ["src/lib/api/runnerClient.ts", "src/app/api/runner/health/route.ts"],
    ):
        anomalies.append(
            RepoAnomaly(
                severity="info",
                code="runner_integration_not_found",
                message="README references Runner integration, but no runner client/API route was found.",
            )
        )

    if "kernel" in lower_readme and not _any_exists(
        repo_path,
        ["src/lib/api/kernelClient.ts", "src/app/api/kernel/status/route.ts"],
    ):
        anomalies.append(
            RepoAnomaly(
                severity="info",
                code="kernel_integration_not_found",
                message="README references Kernel integration, but no kernel client/API route was found.",
            )
        )


def _check_old_branding(repo_path: Path, readme: str, anomalies: list[RepoAnomaly]) -> None:
    if "Autonomyx" in readme or "openautonomyx" in readme.lower():
        anomalies.append(
            RepoAnomaly(
                severity="warning",
                code="old_branding_in_readme",
                message="README still contains old Autonomyx branding.",
            )
        )

    for path in repo_path.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".md", ".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".yaml", ".yml", ".env"}:
            continue
        text = _read_text(path)
        if text and ("Autonomyx" in text or "openautonomyx" in text.lower()):
            anomalies.append(
                RepoAnomaly(
                    severity="info",
                    code="old_branding_in_repo",
                    message="Repository contains old Autonomyx branding outside README.",
                    evidence=str(path.relative_to(repo_path)),
                )
            )
            return


def _extract_backtick_paths(text: str) -> list[str]:
    parts = text.split("`")
    return [parts[index].strip() for index in range(1, len(parts), 2)]


def _any_exists(repo_path: Path, paths: list[str]) -> bool:
    return any((repo_path / path).exists() for path in paths)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


# Secret detection patterns for security gate
_SECRET_PATTERNS = [
    # AWS
    (r"(?i)(aws_access_key|aws_secret_key|aws_secret_access_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{20,40}['\"]?", "aws_credentials"),
    # GitHub token
    (r"(?i)(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9]{36,}", "github_token"),
    # OpenAI key
    (r"sk-[A-Za-z0-9]{20,}", "openai_key"),
    # Anthropic key
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "anthropic_key"),
    # Generic API key
    (r"(?i)(api_key|apikey|secret|token)\s*[=:]\s*['\"]?[A-Za-z0-9_-]{16,}['\"]?", "api_credentials"),
    # Private key
    (r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "private_key"),
]


def _check_secrets(repo_path: Path, anomalies: list[RepoAnomaly]) -> None:
    """Check for exposed secrets in the repository."""
    import re
    for path in repo_path.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".yaml", ".yml", ".env", ".env.local", ".env.production"}:
            continue
        # Skip node_modules and common Generated paths
        if "node_modules" in path.parts or "dist" in path.parts or "build" in path.parts:
            continue
        text = _read_text(path)
        if not text:
            continue
        for pattern, secret_type in _SECRET_PATTERNS:
            if re.search(pattern, text):
                anomalies.append(
                    RepoAnomaly(
                        severity="error",
                        code="secret_detected",
                        message=f"Potential {secret_type} detected in {path.name}.",
                        evidence=str(path.relative_to(repo_path)),
                    )
                )
                return
