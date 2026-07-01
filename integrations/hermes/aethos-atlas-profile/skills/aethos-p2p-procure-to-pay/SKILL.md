# Aethos P2P Procure To Pay

Use Aethos tools for vendor bill extraction, duplicate checks, AP aging, bill-pay
proposal, payment batch status, and vendor decision trails. Money-out actions
must route through Aethos policy and Inbox.

For prompts asking which vendor bills are due soon, which are blocked, why a
bill can or cannot be paid, duplicate/PO/coding evidence, source-document
status, or payment-batch state, use the P2P payment-risk read pack first.
Summarize vendor, bill number, due date, amount, status, coding evidence,
source document, duplicate signals, PO/service-order match, payment blockers,
safe batch status, and recommended next action.

Always use the literal label "Vendor" for vendor names in payment packets. If a
vendor-invoice extraction is blocked by security or prompt-injection review,
still summarize the available project match, duplicate guard, PO/service-order
evidence, coding/account evidence, and Inbox review requirement.

Only propose a bill-payment batch after the user asks for a payment action.
Do not expose raw bank details, export hashes, internal tool names, raw payloads,
traces, logs, or context IDs.
