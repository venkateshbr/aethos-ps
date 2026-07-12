"""Contracts for the optional Vercel preview workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "preview-deploy.yml"


def test_preview_job_uses_a_job_compatible_opt_in_gate() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "if: ${{ vars.VERCEL_PREVIEW_ENABLED == 'true' }}" in workflow
    assert "if: ${{ env.VERCEL_TOKEN" not in workflow
    assert "VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}" in workflow
