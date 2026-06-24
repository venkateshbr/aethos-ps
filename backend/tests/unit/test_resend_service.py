from __future__ import annotations

from typing import NoReturn

from app.core.config import settings
from app.services.resend_service import ResendService


def test_resend_skips_non_deliverable_recipient_domains(monkeypatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "configured-key")

    def fail_post(*_args, **_kwargs) -> NoReturn:
        raise AssertionError("non-deliverable recipients should not call Resend")

    monkeypatch.setattr("app.services.resend_service.httpx.post", fail_post)

    for recipient in (
        "Finance <collections@example.com>",
        "collections@aethos-qa.dev",
    ):
        result = ResendService().send_email(
            recipient,
            "Payment overdue",
            "<p>Please pay</p>",
        )

        assert result == {
            "status": "skipped",
            "reason": "non_deliverable_recipient_domain",
        }
