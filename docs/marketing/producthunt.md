# Aethos — ProductHunt Launch Listing

> Owner: Netra (Issue #76)
> Status: Draft — ready for founder review before scheduling

---

## Tagline (max 60 chars)

Engagement letters to paid invoices — no forms

*(55 chars)*

---

## Short Description (max 260 chars)

Drop a document. Agents extract, propose, and post — you approve. GAAP double-entry under the hood. Five billing models, 13 AI specialists, 14-day free trial. Works across US, UK, Singapore, India, and Australia from day one.

*(233 chars)*

---

## Full Description

If you run a consulting firm, dev shop, advisory practice, or any other professional services business, your billing process probably looks something like this: engagement letter in Word, time tracked in Harvest or a spreadsheet, invoice assembled by copying last month's, payment chased over email, vendor bills stuffed into a folder for "later."

The bottleneck is not the work. It is the 40 minutes of admin between finishing the work and sending an invoice. Multiply that across every engagement, every month, and you have a part-time job that the founder is usually doing themselves late on a Sunday night.

Aethos is built around a single idea: the AI should do the data entry, and you should only be in the loop for decisions.

Here is what that looks like in practice. You drop your signed engagement letter into the chat. An agent reads it, extracts the client name, billing model, rate card, scope, and start date, and drafts an engagement record. You see a card with everything it found, a confidence score, and three options: Approve, Edit, or Reject. You approve in one click. The engagement is live. No form filling.

From there, you log time in the same chat — "4 hours on the Meridian strategy deck, billable" — and the agent records it against the right project and rate card. At month end, one command drafts an invoice from all unbilled time and expenses. The invoice goes out with a Stripe Payment Link attached. When the client pays, the webhook fires, the journal is posted, and your AR is closed. GAAP-compliant double-entry, automatically.

The same loop runs on the AP side. Forward a vendor invoice into chat. The agent extracts the amounts, codes the expense to the right GL account, links it to the right project, and queues it for your approval before it touches the books.

This is what agent-first means: agents do the work and surface proposals; you stay in control of every decision that matters. Every mutation that touches money lands in a Human-in-the-Loop inbox with a confidence score. Agents start cautious. They earn autonomy as they demonstrate accuracy. You set the dial.

What Aethos ships with today:
- 5 billing models: time and materials, fixed fee, milestone, retainer, and capped T&M
- 13 AI agents covering extraction, drafting, billing runs, and collections
- GAAP double-entry general ledger with period locks and reversing-entry corrections
- Stripe Payment Links on every invoice, with automatic journal posting on receipt
- Stripe Connect so your clients' payments go directly to your connected account
- Multi-currency across US, UK, Singapore, India, and Australia — with local tax rates seeded (VAT, GST, etc.)
- 14-day free trial

Who this is for: PS firms of 3 to 30 people where the founder or a senior person still owns the finance function. The person who knows billing is a mess but has not had time to fix it because fixing it requires even more manual work.

What is still v1: the timesheet UI is minimal — chat-driven entry works, but a calendar week view is coming. AP bank file export supports NACHA and universal CSV; native BACS, ABA, GIRO, and NEFT arrive in v1.1. We shipped what is real and working, not a roadmap.

---

## First Maker Comment

I spent years watching small consulting firms leave money on the table — not because the work was bad, but because the billing was slow. Engagement letters drafted in Word, invoices built from a template, AR chased manually. I have done every part of that myself.

The question I kept coming back to was: why does the human have to move the data? The engagement letter already has the rate card. The time log already has the hours. The only reason someone is retyping information into an invoice is that the tools were never designed to talk to each other.

Aethos is built on AI agents that close those gaps — but the design question I am least certain about is the Human-in-the-Loop UX. How much friction is right in the approval flow? When should an agent act on its own versus stop and ask? We have made a specific bet (confident actions first, progressive autonomy), and I would genuinely love feedback from anyone who runs a real billing workflow on whether that balance feels correct.

Thank you to our three design-partner firms who have been running real client billing on the beta. You have shaped this product more than any other input.

— [Founder name]

---

## Topics

SaaS, Accounting, AI, B2B, Productivity

---

## Launch Checklist

- [ ] Set launch date (target: Friday of Week 6)
- [ ] Schedule ProductHunt post for 12:01am PST
- [ ] Notify design partners to upvote and leave a first comment
- [ ] Post founder-voice thread on LinkedIn and Twitter on launch morning
- [ ] Prepare 5 quick-answer responses: pricing, security, vs. QuickBooks, vs. Xero, trial terms
- [ ] Gallery images: 1270x952px, exported at 2x — 5 screenshots listed in press_kit.md
- [ ] Verify all screenshot captions are under 80 chars (ProductHunt truncates)
- [ ] Confirm maker account is connected to Aethos product page before launch day
- [ ] Seed upvote ask to newsletter subscribers 24 hours before launch, not day-of
- [ ] 90-second demo video: document drop to HITL approve to invoice sent
