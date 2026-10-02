# Focused Demo Guide Fix Browser Validation

- URL: https://aethos.ishirock.tech
- Tenant: Meridian Advisory QA 1790714645482
- Build health SHA expected: aebba539d127253e28e8b9f5145cc897037c456b
- Console errors: 0
- Network failures: 3

## Results
### 1-6-capped-tax — PASS

Missing: none
Invalid: none
Screenshot: ../docs/qa/focused-demo-fix-2026-09-30T02-16-23-064Z/screenshots/1-6-capped-tax-response.png

```text
 Prepared a Nexus Corporation Tax Return FY2025 engagement draft.
- Client: Nexus Capital Partners.
- Service: Corporation Tax Return FY2025.
- Billing: fixed fee GBP 18,500 with a cap at GBP 22,000 if advisory hours overrun.
- Control: capped-fee scope and advisory overrun risk require Inbox approval before the engagement is created/sent.
```

### 1-7-draft-reminders — PASS

Missing: none
Invalid: none
Screenshot: ../docs/qa/focused-demo-fix-2026-09-30T02-16-23-064Z/screenshots/1-7-draft-reminders-response.png

```text
 Collections readout:
- Totals: 2 open invoices; 2 overdue; balances {'GBP': '13500.0', 'USD': '0.0'}.
- Customer: Nexus Capital Partners LP; invoice INV-1001: due 2026-06-19; aging over_90; balance GBP 9000.0; payment status unpaid; reminder count 1; policy stage final; blockers ['cooldown_active']; next action Wait for the collections cooldown before drafting another reminder..
- Customer: Thornton Tech Solutions Ltd; invoice INV-1003: due 2026-07-10; aging paid; balance USD 0.0; payment status paid; reminder count 0; policy stage none; blockers ['invoice_paid']; next action No collections action; the invoice is paid..
- Customer: Brightwater Manufacturing Ltd; invoice INV-1002: due 2026-07-25; aging 61_90; balance GBP 4500.0; payment status unpaid; reminder count 1; policy stage final; blockers ['cooldown_active']; next action Wait for the collections cooldown before drafting another reminder..
Any customer reminder email must be drafted to Inbox and approved before sending.
```

## Network failures
net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/billing/subscription-status
net::ERR_ABORTED https://aethos.ishirock.tech/api/v1/chat/threads?limit=20
net::ERR_ABORTED https://fonts.gstatic.com/s/materialicons/v145/flUhRq6tzZclQEJ-Vdg-IuiaDsNc.woff2
