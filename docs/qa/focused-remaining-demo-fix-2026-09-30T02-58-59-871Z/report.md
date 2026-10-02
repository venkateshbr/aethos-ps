# Focused Remaining Demo Prompt Fix Validation

Run ID: `2026-09-30T02-58-59-871Z`
Base URL: `https://aethos.ishirock.tech`
Expected build SHA: `ea385cc1118777b3c7b1c0c379b073e327578467`
Observed build SHA: `ea385cc1118777b3c7b1c0c379b073e327578467`

Counts: PASS 2 / FAIL 0
Console errors: 0
Network failures: 0

## Results

### 1-3a-delivery-data — PASS

Screenshot: `docs/qa/focused-remaining-demo-fix-2026-09-30T02-58-59-871Z/screenshots/1-3a-delivery-data-response.png`

Prompt:
```text
Show me Alice Chen's June delivery data. Summarize approved time, pending time, billable expenses, utilization, WIP, and which entries can be invoiced for Nexus.
```
Response:
```text
 Delivery and utilization context for Alice in June 2026:
- Approved hours 0; pending hours 24.0; utilization 0.00%; WIP 0.00; billable expenses 185.50.
- Invoice-ready billable expenses: 1 item(s), total 185.50.
Use the WIP and Project P&L reports for invoice-ready detail; I did not create an invoice.
```
Notes: Business-valid answer: matched 7/7 required signals.

### 1-4-billing-run — PASS

Screenshot: `docs/qa/focused-remaining-demo-fix-2026-09-30T02-58-59-871Z/screenshots/1-4-billing-run-response.png`

Prompt:
```text
Prepare the June 2026 Nexus billing run across fixed fee, monthly retainer, T&M advisory hours, and approved expenses. Show the draft invoice lines and route the invoice to Inbox before sending.
```
Response:
```text
 Prepared the Nexus 2026-06 billing run draft and routed the invoice to Inbox before sending.
Draft invoice lines:
- Group Statutory Accounts: fixed fee milestone 1/2, GBP 21,000.00.
- Monthly Management Accounts: June retainer, GBP 8,500.00.
- CFO Advisory: T&M advisory hours, 12.5 hours x GBP 350 = GBP 4,375.00.
- Approved expenses: Travel & Subsistence, GBP 843.20.
- Journal impact after approval: DR Accounts Receivable for the gross invoice; CR Revenue for fixed fee, retainer, T&M, and expenses; CR VAT/tax payable where applicable.
No invoice was sent directly. Review the Inbox invoice draft and approval task before customer delivery.
```
Notes: Business-valid answer: matched 8/8 required signals.
