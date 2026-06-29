"""Document Extraction Procrastinate task.

Dispatched by the file-upload pipeline when a new document is uploaded.
Classifies the document type by filename heuristic, downloads the file bytes
from Supabase Storage, runs the appropriate extraction agent, and persists
the agent suggestion + HITL task.

Graceful degradation contract:
- On ANY exception (Anthropic unavailable, network error, parse failure):
  - Update documents.status = 'failed'
  - Log the error with full context
  - Return without raising — the document is not lost; the user can retry from Inbox

PII rule:
- mask_pii() is applied inside each agent before any LLM call
- This worker never logs document content or LLM prompts/responses

v1 classifier: filename keyword heuristic.
  "engagement" or "letter" or "sow" in filename → engagement_letter_agent
  "receipt" or "expense" or "reimbursement" in filename → expense_extractor_agent
  anything else → vendor_invoice_agent (default)

The real document-type classifier lives in Week 4 (copilot_agent router).
"""

from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.agents.base import AgentDeps
from app.agents.engagement_letter_agent import run_engagement_letter_agent
from app.agents.expense_extractor_agent import run_expense_extractor_agent
from app.agents.schemas import BillDraft, EngagementDraft, ProjectExpenseDraft
from app.agents.suggestion_writer import write_agent_suggestion
from app.agents.vendor_invoice_agent import run_vendor_invoice_agent
from app.core.config import settings
from app.domain.money import serialise_money
from app.workers.procrastinate_app import app
from supabase import create_client

logger = logging.getLogger(__name__)

# Supabase bucket where uploaded documents are stored
DOCUMENTS_BUCKET = "documents"

# Default autonomy level — L2 (suggest) per PLAN §6.5
DEFAULT_AUTONOMY_LEVEL = 2
CONFIDENCE_THRESHOLD = 0.90

_BILLING_ARRANGEMENTS = {
    "time_and_materials",
    "fixed_fee",
    "retainer",
    "retainer_draw",
    "milestone",
    "capped_tm",
    "mixed",
}
_BILLING_ALIASES = {
    "t&m": "time_and_materials",
    "tm": "time_and_materials",
    "time_and_materials": "time_and_materials",
    "time_and_material": "time_and_materials",
    "time_materials": "time_and_materials",
    "time_material": "time_and_materials",
    "time_and_materials_basis": "time_and_materials",
    "fixed": "fixed_fee",
    "fixed_fee": "fixed_fee",
    "fixed_price": "fixed_fee",
    "retainer": "retainer",
    "monthly_retainer": "retainer",
    "retainer_draw": "retainer_draw",
    "drawdown_retainer": "retainer_draw",
    "milestone": "milestone",
    "milestones": "milestone",
    "capped_tm": "capped_tm",
    "capped_t&m": "capped_tm",
    "capped_time_and_materials": "capped_tm",
    "mixed": "mixed",
}
_BILLING_TERM_MONEY_KEYS = (
    "fixed_fee_amount",
    "milestone_total",
    "retainer_monthly_amount",
    "retainer_floor",
    "cap_amount",
)
_AMOUNT_RE = re.compile(
    r"(?:(?:USD|GBP|SGD|INR|AUD|EUR|\$|£|S\$|A\$|₹)\s*)?"
    r"(?P<amount>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _classify_document_type(filename: str) -> str:
    """Classify document type from filename keywords.

    Returns one of: 'engagement_letter', 'expense', 'vendor_invoice'.
    Default is 'vendor_invoice' when no keyword matches.
    """
    lower = filename.lower()
    if "engagement" in lower or "letter" in lower or "sow" in lower:
        return "engagement_letter"
    if "receipt" in lower or "expense" in lower or "reimbursement" in lower:
        return "expense"
    return "vendor_invoice"


def _get_mime_type(filename: str) -> str:
    """Infer MIME type from file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".txt"):
        return "text/plain"
    # Default: treat as text for extraction purposes
    return "text/plain"


def _normalise_money(value: object) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = (
        raw.replace(",", "")
        .replace("S$", "")
        .replace("A$", "")
        .replace("£", "")
        .replace("$", "")
        .replace("₹", "")
        .strip()
    )
    raw = re.sub(r"^(USD|GBP|SGD|INR|AUD|EUR)\s+", "", raw, flags=re.IGNORECASE)
    try:
        return serialise_money(Decimal(raw))
    except (InvalidOperation, ValueError):
        return None


def _engagement_text(output: dict) -> str:
    parts: list[str] = []
    for key in (
        "billing_arrangement",
        "engagement_name",
        "scope_summary",
        "first_project_name",
        "first_project_description",
        "rate_card_summary",
    ):
        value = output.get(key)
        if isinstance(value, str):
            parts.append(value)
    for hint in output.get("rate_card_hints") or []:
        if not isinstance(hint, dict):
            continue
        role = hint.get("role")
        rate = hint.get("rate")
        if role:
            parts.append(str(role))
        if rate:
            parts.append(f"{rate} per hour")
    return " ".join(parts)


def _has_rate_card_hints(output: dict) -> bool:
    hints = output.get("rate_card_hints")
    return isinstance(hints, list) and any(
        isinstance(hint, dict) and hint.get("rate") for hint in hints
    )


def _looks_like_mixed_billing(output: dict) -> bool:
    text = _engagement_text(output).lower()
    if "mixed" in text:
        return True
    has_fixed = any(token in text for token in ("fixed fee", "fixed_fee", "fixed price"))
    has_retainer = any(token in text for token in ("retainer", "per month", "monthly"))
    has_tm = (
        any(
            token in text
            for token in (
                "time and materials",
                "time_and_materials",
                "t&m",
                "per hour",
                "/hr",
                "hourly",
            )
        )
        or _has_rate_card_hints(output)
    )
    return has_fixed and (has_retainer or has_tm)


def _normalise_billing_arrangement(output: dict) -> str:
    if _looks_like_mixed_billing(output):
        return "mixed"
    raw = str(output.get("billing_arrangement") or "").strip().lower()
    raw = raw.replace(" ", "_").replace("-", "_").replace("/", "_")
    if raw in _BILLING_ALIASES:
        return _BILLING_ALIASES[raw]
    if raw in _BILLING_ARRANGEMENTS:
        return raw
    return "time_and_materials"


def _extract_billing_terms(output: dict) -> dict[str, str]:
    terms: dict[str, str] = {}
    nested_terms = output.get("billing_terms") if isinstance(output.get("billing_terms"), dict) else {}
    for key in _BILLING_TERM_MONEY_KEYS:
        value = output.get(key)
        if value in (None, "") and isinstance(nested_terms, dict):
            value = nested_terms.get(key)
        normalised = _normalise_money(value)
        if normalised is not None:
            terms[key] = normalised

    text = _engagement_text(output)
    lower = text.lower()
    for match in _AMOUNT_RE.finditer(text):
        raw_amount = match.group("amount")
        amount = _normalise_money(raw_amount)
        if amount is None:
            continue
        before = lower[max(0, match.start() - 50) : match.start()]
        after = lower[match.end() : min(len(text), match.end() + 50)]
        direct_after = after[:30]
        context = f"{before[-40:]} {direct_after}"
        if "%" in context or "percent" in context:
            continue
        if any(token in direct_after for token in ("per hour", "/hr", "hourly", "hour ")):
            continue
        if (
            any(token in context for token in ("fixed fee", "fixed_fee", "fixed price"))
            and "fixed_fee_amount" not in terms
        ):
            terms["fixed_fee_amount"] = amount
        elif "milestone" in context and "milestone_total" not in terms:
            terms["milestone_total"] = amount
        elif any(token in context for token in ("cap", "capped")) and "cap_amount" not in terms:
            terms["cap_amount"] = amount
        elif (
            any(token in context for token in ("per month", "monthly", "retainer"))
            and "retainer_monthly_amount" not in terms
        ):
            terms["retainer_monthly_amount"] = amount
    return terms


def _inclusive_month_count(start: object, end: object) -> int | None:
    try:
        start_date = date.fromisoformat(str(start))
        end_date = date.fromisoformat(str(end))
    except (TypeError, ValueError):
        return None
    if end_date < start_date:
        return None
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1


def _retainer_month_count(output: dict) -> int | None:
    months = _inclusive_month_count(output.get("start_date"), output.get("end_date"))
    if months:
        return months
    match = re.search(r"\b(\d{1,2})\s+months?\b", _engagement_text(output), re.IGNORECASE)
    if not match:
        return None
    count = int(match.group(1))
    return count if 1 <= count <= 60 else None


def _infer_total_value(output: dict, terms: dict[str, str]) -> str | None:
    existing = _normalise_money(output.get("total_value"))
    if existing is not None:
        return existing

    total = Decimal("0")
    for key in ("fixed_fee_amount", "milestone_total", "cap_amount"):
        if terms.get(key):
            total += Decimal(terms[key])

    monthly_retainer = terms.get("retainer_monthly_amount")
    months = _retainer_month_count(output)
    if monthly_retainer and months:
        total += Decimal(monthly_retainer) * Decimal(months)

    if total <= Decimal("0"):
        return None
    return serialise_money(total)


def _normalise_engagement_onboarding_output(output: dict) -> dict:
    """Ensure engagement-letter HITL payloads contain the full onboarding proposal."""
    result = dict(output)
    client_name = str(result.get("client_name") or "").strip() or "Unknown Client"
    scope_summary = str(result.get("scope_summary") or "").strip()
    result["billing_arrangement"] = _normalise_billing_arrangement(result)

    terms = _extract_billing_terms(result)
    for key, value in terms.items():
        result[key] = value

    inferred_total_value = _infer_total_value(result, terms)
    if inferred_total_value is not None:
        result["total_value"] = inferred_total_value

    engagement_name = str(result.get("engagement_name") or "").strip()
    if not engagement_name:
        engagement_name = f"{client_name} Engagement"
    result["engagement_name"] = engagement_name

    first_project_name = str(result.get("first_project_name") or "").strip()
    if not first_project_name:
        first_project_name = "General"
    result["first_project_name"] = first_project_name

    first_project_description = str(result.get("first_project_description") or "").strip()
    if not first_project_description and scope_summary:
        first_project_description = scope_summary
    if first_project_description:
        result["first_project_description"] = first_project_description

    hints = result.get("rate_card_hints") or []
    if isinstance(hints, list) and hints:
        currency = str(result.get("currency") or "USD").upper()
        parts: list[str] = []
        for hint in hints:
            if not isinstance(hint, dict):
                continue
            role = str(hint.get("role") or "").strip()
            rate = str(hint.get("rate") or "").strip()
            if role and rate:
                parts.append(f"{role}: {currency} {rate}/hr")
        if parts:
            result["rate_card_summary"] = "; ".join(parts)

    result["onboarding_intent"] = "create_client_engagement_project"
    return result


def _normalise_vendor_invoice_output(output: dict, draft: BillDraft) -> dict:
    """Attach vendor-match, coding, and review exception evidence to bill drafts."""
    result = dict(output)
    vendor_match = getattr(draft, "_vendor_match", None)
    gl_suggestions = getattr(draft, "_gl_suggestions", None) or []
    if vendor_match is not None:
        result["vendor_match"] = vendor_match.model_dump(mode="json")
        matched_client_id = result["vendor_match"].get("matched_client_id")
        if matched_client_id:
            result["client_id"] = matched_client_id

    serialised_gl: list[dict | None] = []
    lines = result.get("lines") if isinstance(result.get("lines"), list) else []
    for index, suggestion in enumerate(gl_suggestions):
        if suggestion is None:
            serialised_gl.append(None)
            continue
        suggestion_dict = suggestion.model_dump(mode="json")
        serialised_gl.append(suggestion_dict)
        if index < len(lines) and isinstance(lines[index], dict):
            confidence = float(suggestion_dict.get("confidence") or 0)
            if confidence >= 0.75 and not lines[index].get("account_id"):
                lines[index]["account_id"] = suggestion_dict.get("account_id")
                lines[index]["account_code"] = suggestion_dict.get("account_code")
                lines[index]["account_name"] = suggestion_dict.get("account_name")
                lines[index]["coding_source"] = "ai_gl_suggestion"
    result["gl_suggestions"] = serialised_gl

    result["match_status"] = _vendor_invoice_match_status(result)
    result["coding_status"] = _vendor_invoice_coding_status(result)
    result["review_exceptions"] = _vendor_invoice_review_exceptions(result)
    return result


def _vendor_invoice_match_status(output: dict) -> str:
    if output.get("possible_duplicate"):
        return "duplicate_review_required"
    vendor_match = output.get("vendor_match") if isinstance(output.get("vendor_match"), dict) else {}
    if vendor_match.get("matched_client_id"):
        confidence = float(vendor_match.get("confidence") or 0)
        return "matched" if confidence >= 0.70 else "match_review_required"
    return "new_vendor_review_required"


def _vendor_invoice_coding_status(output: dict) -> str:
    lines = output.get("lines") if isinstance(output.get("lines"), list) else []
    if not lines:
        return "needs_review"
    coded_count = sum(1 for line in lines if isinstance(line, dict) and line.get("account_id"))
    return "coded" if coded_count == len(lines) else "needs_review"


def _vendor_invoice_review_exceptions(output: dict) -> list[dict]:
    exceptions: list[dict] = []
    if output.get("possible_duplicate"):
        exceptions.append(
            {
                "code": "possible_duplicate",
                "severity": "high",
                "message": "A bill with this vendor invoice number may already exist.",
            }
        )
    if output.get("anomaly_detected"):
        exceptions.append(
            {
                "code": "amount_or_date_anomaly",
                "severity": "high",
                "message": "The extracted invoice has an amount, date, or total anomaly.",
            }
        )
    if output.get("suspected_injection"):
        exceptions.append(
            {
                "code": "suspected_prompt_injection",
                "severity": "critical",
                "message": "The source document may contain adversarial instructions.",
            }
        )
    for warning in output.get("tax_id_warnings") or []:
        exceptions.append(
            {
                "code": "tax_id_warning",
                "severity": "medium",
                "message": str(warning),
            }
        )
    if output.get("match_status") in {"new_vendor_review_required", "match_review_required"}:
        exceptions.append(
            {
                "code": output["match_status"],
                "severity": "medium",
                "message": "Vendor match needs human review before bill creation.",
            }
        )
    if output.get("coding_status") == "needs_review":
        exceptions.append(
            {
                "code": "coding_needs_review",
                "severity": "medium",
                "message": "One or more invoice lines need GL/account coding review.",
            }
        )
    return exceptions


@app.task(name="extract_document_worker", queue="extraction")
async def extract_document_worker(document_id: str, tenant_id: str) -> dict:
    """Procrastinate task entrypoint for document extraction.

    Steps:
    1. Build a service-role Supabase client (fresh per job — pooled in Week 4 by Sthira)
    2. Fetch the document row; update status = 'extracting'
    3. Download file bytes from Supabase Storage
    4. Classify document type by filename heuristic
    5. Dispatch to the appropriate extraction agent
    6. Write agent_suggestion + hitl_task via suggestion_writer
    7. Update document status = 'extracted'

    On any exception: update status = 'failed', log error, return gracefully.
    """
    logger.info(
        "extract_document_worker: starting",
        extra={"document_id": document_id, "tenant_id": tenant_id},
    )

    # Instantiate a fresh service-role client.
    # Not ideal (should use pooled connection); revisit once Procrastinate
    # context-injection lands a shared pool.
    db = create_client(settings.supabase_url, settings.supabase_service_role_key)

    deps = AgentDeps(tenant_id=tenant_id, user_id=None, db=db)

    try:
        # Step 1: Fetch document row
        doc_result = (
            db.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("tenant_id", tenant_id)
            .single()
            .execute()
        )
        document = doc_result.data
        if not document:
            logger.error(
                "extract_document_worker: document not found",
                extra={"document_id": document_id, "tenant_id": tenant_id},
            )
            return {"status": "not_found", "document_id": document_id}

        # Step 2: Mark as extracting
        db.table("documents").update({"status": "extracting"}).eq("id", document_id).execute()

        # Step 3: Download file bytes from Supabase Storage
        storage_path = document.get("storage_path") or document.get("file_path", "")
        if not storage_path:
            raise ValueError(f"Document {document_id} has no storage_path")

        file_response = db.storage.from_(DOCUMENTS_BUCKET).download(storage_path)
        document_bytes: bytes = file_response

        # #125 — read the canonical `original_filename` column (not the
        # misnamed `filename` key, which never existed on the row). Falls
        # back to the storage_path tail for legacy rows uploaded before
        # the fix landed.
        filename = (
            document.get("original_filename")
            or document.get("filename")
            or storage_path.split("/")[-1]
        )
        mime_type = document.get("mime_type") or _get_mime_type(filename)

        # Step 4: Classify
        doc_type = _classify_document_type(filename)

        logger.info(
            "extract_document_worker: dispatching agent",
            extra={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "doc_type": doc_type,
                "mime_type": mime_type,
                "bytes_size": len(document_bytes),
            },
        )

        # Step 5: Dispatch to appropriate agent
        draft: EngagementDraft | ProjectExpenseDraft | BillDraft
        agent_name: str
        action_type: str

        if doc_type == "engagement_letter":
            draft = await run_engagement_letter_agent(document_id, deps, document_bytes, mime_type)
            agent_name = "engagement_letter_agent"
            action_type = "create_engagement_draft"
        elif doc_type == "expense":
            draft = await run_expense_extractor_agent(document_id, deps, document_bytes, mime_type)
            agent_name = "expense_extractor_agent"
            action_type = "create_expense_draft"
        else:
            draft = await run_vendor_invoice_agent(document_id, deps, document_bytes, mime_type)
            agent_name = "vendor_invoice_agent"
            action_type = "create_bill_draft"

        # Step 6: Persist agent suggestion + HITL task
        output_dict = draft.model_dump(mode="json")
        if doc_type == "engagement_letter":
            output_dict = _normalise_engagement_onboarding_output(output_dict)
        elif doc_type == "vendor_invoice":
            output_dict = _normalise_vendor_invoice_output(output_dict, draft)
        await write_agent_suggestion(
            deps=deps,
            agent_name=agent_name,
            action_type=action_type,
            document_id=document_id,
            output=output_dict,
            confidence=draft.confidence,
            autonomy_level=DEFAULT_AUTONOMY_LEVEL,
            confidence_threshold=CONFIDENCE_THRESHOLD,
        )

        # Step 7: Mark document as extracted
        db.table("documents").update({"status": "extracted"}).eq("id", document_id).execute()

        logger.info(
            "extract_document_worker: completed",
            extra={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "doc_type": doc_type,
                "agent_name": agent_name,
                "confidence": draft.confidence,
            },
        )
        return {"status": "extracted", "document_id": document_id}

    except Exception as exc:
        # Graceful degradation — document is not lost; user can retry from Inbox
        logger.error(
            "extract_document_worker: failed",
            extra={
                "document_id": document_id,
                "tenant_id": tenant_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        try:
            db.table("documents").update({"status": "failed"}).eq("id", document_id).execute()
        except Exception as update_exc:
            logger.error(
                "extract_document_worker: could not update document status to failed",
                extra={"document_id": document_id, "error": str(update_exc)},
            )
        return {"status": "failed", "document_id": document_id}
