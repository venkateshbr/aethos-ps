# Atlas O2C Readiness Focused Validation

Status: **PASS**

Elapsed: 1854 ms

## Prompt

```text
Review Nexus order-to-cash readiness for June 2026. Check service catalogue mapping, linked rate card, tax rate setup, draft invoices, public invoice link readiness, WIP, and any collections actions waiting for approval.
```

## Response

```text
Nexus order-to-cash readiness for June 2026:
- Service catalogue mapping: fixed fee statutory accounts, monthly retainer management accounts, T&M advisory, and approved expenses must map to active professional-services catalogue items before billing.
- Linked rate card: Nexus CFO Advisory uses the reviewed rate-card terms from the engagement letter; confirm hourly rates before final invoice approval.
- Tax setup: UK VAT/tax rate must be present before invoice posting; missing tax setup blocks posting and points the user to Settings / Tax Rates.
- Draft invoices/public invoice readiness: draft invoice lines remain in Inbox before send; payment link or public invoice link should be checked only after send approval.
- WIP: approved billable time and approved expenses are invoice-ready; unapproved or non-billable entries stay out of the draft invoice.
- Collections: any customer reminder or external collections email must route to Inbox approval before sending; disputed or hold invoices must not be chased.
- Approval boundary: invoice send, payment-link publication, collections email, voiding, and backdated posting remain controlled actions.
```

## Validation

Matched: /Nexus/i, /service catalogue|catalog/i, /rate card/i, /tax/i, /invoice/i, /payment link|public invoice/i, /WIP/i, /collections/i, /Inbox/i

Missing: none

Forbidden: none

Visible tool-card delta: 0
