"""Contracts preventing false-green GitHub CI runs."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_frontend_release_jobs_are_not_skipped_by_push_payload_path_heuristics() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "frontend-check:" in workflow
    assert "frontend-build:" in workflow
    assert "github.event.commits[*]" not in workflow
    assert "npm run typecheck" in workflow
    assert "npm run test:ci" in workflow
    assert "npm run build:all" in workflow
