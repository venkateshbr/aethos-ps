"""ResendService — sends transactional email via Resend API.

Graceful degradation: when ``resend_api_key`` is not configured the service
logs a warning and returns ``{"status": "skipped"}`` so callers never have to
branch on the key being present.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


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
