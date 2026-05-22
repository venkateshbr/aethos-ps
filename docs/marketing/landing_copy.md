# Landing Page Copy

> Owner: Netra (Issue #76)
> Status: Draft — ready for founder review

---

## Global (en-US base)

### Hero

**Headline:** Engagement to cash. Without the forms.

**Subhead:** Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. GAAP double-entry under the hood. Works for US, UK, Singapore, India, and Australia.

**CTA:** Start your 14-day free trial

**Below CTA (fine print):** No credit card required to start.

---

### Three Features

**1. Chat-first, not form-first**

The primary interface is a conversation. Drop a document — engagement letter, receipt, vendor invoice — and an AI agent extracts the structured data and presents a proposal. Describe a transaction in plain English — "4 hours on the Meridian deck, billable" — and it is recorded. Every interaction that should feel like filling out a form has been replaced by a message and a one-click approval.

**2. Every billing model, one place**

Professional services firms do not bill in a single way, and Aethos does not ask them to choose one. Time and materials, fixed fee, milestone, retainer, and capped T&M are all supported natively on a single engagement. Switch billing models across phases, run mixed engagements with a retainer floor and T&M overage, and generate invoices that reflect exactly what was agreed — without rebuilding a template each time.

**3. Get paid faster with Stripe**

Every invoice includes a Stripe Payment Link that your client can pay in two clicks, no login required. When payment arrives, the webhook fires and the AR journal entry posts automatically — no manual reconciliation. Stripe Connect routes payments directly to your firm's connected account; Aethos takes nothing from the transaction in v1. You close the month and the books close with it.

---

### Social Proof (placeholders — replace with design-partner quotes post-LOI)

"[Quote from design partner 1 — specifically about the document extraction or HITL flow]"
— [Name], [Title], [Firm type, e.g. "12-person management consultancy, Chicago"]

"[Quote from design partner 2 — specifically about billing models or invoice speed]"
— [Name], [Title], [Firm type, e.g. "8-person dev shop, London"]

"[Quote from design partner 3 — specifically about the GL or accounting accuracy]"
— [Name], [Title], [Firm type, e.g. "20-person advisory firm, Singapore"]

---

### Pricing

| Plan | Price | Who it is for |
|---|---|---|
| Starter | $29/mo | Solo practitioners and firms up to 5 people who need clean invoicing and a real GL without the overhead of a full ERP. |
| Growth | $79/mo | Growing firms of 5 to 20 people running multiple concurrent engagements with mixed billing models and a team to manage. |
| Pro | $199/mo | Established practices of 20 to 50 people who need full AP workflows, billing-run automation, and advanced agent autonomy controls. |

All plans include the 14-day free trial. No permanent free tier — we want users who use it in real workflows.

---

### FAQ

**Q: Is my financial data secure?**
A: All data is stored in an isolated, tenant-scoped database with row-level security. We never mix tenant data. Financial transactions are encrypted at rest and in transit. No raw PII (account numbers, tax IDs, card details) is ever sent to an AI model — values are masked before any LLM call. We are happy to walk you through the architecture on a call.

**Q: Does Aethos replace my accountant?**
A: No, and we do not want it to. Aethos handles the data entry, the journal posting, and the routine workflows that should not require a human. Your accountant reviews, interprets, and advises — that is what they should be spending time on. Aethos produces a clean, GAAP-compliant general ledger that your accountant or auditor can work with directly.

**Q: Which accounting standards does Aethos follow?**
A: The GL is GAAP-compliant double-entry accounting — debits equal credits on every transaction. Posted entries are immutable; corrections go through reversing entries, not overwrites. The product is designed for US GAAP and is consistent with IFRS for the core balance-sheet and P&L treatment. Jurisdiction-specific compliance (ASC 606, FRS 102, Ind AS) is the firm's accountant's responsibility in v1; automated rev-rec agent is on the roadmap for v1.1.

**Q: What integrations are available at launch?**
A: Stripe (SaaS subscriptions, Payment Links, and Connect for firm payouts), Resend (transactional and invoice email), Supabase Auth, and NACHA/CSV bank file export for AP bill payments. Xero and QuickBooks data import, native BACS/ABA/GIRO/NEFT bank files, and a public API are planned for v1.1. If there is a specific integration blocking your trial, tell us — it directly affects the roadmap.

**Q: What support do I get during the beta?**
A: All beta users get async email support with a 24-hour response SLA. Design-partner firms (three available — see the design-partner program) get a direct founder line, weekly 30-minute calls for the first six weeks, and white-glove data onboarding. If you are evaluating Aethos for a real workflow, reach out directly and we will make the onboarding work.

---

## UK Variant

### Hero

**Headline:** Engagement to cash. Without the forms.

**Subhead:** Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. GAAP-consistent double-entry under the hood, with VAT handled. Built for UK professional services from day one.

**CTA:** Start your 14-day free trial

**Below CTA:** No card required to start. UK pricing in GBP.

---

### Features (UK-specific notes)

Same three features as global. Add to the "Get paid faster with Stripe" feature: Stripe Payment Links work in GBP; Stripe Tax calculates VAT on your SaaS subscription automatically; UK firms using BACS for vendor bill payments will get native BACS file export in v1.1 (universal CSV export available now).

---

### Pricing (UK)

| Plan | Price | Who it is for |
|---|---|---|
| Starter | £25/mo | Solo practitioners and small practices up to 5 people needing clean invoicing, VAT coding, and a proper GL without the cost of a full ERP. |
| Growth | £69/mo | Growing UK firms of 5 to 20 people with multiple engagements, VAT-registered clients, and a team to coordinate. |
| Pro | £179/mo | Established UK practices needing full AP workflows, VAT rate management across standard (20%), reduced (5%), and zero-rated transactions, and advanced automation. |

---

### UK FAQ Additions

**Q: Does Aethos handle VAT?**
A: Yes. UK tenants get VAT rates pre-seeded at signup (20% standard, 5% reduced, 0% zero-rated). Each invoice line carries a tax code and tax amount. VAT totals are broken out on the invoice and in the GL. VAT return preparation (Making Tax Digital) is not automated in v1 — export your GL data to your accountant or VAT software. MTD integration is on the roadmap.

**Q: Do I need to register with Companies House to use Aethos?**
A: No. Aethos is accounting and billing software — it does not interact with Companies House filings. If your firm is incorporated, the registered address and company number can be stored in Settings and appear on your invoice headers.

---

## Singapore Variant

### Hero

**Headline:** Engagement to cash. Without the forms.

**Subhead:** Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. GAAP double-entry with GST at 9% under the hood. Built for Singapore professional services firms.

**CTA:** Start your 14-day free trial

**Below CTA:** No card required to start. Singapore pricing in SGD.

---

### Pricing (Singapore)

| Plan | Price | Who it is for |
|---|---|---|
| Starter | S$39/mo | Solo consultants and small practices needing clean invoicing, GST-compliant billing, and a real GL without the cost of enterprise software. |
| Growth | S$109/mo | Growing Singapore firms of 5 to 20 people managing multiple client engagements with multi-currency billing (SGD + USD/GBP for international clients). |
| Pro | S$279/mo | Established Singapore practices — advisory, consulting, finance, or tech — needing full AP automation, GST reconciliation support, and advanced agent autonomy. |

---

### Singapore FAQ Additions

**Q: Does Aethos handle Singapore GST?**
A: Yes. Singapore tenants get GST pre-seeded at 9% at signup. Each invoice and bill line carries a tax code and GST amount. GST-inclusive and GST-exclusive billing are both supported. GST F5/F7 return automation is not in v1 — export GL data to your tax advisor. MAS reporting is outside scope in v1.

**Q: Can I bill international clients in USD or GBP from my Singapore entity?**
A: Yes. Aethos supports per-engagement and per-invoice currency override. Your firm books in SGD as the base currency; invoices to international clients can be in USD, GBP, or any supported currency. FX rates are fetched daily and stored; journal lines record both the foreign amount and the SGD base equivalent.

---

## India Variant

### Hero

**Headline:** Engagement to cash. Without the forms.

**Subhead:** Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. Double-entry accounting with GST rates seeded for all slabs. Built for Indian consulting and CA firms.

**CTA:** Start your 14-day free trial

**Below CTA:** No card required. India pricing in INR.

---

### Pricing (India)

| Plan | Price | Who it is for |
|---|---|---|
| Starter | ₹2,499/mo | Solo consultants, freelance advisors, and CA practices with project billing needs and a preference for a clean, AI-assisted workflow over spreadsheets. |
| Growth | ₹6,999/mo | Growing Indian consulting firms of 5 to 20 people managing retainer and milestone engagements with multiple clients across GST categories. |
| Pro | ₹17,999/mo | Established advisory, IT consulting, or CA firms needing full AP bill workflow, NEFT/RTGS export support (v1.1), and advanced billing automation. |

---

### India FAQ Additions

**Q: Which GST slabs does Aethos support?**
A: All five GST slabs are pre-seeded at signup: 0%, 5%, 12%, 18%, and 28%. Each invoice and bill line carries a GST code and tax amount. CGST/SGST/IGST split is available as a manual override in v1; automated split based on supply type and state is on the roadmap for v1.1.

**Q: Can CA firms use Aethos for their own practice billing?**
A: Yes — and CA firms are one of our priority segments. CA practices often have the most sophisticated understanding of what a correct journal entry looks like, and Aethos is designed to produce exactly that. The AI extraction confidence scores and the HITL approval flow are designed so that a finance professional can audit every agent-proposed entry before it posts. We welcome CA firms as design partners.

**Q: Does Aethos support INR invoicing for international clients?**
A: You can invoice international clients in USD, GBP, SGD, or AUD from your India entity. FEMA and RBI compliance for foreign currency invoices is your CA's responsibility; Aethos records the transaction in both the invoice currency and INR equivalent using daily FX rates.

---

## Australia Variant

### Hero

**Headline:** Engagement to cash. Without the forms.

**Subhead:** Drop your engagement letter. Aethos extracts, proposes, and posts — you approve. GAAP-consistent double-entry with GST at 10% under the hood. Built for Australian professional services firms.

**CTA:** Start your 14-day free trial

**Below CTA:** No card required to start. Australia pricing in AUD.

---

### Pricing (Australia)

| Plan | Price | Who it is for |
|---|---|---|
| Starter | A$45/mo | Solo practitioners and small practices up to 5 people who want clean AI-assisted invoicing and a real GL without paying for a full ERP. |
| Growth | A$119/mo | Growing Australian firms of 5 to 20 people with multiple concurrent engagements, mixed billing models, and a team to coordinate. |
| Pro | A$299/mo | Established Australian consulting, advisory, or professional services practices needing full AP automation, GST reconciliation, and advanced billing run controls. |

---

### Australia FAQ Additions

**Q: Does Aethos handle Australian GST?**
A: Yes. Australian tenants get GST pre-seeded at 10% and GST-0% (exports) at signup. Each invoice and bill line carries a GST code. GST-inclusive pricing is supported for domestic clients. BAS (Business Activity Statement) preparation is not automated in v1 — export your GL to your accountant or accounting software. ABA file export for bill payments is planned for v1.1 (universal CSV is available now).

**Q: We currently use Xero. How hard is the migration?**
A: Aethos does not have a Xero connector in v1 — we are being honest about that. Design-partner firms get white-glove manual onboarding, which means we migrate your client list, chart of accounts, and open AR from a CSV export. A Xero import connector is a high-priority v1.1 item, and design partners directly influence that timeline. If migrating from Xero is your blocker, reach out — we will prioritise accordingly.

**Q: Does Aethos work with Australian banks for bill payments?**
A: NACHA (US ACH format) and universal CSV are available at launch. ABA file format for Australian bank bulk payment portals is planned for v1.1. In the meantime, the universal CSV export maps to the column format accepted by most Australian bank business portals (ANZ, CBA, Westpac, NAB). We document the column mapping per bank in the help centre.
