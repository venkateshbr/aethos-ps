# Supabase Storage Buckets — Operator Runbook

> **Owner**: Sthira (SRE)
> **Source of truth migration**: [`backend/supabase/migrations/0016_storage_documents_bucket.sql`](../../backend/supabase/migrations/0016_storage_documents_bucket.sql)
> **Filed against issue**: [#100](https://github.com/venkateshbr/aethos-ps/issues/100)

---

## Why this exists

Buckets in Supabase Storage are *not* visible to ORM migrations by default — they live in the `storage.buckets` table inside the managed `storage` schema. If we provision a bucket through the dashboard or via the Storage REST API and never codify it, a fresh project (staging clone, disaster-recovery rebuild, second region) starts with **zero buckets** and every upload returns `404 Bucket not found`. That is exactly what happened in issue #100: `POST /api/v1/documents/upload` was 500'ing for every tenant because the `documents` bucket had never been created on project `glcljucaayeesvrsjths`.

This document is the operator inventory and the bootstrap procedure. Every Storage bucket the product uses **must** be listed here and **must** have a corresponding migration. If you add a new bucket, update both.

---

## Bucket inventory

### `documents` — primary

| Property | Value |
| --- | --- |
| Purpose | Uploaded source files for AI extraction: engagement letters, vendor invoices, receipts, contracts. The entry point for the C10/C11/C12/C13 agent pipeline. |
| Public | **No** (private) |
| File size limit | 20 MiB (`20 * 1024 * 1024` = `20,971,520` bytes) |
| Allowed MIME types | `application/pdf`, `image/jpeg`, `image/png`, `image/webp`, `text/plain` |
| Path convention | `{tenant_id}/{year}/{month:02d}/{document_id}.{ext}` |
| Path constructed by | [`backend/app/api/v1/endpoints/documents.py`](../../backend/app/api/v1/endpoints/documents.py) (lines around `storage_path = ...`) |
| Written via | Service-role Supabase client (`get_service_role_client`) — bypasses RLS |
| Tenant scoping (writes) | Enforced at API layer by `get_tenant_id` membership check (issue #90) — the verified `tenant_id` is the first path segment |
| Tenant scoping (RLS, defense in depth) | First path segment must match an active row in `public.tenant_users` for `auth.uid()`. See policies `documents_tenant_{select,insert,update,delete}` on `storage.objects`. |
| Migration | [`backend/supabase/migrations/0016_storage_documents_bucket.sql`](../../backend/supabase/migrations/0016_storage_documents_bucket.sql) |

### Future buckets (planned, not yet provisioned)

These are referenced in PLAN.md but not built. **Each one needs its own migration** following the pattern in `0016_*`:

| Name | Planned purpose | Public? | Size cap (working assumption) |
| --- | --- | --- | --- |
| `invoice-pdfs` | Generated/sent invoice PDFs for AR | Private | 10 MiB |
| `brand-assets` | Tenant logos, letterhead, email signatures | Private (signed URLs to clients) | 5 MiB |
| `report-exports` | One-shot report exports (CSV/XLSX/PDF) — TTL'd | Private | 50 MiB |

When you build one of these, replicate `0016_*` with the bucket's name, size cap, MIME allow-list, and (if path convention differs) the appropriate `storage.foldername(name)[N]` index in the RLS policies.

---

## Provisioning a bucket in a new Supabase project

The migration is the source of truth. There are two scenarios.

### Scenario A — Fresh project bootstrap (recommended)

Run all migrations in order. The Supabase CLI handles this for both local and remote:

```bash
cd backend

# Local (Postgres-only dev DB):
supabase db reset                  # applies every migration in order

# Remote (live project):
supabase link --project-ref <PROJECT_REF>   # one-time
supabase db push                            # applies any un-applied migrations
```

After `supabase db push`, the bucket and its RLS policies are in place.

### Scenario B — Existing project missing one specific bucket

If the project already has most migrations and you just need to (re-)provision the bucket, run the migration explicitly. The migration is **idempotent** (`INSERT ... ON CONFLICT DO UPDATE` for the bucket row, `DROP POLICY IF EXISTS` + `CREATE POLICY` for each policy), so re-running it is safe even if some pieces already exist.

```bash
cd backend
supabase db push                  # if 0016 hasn't been applied to remote yet
# OR
psql "$DATABASE_URL" -f backend/supabase/migrations/0016_storage_documents_bucket.sql
```

### Scenario C — Out-of-band hotfix (no CLI, no psql)

If the CLI is broken or you only have the service-role key, the Storage admin REST API can create the bucket. **This will NOT install the RLS policies — run the migration as soon as possible after.**

```bash
set -a && source backend/.env && set +a   # load SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY

curl -s -X POST "${SUPABASE_URL}/storage/v1/bucket" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "documents",
    "name": "documents",
    "public": false,
    "file_size_limit": 20971520,
    "allowed_mime_types": [
      "application/pdf",
      "image/jpeg",
      "image/png",
      "image/webp",
      "text/plain"
    ]
  }'
```

---

## Verification after deploy

### 1. Bucket exists and config matches expectation

```bash
set -a && source backend/.env && set +a

curl -s -X GET "${SUPABASE_URL}/storage/v1/bucket/documents" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" | python3 -m json.tool
```

Expected (key fields):
```json
{
  "id": "documents",
  "name": "documents",
  "public": false,
  "file_size_limit": 20971520,
  "allowed_mime_types": [
    "application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"
  ]
}
```

### 2. RLS policies exist

Query via psql / Supabase SQL editor:
```sql
SELECT polname, cmd::text
  FROM pg_policy
  JOIN pg_class ON pg_class.oid = pg_policy.polrelid
 WHERE pg_class.relname  = 'objects'
   AND pg_class.relnamespace = 'storage'::regnamespace
   AND polname LIKE 'documents_tenant_%';
```

Expected: four rows — `documents_tenant_select`, `documents_tenant_insert`, `documents_tenant_update`, `documents_tenant_delete`.

### 3. End-to-end upload via the API

The full happy-path regression lives in [`backend/tests/api/test_documents.py`](../../backend/tests/api/test_documents.py):

```bash
cd backend
set -a && source .env && set +a
uv run pytest tests/api/test_documents.py -v
```

`test_upload_pdf_document_happy_path` is currently `xfail`-marked referencing #100; once the bucket exists, it will `xpass` (and the SDET will un-xfail in the next QA pass).

### 4. Cross-tenant isolation smoke test

Upload as Tenant A; confirm Tenant B cannot read the same path through an authenticated client. The exact test fixture is owned by Aksha and lives in the same file family; the manual smoke is:

1. Upload via `POST /api/v1/documents/upload` with Tenant A's JWT + `X-Tenant-ID: <tenant_a>`.
2. Note the returned `storage_path` (e.g. `<tenant_a>/2026/05/<uuid>.pdf`).
3. With a Tenant B JWT, attempt a Storage SELECT on that exact path via the authenticated client — expect a Storage RLS denial.
4. Repeat with the service-role client — expect success (proves service-role bypass is intentional).

---

## Common failure modes

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `404 Bucket not found` on upload | Bucket missing on this project | Scenario B above |
| `403` on upload via authenticated client | RLS path-segment / membership check failed | Verify `(storage.foldername(name))[1]` matches a tenant the JWT subject is a member of |
| Upload accepted but file > 20 MiB rejected | Hit Supabase Storage `file_size_limit` | Increase via `UPDATE storage.buckets SET file_size_limit = ...` and update the API constant + migration to match |
| MIME rejected by Storage but not by API | Storage `allowed_mime_types` is narrower than `_ALLOWED_MIME_TYPES` in `documents.py` | Sync both — Migration is source of truth; update via a new migration |

---

## Cross-references

- API endpoint that uses the bucket: [`backend/app/api/v1/endpoints/documents.py`](../../backend/app/api/v1/endpoints/documents.py)
- Tenant membership dependency (used to validate `auth.uid()` in RLS): [`backend/app/core/tenant.py`](../../backend/app/core/tenant.py)
- Bucket-provisioning migration: [`backend/supabase/migrations/0016_storage_documents_bucket.sql`](../../backend/supabase/migrations/0016_storage_documents_bucket.sql)
- Documents table schema: [`backend/supabase/migrations/0005_documents_ai_hitl.sql`](../../backend/supabase/migrations/0005_documents_ai_hitl.sql)
- Regression tests: [`backend/tests/api/test_documents.py`](../../backend/tests/api/test_documents.py)
- Filed bug: [#100](https://github.com/venkateshbr/aethos-ps/issues/100)
