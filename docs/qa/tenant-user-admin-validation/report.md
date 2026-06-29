# Tenant User Admin Live Validation

Run ID: `2026-06-29t11-22-42`
Tenant ID: `d70f5fa4-d03f-44b5-a9a8-237e6d873d49`

- Created tenant through production signup API.
- Invited ERP manager through `/api/v1/tenant-users`.
- Verified owner Settings > Tenant Users UI shows the invited manager.
- Verified manager can log into the main Aethos app and open Reports.

Screenshots:
- [owner-tenant-users-settings.png](screenshots/owner-tenant-users-settings.png)
- [manager-reports-login.png](screenshots/manager-reports-login.png)
