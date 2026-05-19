# SaaS Onboarding And Payments Playbook

Use this playbook for customer signup, subscription checkout, tenant provisioning,
billing portal, webhook, and platform-admin workflows.

## Lessons Learned

- The frontend flow is the truth for onboarding acceptance. API scripts are useful
  helpers, but they do not prove a customer can sign up.
- Webhooks must be tested through the public/tunneled backend URL, not only by
  calling handler code locally.
- Payment provider objects and application tenant objects must reconcile:
  checkout session, customer, subscription, organization, initial admin, and
  billing settings.
- Provisioning must be idempotent because providers can retry webhooks.
- Role checks need both UI and API verification. Hiding a button is not enough;
  returning 403 is not enough by itself either.
- Demo data cleanup is a product requirement for repeatable sales/testing flows.
- Dashboards should be validated in the frontend after data creation, especially
  money totals and status rollups.

## Required Flow

1. Open the public marketing/home page.
2. Navigate to Get Started.
3. Enter organization details and initial admin details.
4. Start sandbox checkout from the frontend.
5. Complete provider checkout with a sandbox/test payment method.
6. Confirm the success/return page is shown.
7. Verify webhook delivery and signature validation.
8. Verify tenant provisioning:
   - organization exists.
   - initial admin exists.
   - provider customer/subscription IDs are recorded.
   - billing status is correct.
9. Log in as the initial admin through the frontend.
10. Invite or create representative users.
11. Create representative domain records through the frontend.
12. Validate dashboards and totals in the frontend.
13. Validate the same totals through API/database checks.
14. Log in as each role and verify allowed/forbidden behavior.
15. Clean up the demo tenant/customer through admin UI or documented cleanup path.

## Stripe-Specific Checklist

- Use test-mode keys for development and regression.
- Use test card numbers or payment methods from Stripe's official docs.
- Configure webhook endpoint to the reachable backend URL.
- Subscribe to at least:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Verify the webhook signing secret matches the endpoint.
- Confirm Price IDs are from the same Stripe mode as the API keys.
- Never mix test and live keys or Price IDs.
- Never commit keys, webhook secrets, customer IDs tied to real customers, or
  payment method data.

## Evidence Template

```markdown
## Onboarding Regression Evidence

- Frontend URL:
- API URL:
- Payment provider mode: sandbox/test
- Checkout session/test customer reference:
- Tenant created:
- Initial admin login verified:
- Domain records created through UI:
- Dashboard totals verified in UI:
- Backend/API reconciliation:
- RBAC roles tested:
- Demo cleanup completed:
- Issues found:
- Residual risk:
```

