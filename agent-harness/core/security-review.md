# Security Review

Prahari review is mandatory for:

- Authentication and session handling.
- JWT claims, signing, expiry, refresh, or validation.
- RBAC/ABAC/permission changes.
- Tenant isolation, RLS, or service-role usage.
- Agent tools that read/write protected data.
- External integrations, webhooks, OAuth, or payments.
- Secrets, encryption keys, or credential storage.
- Infrastructure exposure, CORS, CSP, cookies, or network boundaries.

## Prahari Checklist

- No secrets committed.
- No raw PII sent to external services.
- Least privilege is maintained.
- Tenant/user scoping is enforced in app and database where possible.
- Webhooks verify signatures.
- External callbacks validate origin and replay risk.
- Admin endpoints require explicit admin authorization.
- Logs do not contain tokens, credentials, or sensitive payloads.
- Security-sensitive failures fail closed.
- Tests cover forbidden and cross-tenant access paths.

## Secret Handling

- Use `.env.example` for variable names and placeholders.
- Keep real `.env` files ignored.
- Do not print secrets in final responses or logs.
- Rotate any secret that appears in chat, logs, commits, or screenshots.

