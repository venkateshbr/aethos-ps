"""ResendService — sends transactional email via Resend API.

Graceful degradation: when ``resend_api_key`` is not configured or the recipient
belongs to a non-deliverable test/demo domain, the service logs a warning and
returns ``{"status": "skipped"}`` so callers never have to branch on send
availability.
"""

from __future__ import annotations

import logging
from email.utils import parseaddr

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

NON_DELIVERABLE_RECIPIENT_DOMAINS = {
    "aethos-qa.dev",
    "example.com",
    "example.net",
    "example.org",
}


class ResendService:
    """Thin wrapper around the Resend transactional email API."""

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        from_name: str = "Aethos",
    ) -> dict:
        """Send a single transactional email.

        Parameters
        ----------
        to:        Recipient email address.
        subject:   Email subject line.
        body_html: HTML body content.
        from_name: Display name for the sender (default "Aethos").

        Returns
        -------
        Resend API response dict, or ``{"status": "skipped"}`` / ``{"status":
        "error", "error": ...}`` on non-fatal failure.
        """
        if _is_non_deliverable_recipient(to):
            logger.warning(
                "non-deliverable recipient domain — email skipped",
                extra={"to": to},
            )
            return {"status": "skipped", "reason": "non_deliverable_recipient_domain"}

        if not settings.resend_api_key:
            logger.warning(
                "resend_api_key not set — email skipped",
                extra={"to": to},
            )
            return {"status": "skipped"}

        try:
            resp = httpx.post(
                "https://api.resend.com/emails",
                json={
                    "from": f"{from_name} <noreply@aethos.app>",
                    "to": [to],
                    "subject": subject,
                    "html": body_html,
                },
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info("email_sent", extra={"to": to})
            return resp.json()
        except Exception as e:
            logger.error("email_failed", extra={"to": to, "error": str(e)})
            return {"status": "error", "error": str(e)}


def _is_non_deliverable_recipient(to: str) -> bool:
    """Skip reserved/demo domains used by tests and local QA flows."""
    _, addr = parseaddr(to)
    if "@" not in addr:
        return False
    domain = addr.rsplit("@", 1)[1].lower().rstrip(".")
    return domain in NON_DELIVERABLE_RECIPIENT_DOMAINS
