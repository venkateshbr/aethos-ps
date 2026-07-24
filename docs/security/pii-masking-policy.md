# PII Masking & Data-Classification Policy

**Owner:** Prahari (Security) · **Issues:** #374, #392 (LR-13) · **Status:** enforced in code

This is the source of truth for how Aethos classifies sensitive data and where it
is redacted before it leaves a trust boundary (an external LLM call, a log sink, a
trace, or a rendered document). It documents *verified* behaviour only — the demo
and user guides must not claim more than this page.

## 1. Data classification

| Class | Examples | Handling at trust boundaries |
|---|---|---|
| **C1 — Financial identifiers** | Bank account numbers, IBAN, routing/ABA/sort code/BSB, full card PAN | **Always masked** (regex, deterministic) before LLM + logs |
| **C1 — Government / tax identifiers** | SSN, US EIN, UK VAT, IN GSTIN, AU ABN, SG NRIC/FIN | **Always masked** before LLM + logs |
| **C2 — Direct contact identifiers** | Email address, phone/mobile/fax numbers | **Always masked** before LLM + logs (email keeps domain for context) |
| **C3 — Names & locations** | Person names, places/addresses in free text | Masked on the **pre-model document path** via optional NER (`mask_pii_deep`); see §4 |
| **C4 — Business data** | Invoice numbers, amounts, dates, engagement names | Not masked — required for the product to function; never blindly redacted |

C1/C2 are matched by **structured regex** because they have distinctive, auditable
shapes. C3 needs a statistical model (NER) and is a lower-severity, opt-in layer.

## 2. Where masking happens (the two boundaries)

All redaction lives in one module, `backend/app/domain/pii.py`, so the agent layer
and the logging layer share exactly one implementation.

1. **Pre-model boundary** — every text that is about to leave for an external LLM
   (document extractions, agent context) is passed through **`mask_pii_deep`**
   (`app/agents/base.py`: `build_document_content`, agent context builder). That is
   structured regex **plus** NER name/place masking where a model is installed.
2. **Pre-log boundary** — the logging formatter (`app/core/logging`) runs every log
   record's message through **`mask_pii`** (regex only — NER is far too slow per
   record). Structured logging is **deny-by-default** for sensitive payloads: the
   formatter masks the rendered message, and exception text flows through the same
   masker. See `tests/unit/test_log_pii_masking.py`.

Structured field-level maskers (`mask_registration_number`, `mask_address` in
`base.py`) redact specific document fields where the whole field is sensitive.

## 3. Coverage (what `mask_pii` redacts)

Deterministic, dependency-free, applied at both boundaries:

- **SSN** `123-45-6789` → `[REDACTED-SSN]`
- **Card PAN** 16 digits, space/dash tolerant → `[REDACTED-CARD]`
- **Tax IDs** US EIN, UK VAT (`GB#########`), IN GSTIN, AU ABN → `[REDACTED-TAX-ID]`
- **Bank accounts** IBAN (unlabelled) + account/routing/ABA/sort/BSB when
  context-labelled → `[REDACTED-BANK-ACCOUNT]`
- **SG NRIC/FIN** `S1234567D` → `[REDACTED-NRIC]`
- **Phone** international (`+CC …`), NANP grouped (`(415) 555-2671`, `415-555-2671`,
  `415.555.2671`), and context-labelled (`Mobile: …`, `Tel …`) → `[REDACTED-PHONE]`
- **Email** username redacted, domain kept → `[REDACTED]@domain`

### False-positive controls

Phone and bank-account matching is intentionally conservative so business data
survives: bare space-grouped digit runs, invoice numbers (`INV-2026-0012`), amounts
(`1,234,567.89`), ISO dates (`2026-07-25`), and PO numbers are **not** masked. These
are pinned by `tests/unit/test_agents.py::test_mask_pii_phone_no_false_positives`
and the `test_mask_pii_no_false_positives_*` cases.

## 4. Names / addresses (NER) — opt-in per environment

`mask_pii_deep` adds a spaCy NER pass (`PERSON`, `GPE`, `LOC`, `FAC`, `NORP` →
`[REDACTED-NAME]`) for the pre-model path only. It **degrades gracefully**: with no
model installed it is exactly `mask_pii` (regex-only), so CI and lean images stay
dependency-free and never crash. To enable name/place masking in an environment:

```bash
pip install spacy && python -m spacy download en_core_web_sm
# add the same to the API/Hermes container image to turn it on in production
```

It is deliberately **never** wired into the log formatter (too slow per record).

## 5. Protected paths (approved exceptions)

Some flows legitimately need unmasked identifiers and must **not** go through an
external LLM:

- **Payment execution** (Stripe, bank rails) uses raw account/card data server-side
  only; it is never placed in agent context or LLM prompts.
- **Persisted business records** (the ledger, invoices, bills) store real values in
  the tenant-isolated database (RLS) — masking applies to *egress* to third parties
  and logs, not to first-party storage.

Any new path that sends document or record text to a model MUST call `mask_pii_deep`
first; any new log call is covered automatically by the formatter.

## 6. Historical logs & retained artifacts — remediation plan

The masker protects data **going forward**. For artifacts created before this
boundary was complete:

1. **Logs** — the platform log sink has a rolling retention window; masked-forward
   plus expiry of the pre-policy window is the primary remediation. No structured C1
   identifiers were confirmed in retained logs during the #368 audit, but the
   retention window should be allowed to roll before that assumption is dropped.
2. **Traces (Langfuse/Logfire)** — same masker feeds trace text; purge any
   pre-policy traces older than the current retention window.
3. **Extracted documents** — stored extractions are first-party (RLS-scoped) and are
   not egress; they are covered by tenant data-deletion on account closure.

Owner action: confirm the log/trace retention windows have rolled past the
policy-completion date before certifying historical remediation closed.

## 7. Verified-behaviour statement (for guides)

The demo/user guides may state: *"Structured financial and government identifiers,
contact details (email/phone), and — where enabled — person and place names are
redacted before any text is sent to an external AI model or written to logs."* They
must **not** claim address/name masking is on unless the environment has the NER
model installed.
