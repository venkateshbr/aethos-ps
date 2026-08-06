"""Contract for the governed production billing-override workflow (#481)."""

from pathlib import Path


def test_billing_override_workflow_is_manual_audited_and_production_gated() -> None:
    workflow = (
        Path(__file__).resolve().parents[3]
        / ".github"
        / "workflows"
        / "billing-access-override.yml"
    ).read_text()

    assert "workflow_dispatch:" in workflow
    assert "environment: production" in workflow
    assert "secrets.AETHOS_PRODUCTION_ENV" in workflow
    assert "github.actor" in workflow
    assert "grant_billing_access_override" in workflow
    assert "revoke_billing_access_override" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
