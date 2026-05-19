# E2E Onboarding Regression Scenario

Use this template for SaaS signup, billing, tenant provisioning, RBAC, and cleanup
regressions.

## Scenario

- Product:
- Environment:
- Frontend URL:
- API URL:
- Payment provider mode:
- Test organization/customer name:

## Preconditions

- `.env` configured with sandbox/test provider credentials.
- Webhook endpoint reachable by provider.
- Test Price IDs/products configured.
- Platform admin user available.
- Demo data cleanup path available.

## Steps

1. Open the public homepage in a browser.
2. Click Get Started.
3. Enter organization name and short name.
4. Enter initial admin details.
5. Select subscription tier and billing interval.
6. Continue to checkout.
7. Complete checkout with sandbox/test payment method.
8. Confirm return/success page.
9. Verify webhook was received and accepted.
10. Log in as initial admin through frontend.
11. Create or invite users for each supported role.
12. Create representative domain records through frontend.
13. Add financial/metric/status data through frontend when relevant.
14. Verify dashboard values and statuses in frontend.
15. Verify backend/API records reconcile with frontend.
16. Log in as restricted roles and test allowed/forbidden actions.
17. Delete or archive the demo tenant/customer through admin UI.
18. Confirm deleted tenant users cannot log in.

## Expected Results

- Subscription status is correct.
- Tenant is provisioned once.
- Initial admin can log in.
- Role permissions are enforced in UI and API.
- Dashboard totals match source records.
- Demo cleanup removes or disables tenant data as designed.

## Evidence

- Browser screenshots or recording:
- API validation commands:
- Provider webhook/event IDs:
- Records/totals validated:
- Cleanup confirmation:

