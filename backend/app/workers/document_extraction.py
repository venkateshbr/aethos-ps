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

from app.agents.base import AgentDeps
from app.agents.engagement_letter_agent import run_engagement_letter_agent
from app.agents.expense_extractor_agent import run_expense_extractor_agent
from app.agents.schemas import BillDraft, EngagementDraft, ProjectExpenseDraft
from app.agents.suggestion_writer import write_agent_suggestion
from app.agents.vendor_invoice_agent import run_vendor_invoice_agent
from app.core.config import settings
from app.workers.procrastinate_app import app
from supabase import create_client

logger = logging.getLogger(__name__)

# Supabase bucket where uploaded documents are stored
DOCUMENTS_BUCKET = "documents"

# Default autonomy level — L2 (suggest) per PLAN §6.5
DEFAULT_AUTONOMY_LEVEL = 2
CONFIDENCE_THRESHOLD = 0.90


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

        filename = document.get("filename") or storage_path.split("/")[-1]
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
