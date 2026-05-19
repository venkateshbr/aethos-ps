"""ARQ worker: document extraction stub.

Week 2 implementation — picks up ``extract_document_worker`` jobs enqueued by
the ``POST /documents/upload`` endpoint and logs receipt.

Week 3 will wire this worker to the specialist agents:
  - ``engagement_letter_agent`` for engagement letters / SOWs
  - ``vendor_invoice_agent`` for AP vendor invoices
  - ``expense_extractor_agent`` for receipts

For now the worker acknowledges the job, logs the document_id, and returns a
stub result.  The ``documents.status`` column update is deferred to Week 3
when the worker has a real Supabase client in its ARQ context (Sthira wires
the Redis → Supabase context plumbing).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def extract_document_worker(ctx: dict, document_id: str, tenant_id: str) -> dict:
    """Document extraction worker — stub for Week 2.

    Week 3 will:
    1. Fetch the ``documents`` row to get storage_path and mime_type.
    2. Download the file from Supabase Storage.
    3. Classify the document type (engagement_letter / receipt / vendor_invoice).
    4. Dispatch to the appropriate PydanticAI specialist agent.
    5. Write ``extraction_results`` row + create ``agent_suggestions`` / ``hitl_tasks``.
    6. Update ``documents.status`` to "extracted" or "failed".
    7. Emit a Supabase realtime event so the UI updates.

    Args:
        ctx:         ARQ worker context (Redis connection, job metadata).
        document_id: UUID of the ``documents`` row to process.
        tenant_id:   Tenant scope for RLS.

    Returns:
        Stub result dict. Replace with real extraction output in Week 3.
    """
    logger.info(
        "extract_document_worker picked up job",
        extra={"document_id": document_id, "tenant_id": tenant_id},
    )

    # TODO Week 3: classify document type, dispatch to appropriate agent.
    # For now: log and return a stub result.
    # In a real run we'd update documents.status = 'extracting' first,
    # then 'extracted' or 'failed' after the agent completes.

    return {
        "status": "stub",
        "document_id": document_id,
        "message": "Extraction not yet implemented — see Week 3",
    }
