# Production Data Reset

Use this runbook when production needs to be returned to a clean platform state
without dropping the Supabase project or platform reference data.

## What Gets Deleted

`backend/scripts/reset_operational_data.py` deletes:

- all rows in `public.tenants`;
- all tenant-scoped public tables where `tenant_id` matches a deleted tenant;
- dependent public tables discovered through foreign keys;
- all objects from the private Supabase Storage `documents` bucket through the
  supported Storage API;
- Supabase Auth users through the supported Admin API, unless
  `--no-include-auth-users` is passed;
- tenant-specific rows in mixed tables such as `tax_rates`.
- global operational rows that are not platform master data, including
  webhook idempotency logs, rate-limit events when present, and Procrastinate
  queued job/event rows.

The script is schema-driven and dry-runs by default.

Supabase Auth users are a separate control-plane surface. The reset script now
deletes them through the Supabase Admin API by default after the database reset
transaction commits. Use `--no-include-auth-users` only when you intentionally
want to preserve login identities.

## Required Master Data

These records must remain for the platform to function after all tenants are
deleted:

- `public.fx_rates`: global currency rates used by O2C, P2P, and R2R
  base-currency calculations.
- `public.tax_rates` rows where `tenant_id IS NULL`: system tax catalog
  visible to all tenants at setup time.
- **System RBAC catalogue** (seeded by migration `0096`): `security_privileges`,
  `security_duties`, `security_duty_privileges`, and **`security_role_duties`**.
  These are now explicitly protected. `security_role_duties` in particular has no
  `tenant_id` but is an FK-child of `security_roles` (which does), so before the
  2026-07-20 fix the FK-closure silently deleted all 94 role→duty mappings —
  leaving every new tenant's users (incl. the owner) with **zero effective
  privileges** and every permission-gated UI action (e.g. Draft Invoice)
  disabled. If this ever recurs, repair by re-applying migration `0096` (it is
  idempotent: `ON CONFLICT DO NOTHING`).
- `storage.buckets` row with `id = 'documents'`: private document-upload
  bucket used by invoice, expense, and engagement-letter intake.
- Database extensions, enum types, functions, triggers, RLS policies, and
  Procrastinate tables created by migrations. The reset can clear queue rows,
  but it must not drop the queue tables.
- Supabase Auth configuration and application environment variables.
- The Supabase Auth service configuration itself. Individual `auth.users`
  records are not required master data; after a full tenant reset, users with
  no active `tenant_users` membership can be deleted.

Tenant-scoped master data such as chart of accounts, approval policies,
service catalogue choices, employees, clients/vendors, and number sequences is
deleted because it belongs to a tenant. New tenants recreate the required
tenant baseline through the signup/provisioning path.

## Dry Run

From a shell with `DATABASE_URL` exported:

```bash
cd backend
uv run python -m scripts.reset_operational_data
```

The dry run prints tenant count, storage object count, per-table row counts,
and preserved master-data counts.

## Execute

```bash
cd backend
uv run python -m scripts.reset_operational_data \
  --execute \
  --confirm DELETE_ALL_TENANTS
```

Use the Supabase session pooler URL on port `5432`. The direct Supabase DB host
can be IPv6-only and is not reliable from Docker bridge networks.

Storage cleanup also requires `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY`. Supabase intentionally blocks direct deletes from
`storage.objects`, so the reset script removes document objects through the
Storage API before deleting tenant rows.

During `--execute`, the script sets `session_replication_role = replica` for
the reset transaction only. This bypasses immutable audit triggers such as
`financial_events` while the operator is intentionally deleting all tenant
history; normal application writes remain protected.

## Repair Master/Config Data

If master/config data is accidentally removed, repair it with:

```bash
cd backend
uv run python -m scripts.seed_master_config --execute
```

The repair script is dry-run by default and only restores:

- the private `documents` Storage bucket and its RLS policies;
- the 20 global FX seed rows;
- the 13 system tax-rate rows where `tenant_id IS NULL`.

It does not create tenants, users, employees, clients, chart of accounts, demo
records, or transaction data.

## Post-Reset Checks

Run these SQL checks through the same connection:

```sql
select count(*) from public.tenants;
select count(*) from public.tenant_users;
select count(*) from auth.users;
select count(*)
from auth.users au
where not exists (
  select 1
  from public.tenant_users tu
  where tu.user_id = au.id
    and tu.deleted_at is null
);
select count(*) from public.fx_rates;
select count(*) from public.tax_rates where tenant_id is null;
select count(*) from public.security_role_duties;
select count(*) from public.security_duty_privileges;
select count(*) from storage.buckets where id = 'documents';
select count(*) from storage.objects where bucket_id = 'documents';
```

Expected result:

- `tenants = 0`
- `tenant_users = 0`
- `auth.users = 0` when orphan Auth cleanup is part of the reset
- orphan `auth.users = 0`
- `fx_rates > 0`
- system `tax_rates > 0`
- `security_role_duties > 0` (94 as of migration 0096) — **RBAC intact**
- `security_duty_privileges > 0`
- `documents` bucket row exists
- `documents` bucket objects = 0
