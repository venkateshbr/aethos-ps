# E2E scenario: linked Telegram ERP pilot (#595)

## Repeatable local checks

- `cd backend && uv run --locked pytest tests/unit/test_telegram_api_contract.py tests/unit/test_copilot_hitl_policy.py tests/unit/test_atlas_tools_api_contract.py tests/unit/test_authz_mutation_coverage.py`
- From the repo root, `bash backend/scripts/test_telegram_synthetic.sh`. Requires local `postgres:17-alpine` and `postgrest/postgrest:v14.8` images. Starts disposable containers on their own network; PostgREST binds only to a random loopback port. Uses local synthetic JWTs, the actual migration and PostgREST, genuine Atlas AR broker queries, and authenticated API requests via ASGI. The synthetic write dispatch is stubbed; policy behavior is covered separately. It never contacts Telegram, Hermes, or a configured Supabase project.

## Staging acceptance before any enablement beyond the sandbox

1. From two synthetic ERP accounts in distinct workspaces with distinguishable AR totals, obtain challenges and link their own dedicated DM identities. Verify no ERP signup/JWT/token is sent to Telegram, wrong-sender/expired/replayed challenges fail, and neither account can revoke the other link.
2. Verify a group, channel, forwarded DM, invalid webhook secret, and disabled feature cannot run a command or produce ERP data. Use only an isolated synthetic staging bot for checks delivered by Telegram.
3. Each linked `/ar` reports its own total and creates an owned, tenant-scoped Nous chat record. Disable one account's tenant membership and verify the next operation is refused.
4. Preview a draft for a seeded synthetic engagement. Verify no Inbox work exists before explicit confirmation. Try a wrong sender and an expired code, then confirm a fresh proposal. Duplicate both delivery and confirmation (different update IDs); expect exactly one Inbox item, no posted invoice, and tenant/user/action audit records. Repeat with a user lacking `invoices.draft` or a billing write lock; expect refusal. Review in the ERP, not Telegram. Never use real ERP records.
5. Unlink from ERP, then test stale confirmation and a new read; both must be denied. Recheck disabled behavior and remove the staging webhook when done. Record redacted evidence on #595; no raw token, code, or identity values.
