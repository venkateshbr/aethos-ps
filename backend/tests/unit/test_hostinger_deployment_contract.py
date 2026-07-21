"""Static contracts for the Hostinger production Compose topology."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOSTINGER_COMPOSE = _REPO_ROOT / "docker-compose.hostinger.yml"
_PRODUCTION_COMPOSE = _REPO_ROOT / "infra" / "docker-compose.prod.yml"
_BACKEND_DOCKERFILE = _REPO_ROOT / "backend" / "Dockerfile"
_HOSTINGER_DEPLOY_SCRIPT = _REPO_ROOT / "scripts" / "deploy" / "hostinger-deploy.sh"
_HOSTINGER_DEPLOY_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "deploy-hostinger.yml"


def _temporary_deploy_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    script = repo / "scripts" / "deploy" / "hostinger-deploy.sh"
    script.parent.mkdir(parents=True)
    script.write_text(_HOSTINGER_DEPLOY_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    for directory in ("backend", "frontend", "integrations"):
        (repo / directory).mkdir()
    (repo / "backend" / "app.txt").write_text("reviewed\n", encoding="utf-8")
    (repo / "frontend" / "app.txt").write_text("reviewed\n", encoding="utf-8")
    (repo / "integrations" / "app.txt").write_text("reviewed\n", encoding="utf-8")
    (repo / "docker-compose.hostinger.yml").write_text("services: {}\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".env\n*.ignored\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.email", "deploy@example.com"], check=True)
    subprocess.run(["git", "-C", repo, "config", "user.name", "Deploy Contract"], check=True)
    subprocess.run(["git", "-C", repo, "add", "."], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "reviewed source"], check=True)
    return repo


def _run_local_deploy(
    repo: Path,
    deploy_sha: str,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ.get("HOME", ""),
        "HOSTINGER_DEPLOY_SOURCE": "local",
        "HOSTINGER_DEPLOY_SHA": deploy_sha,
        "AETHOS_IMAGE_TAG": deploy_sha,
        "HOSTINGER_SSH_HOST": "example.invalid",
    }
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", repo / "scripts" / "deploy" / "hostinger-deploy.sh"],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _hostinger_services() -> dict:
    compose = yaml.safe_load(_HOSTINGER_COMPOSE.read_text(encoding="utf-8"))
    return compose["services"]


def _production_services() -> dict:
    compose = yaml.safe_load(_PRODUCTION_COMPOSE.read_text(encoding="utf-8"))
    return compose["services"]


def _environment_default_int(value: str) -> int:
    match = re.fullmatch(r"\$\{[A-Z0-9_]+:-(\d+)}", value)
    assert match is not None
    return int(match.group(1))


def test_hostinger_services_have_separate_bounded_queue_pool_budgets() -> None:
    services = _hostinger_services()

    api_environment = services["api"]["environment"]
    worker_environment = services["worker"]["environment"]

    assert api_environment["QUEUE_DB_POOL_MIN_SIZE"] == "${QUEUE_API_DB_POOL_MIN_SIZE:-1}"
    assert api_environment["QUEUE_DB_POOL_MAX_SIZE"] == "${QUEUE_API_DB_POOL_MAX_SIZE:-1}"
    assert api_environment["QUEUE_DB_APPLICATION_NAME"] == (
        "${QUEUE_API_DB_APPLICATION_NAME:-aethos-ps-api}"
    )
    assert worker_environment["QUEUE_DB_POOL_MIN_SIZE"] == (
        "${QUEUE_WORKER_DB_POOL_MIN_SIZE:-1}"
    )
    assert worker_environment["QUEUE_DB_POOL_MAX_SIZE"] == (
        "${QUEUE_WORKER_DB_POOL_MAX_SIZE:-2}"
    )
    assert worker_environment["QUEUE_DB_APPLICATION_NAME"] == (
        "${QUEUE_WORKER_DB_APPLICATION_NAME:-aethos-ps-worker}"
    )


def test_hostinger_default_session_budget_preserves_deploy_headroom() -> None:
    services = _hostinger_services()
    api_environment = services["api"]["environment"]
    worker_environment = services["worker"]["environment"]
    dockerfile = _BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    api_worker_match = re.search(r"--workers\s+(\d+)", dockerfile)

    assert api_worker_match is not None
    api_workers = int(api_worker_match.group(1))
    api_pool_max = _environment_default_int(api_environment["QUEUE_DB_POOL_MAX_SIZE"])
    worker_pool_max = _environment_default_int(worker_environment["QUEUE_DB_POOL_MAX_SIZE"])

    # Procrastinate's LISTEN/NOTIFY connection is outside its worker pool.
    steady_sessions = (api_workers * api_pool_max) + worker_pool_max + 1

    assert steady_sessions == 5
    assert (steady_sessions * 2) + 3 <= 15


def test_hostinger_worker_consumes_every_production_queue() -> None:
    worker_command = _hostinger_services()["worker"]["command"]
    queue_argument = re.search(r"--queues=([^\s]+)", worker_command)

    assert queue_argument is not None
    assert set(queue_argument.group(1).split(",")) == {
        "default",
        "extraction",
        "cron",
        "billing",
        "fx",
    }


def test_secondary_production_worker_uses_the_same_queue_contract() -> None:
    worker_command = _production_services()["worker"]["command"]
    queue_argument = re.search(r"--queues=([^\s]+)", worker_command)

    assert queue_argument is not None
    assert set(queue_argument.group(1).split(",")) == {
        "default",
        "extraction",
        "cron",
        "billing",
        "fx",
    }


def test_hostinger_api_requires_the_queue_for_readiness() -> None:
    api_environment = _hostinger_services()["api"]["environment"]

    assert api_environment["QUEUE_REQUIRED"] == "true"


def test_hostinger_api_exposes_the_exact_image_tag_as_build_sha() -> None:
    api_environment = _hostinger_services()["api"]["environment"]

    assert api_environment["BUILD_SHA"] == "${AETHOS_IMAGE_TAG:-unknown}"


def test_hostinger_deploy_defaults_to_the_full_git_sha() -> None:
    script = _HOSTINGER_DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'LOCAL_HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"' in script
    assert 'DEPLOY_SHA="$(env_or_file HOSTINGER_DEPLOY_SHA "$LOCAL_HEAD_SHA")"' in script
    assert 'AETHOS_IMAGE_TAG="$(env_or_file AETHOS_IMAGE_TAG "$DEPLOY_SHA")"' in script
    assert 'if [ "$AETHOS_IMAGE_TAG" != "$DEPLOY_SHA" ]' in script
    assert "rev-parse --short HEAD" not in script


def test_local_deploy_rejects_a_dirty_source_tree(tmp_path: Path) -> None:
    repo = _temporary_deploy_repo(tmp_path)
    deploy_sha = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "backend" / "app.txt").write_text("unreviewed\n", encoding="utf-8")

    result = _run_local_deploy(repo, deploy_sha)

    assert result.returncode != 0
    assert "local deploy source is dirty" in result.stderr.lower()


def test_local_deploy_rejects_a_sha_different_from_head(tmp_path: Path) -> None:
    repo = _temporary_deploy_repo(tmp_path)
    reviewed_sha = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "backend" / "app.txt").write_text("next reviewed version\n", encoding="utf-8")
    subprocess.run(["git", "-C", repo, "add", "."], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "next reviewed source"], check=True)

    result = _run_local_deploy(repo, reviewed_sha)

    assert result.returncode != 0
    assert "local deploy sha must equal the clean local head" in result.stderr.lower()


def test_local_deploy_rejects_an_image_tag_different_from_source_sha(
    tmp_path: Path,
) -> None:
    repo = _temporary_deploy_repo(tmp_path)
    deploy_sha = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    result = _run_local_deploy(
        repo,
        deploy_sha,
        extra_env={"AETHOS_IMAGE_TAG": "0" * 40},
    )

    assert result.returncode != 0
    assert "aethos_image_tag must exactly match" in result.stderr.lower()


def test_local_deploy_syncs_only_the_reviewed_commit_archive(tmp_path: Path) -> None:
    repo = _temporary_deploy_repo(tmp_path)
    deploy_sha = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    runtime_env = repo / ".env"
    runtime_env.write_text(
        "\n".join(
            (
                "SUPABASE_URL=https://example.invalid",
                "SUPABASE_ANON_KEY=test-anon",
                "SUPABASE_SERVICE_ROLE_KEY=test-service",
                "SUPABASE_JWT_SECRET=test-jwt",
                "OPENROUTER_API_KEY=test-openrouter",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "backend" / "unreviewed.ignored").write_text(
        "must not deploy\n",
        encoding="utf-8",
    )
    boundary_bin = tmp_path / "bin"
    boundary_bin.mkdir()
    rsync_log = tmp_path / "rsync.log"
    (boundary_bin / "ssh").write_text(
        "#!/usr/bin/env bash\ncat >/dev/null || true\n",
        encoding="utf-8",
    )
    (boundary_bin / "scp").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (boundary_bin / "curl").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (boundary_bin / "rsync").write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$RSYNC_LOG\"\n"
        "for arg in \"$@\"; do\n"
        "  if [[ \"$arg\" == */backend/ ]] && [ -e \"${arg}unreviewed.ignored\" ]; then\n"
        "    echo UNREVIEWED_SOURCE_PRESENT >> \"$RSYNC_LOG\"\n"
        "  fi\n"
        "done\n",
        encoding="utf-8",
    )
    for command in boundary_bin.iterdir():
        command.chmod(0o755)

    result = _run_local_deploy(
        repo,
        deploy_sha,
        extra_env={
            "PATH": f"{boundary_bin}:{os.environ['PATH']}",
            "AETHOS_LOCAL_ENV_FILE": str(runtime_env),
            "RSYNC_LOG": str(rsync_log),
        },
    )

    assert result.returncode == 0, result.stderr
    synced_sources = rsync_log.read_text(encoding="utf-8")
    assert str(repo) not in synced_sources
    assert "UNREVIEWED_SOURCE_PRESENT" not in synced_sources


def test_git_deploy_checks_out_the_requested_exact_commit() -> None:
    script = _HOSTINGER_DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert '"$APP_DIR" "$REPO_URL" "$BRANCH" "$DEPLOY_SHA"' in script
    assert 'DEPLOY_SHA="$4"' in script
    assert 'git checkout --detach "$DEPLOY_SHA"' in script
    assert 'git rev-parse HEAD' in script
    assert "git pull" not in script


def test_git_deploy_rejects_remote_untracked_source_files() -> None:
    script = _HOSTINGER_DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert (
        'REMOTE_SOURCE_STATUS="$(git status --porcelain --untracked-files=all)"'
        in script
    )
    assert 'if [ -n "$REMOTE_SOURCE_STATUS" ]' in script
    assert "remote deployment checkout is dirty" in script


def test_github_deploy_verifies_clean_exact_workflow_sha() -> None:
    workflow = _HOSTINGER_DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    # The deploy pins to the exact commit SHA end-to-end: it checks out that SHA,
    # tags the images with it, deploys the compose blob at that SHA, and only
    # passes once the live /health/ready build_sha matches the deployed tag.
    assert "TAG: ${{ github.sha }}" in workflow
    assert "ref: ${{ github.sha }}" in workflow
    assert "/blob/$TAG/docker-compose.hostinger.registry.yml" in workflow
    assert '"$SHA" = "$TAG"' in workflow


def test_github_deploy_requires_the_confirmed_hostinger_project_name() -> None:
    workflow = _HOSTINGER_DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    # Project name comes from the repo variable and is verified present before any
    # deploy call; it is never hardcoded to a specific project.
    assert "${{ vars.HOSTINGER_PROJECT_NAME }}" in workflow
    assert '[ -n "${{ vars.HOSTINGER_PROJECT_NAME }}" ]' in workflow
    assert "project-name: aethos-ps-production" not in workflow


def test_hostinger_api_healthcheck_requires_ready_json_status() -> None:
    healthcheck_command = _hostinger_services()["api"]["healthcheck"]["test"][-1]

    assert "/health/ready" in healthcheck_command
    assert "json.load" in healthcheck_command
    assert "data.get('status') == 'ready'" in healthcheck_command
