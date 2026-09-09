"""Static contracts for ECC release and repository security controls."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _workflow(name: str) -> tuple[str, dict]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_release_reuses_the_hostinger_deploy_and_validates_aethos_version() -> None:
    text, workflow = _workflow("release.yml")

    assert "./.github/workflows/deploy-hostinger.yml" in text
    assert "backend/pyproject.toml" in text
    assert "frontend/package.json" not in text
    assert "/docker/aethos-ps" not in text
    assert "HOSTINGER_SSH_KEY" not in text
    assert "dry_run" in workflow[True]["workflow_dispatch"]["inputs"]


def test_hostinger_deploy_is_reusable_and_has_ghcr_write_permission() -> None:
    text, workflow = _workflow("deploy-hostinger.yml")

    assert "workflow_call" in workflow[True]
    assert workflow["permissions"]["packages"] == "write"
    for dockerfile in (
        "backend             Dockerfile",
        "frontend            Dockerfile.prod",
        "integrations/hermes Dockerfile",
        "frontend            Dockerfile.timesheet.prod",
    ):
        assert dockerfile in text


def test_supply_chain_gates_real_backend_and_frontend_lockfiles() -> None:
    text, _ = _workflow("supply-chain-watch.yml")

    assert "frontend/package-lock.json" in text
    assert "backend/uv.lock" in text
    assert "npm audit --audit-level=high" in text
    assert "pip-audit --strict" in text
    assert "|| true" not in text


def test_locked_dependencies_currently_pass_high_severity_audits() -> None:
    """The enforced audit jobs must not be introduced already failing."""

    backend = (REPO_ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8")
    frontend = (REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")

    assert '"cryptography>=50.0.0"' in backend
    assert '"@angular/core": "^20.3.30"' in frontend
    assert '"ws": "8.21.3"' in frontend


def test_ci_runs_commitlint_and_pinned_agentshield() -> None:
    text, _ = _workflow("ci.yml")

    assert "@commitlint/cli" in text
    assert "commitlint.config.js" in text
    assert "git cat-file -e" in text
    assert "ecc-agentshield@1.4.0 scan" in text
    assert "dist.integrity" in text
    assert "--min-severity high --format json" in text
    assert 'in {"critical", "high"}' in text
    assert "known_false_positive" in text
    assert "accepted_role_risks" in text


def test_codeowners_only_references_enforceable_maintainer() -> None:
    codeowners = (REPO_ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")

    owners = {
        token
        for line in codeowners.splitlines()
        if not line.lstrip().startswith("#")
        for token in line.split()
        if token.startswith("@")
    }
    assert owners == {"@venkateshbr"}


def test_dependabot_pins_angular_to_supported_major_and_limits_noise() -> None:
    text = (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")

    assert 'dependency-name: "@angular/*"' in text
    assert 'versions: [">=21"]' in text
    assert text.count("open-pull-requests-limit: 5") >= 2
