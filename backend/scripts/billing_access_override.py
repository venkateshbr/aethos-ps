"""Grant or revoke an audited, time-bounded billing-access override.

This operator-only command calls service-role-only database functions. It
requires an exact tenant id/name pair and is a dry run unless ``--execute`` is
present.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from app.core.config import settings
from supabase import create_client


def _parse_until(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--until must include a timezone")
    return parsed.astimezone(UTC).isoformat()


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("grant", "revoke"))
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--until", type=_parse_until)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.action == "grant" and not args.until:
        parser.error("grant requires --until")
    if args.action == "revoke" and args.until:
        parser.error("revoke does not accept --until")
    return args


def main() -> None:
    args = _args()
    if not args.execute:
        print(
            f"DRY RUN: {args.action} billing override for "
            f"{args.tenant_name} ({args.tenant_id}); add --execute to apply"
        )
        return

    db = create_client(settings.supabase_url, settings.supabase_service_role_key)
    function = (
        "grant_billing_access_override"
        if args.action == "grant"
        else "revoke_billing_access_override"
    )
    payload = {
        "p_tenant_id": args.tenant_id,
        "p_tenant_name": args.tenant_name,
        "p_reason": args.reason,
        "p_actor": args.actor,
    }
    if args.action == "grant":
        payload["p_until"] = args.until
    result = db.rpc(function, payload).execute()
    event_id = result.data
    print(
        f"Applied {args.action} for {args.tenant_name} ({args.tenant_id}); audit event {event_id}"
    )


if __name__ == "__main__":
    main()
