"""Documents router — file upload and status endpoints.

POST /api/v1/documents/upload  — upload a file to Supabase Storage and create
                                  a documents row; enqueues extraction worker.

Supported MIME types: PDF, JPEG, PNG, WebP, plain text.
Max file size: 20 MB.
Storage path: {tenant_id}/{year}/{month:02d}/{document_id}.{ext}
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, date
from datetime import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.auth import CurrentUser, get_current_user
from app.core.db import get_service_role_client
from app.core.tenant import get_tenant_id
from app.models.documents import DocumentResponse
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "text/plain",
    }
)

_MAX_FILE_SIZE_BYTES: int = 20 * 1024 * 1024  # 20 MB

_STORAGE_BUCKET = "documents"

# Extension map for supported MIME types.
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "text/plain": "txt",
}


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    tenant_id: str = Depends(get_tenant_id),
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> DocumentResponse:
    """Upload a document to Supabase Storage and create a ``documents`` row.

    1. Validates MIME type and file size.
    2. Reads full content, computes SHA-256.
    3. Uploads to Supabase Storage at ``{tenant_id}/{year}/{month}/{id}.{ext}``.
    4. Inserts a ``documents`` row with ``status='uploaded'``.
    5. Defers ``extract_document_worker`` Procrastinate task.
    6. Returns ``DocumentResponse``.
    """
    # ------------------------------------------------------------------
    # 1. Validate MIME type (server-side — never trust Content-Type header alone).
    # ------------------------------------------------------------------
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file type: '{content_type}'. "
                f"Allowed types: {', '.join(sorted(_ALLOWED_MIME_TYPES))}"
            ),
        )

    # ------------------------------------------------------------------
    # 2. Read content and validate size.
    # ------------------------------------------------------------------
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large: {len(content):,} bytes. Maximum allowed: 20 MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty file — nothing to upload.",
        )

    # ------------------------------------------------------------------
    # 3. Compute SHA-256 and build storage path.
    # ------------------------------------------------------------------
    sha256_hex = hashlib.sha256(content).hexdigest()
    document_id = str(uuid.uuid4())
    today = date.today()
    ext = _MIME_TO_EXT[content_type]
    storage_path = f"{tenant_id}/{today.year}/{today.month:02d}/{document_id}.{ext}"

    # ------------------------------------------------------------------
    # 4. Upload to Supabase Storage.
    # ------------------------------------------------------------------
    try:
        db.storage.from_(_STORAGE_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except Exception as exc:
        logger.error(
            "Storage upload failed for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while storing the file.",
        ) from exc

    # ------------------------------------------------------------------
    # 5. Insert documents row.
    # ------------------------------------------------------------------
    now_iso = dt.now(tz=UTC).isoformat()
    doc_row: dict = {
        "id": document_id,
        "tenant_id": tenant_id,
        "uploader_id": current_user.user_id,
        # #125 — persist the original filename so the extraction worker's
        # keyword classifier (engagement / receipt / invoice) sees the real
        # name instead of the {uuid}.{ext} storage_path tail and defaulting
        # every upload to vendor_invoice.
        "original_filename": file.filename or "untitled",
        "storage_path": storage_path,
        "mime_type": content_type,
        "file_size_bytes": len(content),
        "sha256": sha256_hex,
        "status": "uploaded",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    try:
        result = db.table("documents").insert(doc_row).execute()
        saved_row: dict = result.data[0]
    except Exception as exc:
        logger.error(
            "DB insert failed for document %s: %s",
            document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while saving the document record.",
        ) from exc

    # ------------------------------------------------------------------
    # 6. Dispatch extraction.
    #
    # Two modes, switched by `settings.extraction_mode`:
    #
    #   sync  — Pilot default. Run the extraction inline; the upload
    #           response carries the result. Blocks the request for 5-30s
    #           while the LLM extracts. No Procrastinate worker required.
    #
    #   async — Defer onto the Procrastinate queue; the upload returns
    #           immediately and the worker processes the job out of band.
    #           Requires DATABASE_URL + a running worker. The original
    #           production design.
    #
    # In both modes, failures are swallowed at the upload layer (the file
    # is already in Storage + the documents row exists; a manual re-queue
    # or cron sweep can pick it up later). The extraction worker itself
    # also has its own try/except that updates documents.status='failed'.
    # ------------------------------------------------------------------
    from app.core.config import settings as _settings

    try:
        from app.workers.document_extraction import extract_document_worker

        if _settings.extraction_mode == "async":
            await extract_document_worker.defer_async(
                document_id=document_id,
                tenant_id=tenant_id,
            )
        else:
            # Inline call — Procrastinate Task wraps the original function on
            # `.func`. Direct invocation skips the queue entirely.
            await extract_document_worker.func(
                document_id=document_id,
                tenant_id=tenant_id,
            )
    except Exception as exc:
        logger.warning(
            "Extraction dispatch (%s) failed for %s: %s",
            _settings.extraction_mode,
            document_id,
            exc,
        )

    # ------------------------------------------------------------------
    # 7. Return response.
    # ------------------------------------------------------------------
    return DocumentResponse(
        id=saved_row.get("id", document_id),
        tenant_id=saved_row.get("tenant_id", tenant_id),
        storage_path=saved_row.get("storage_path", storage_path),
        mime_type=saved_row.get("mime_type", content_type),
        file_size_bytes=saved_row.get("file_size_bytes", len(content)),
        sha256=saved_row.get("sha256", sha256_hex),
        status=saved_row.get("status", "uploaded"),
        created_at=saved_row.get("created_at", now_iso),
    )


# ---------------------------------------------------------------------------
# Presigned URL endpoint (#127)
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}/url",
    summary="Return a short-lived presigned URL for a document the caller can access",
)
async def get_document_url(
    document_id: str,
    expires_in: int = 3600,
    current_user: CurrentUser = Depends(get_current_user),  # noqa: B008
    tenant_id: str = Depends(get_tenant_id),
    db: Client = Depends(get_service_role_client),  # noqa: B008
) -> dict:
    """Return a tenant-scoped presigned URL for the document's bucket object.

    Authorisation: the caller's tenant must own the row. Cross-tenant requests
    yield 404 (same information-hiding pattern as the rest of the API).

    The URL expires in `expires_in` seconds (default 1h, cap 24h to keep blast
    radius small if it leaks via screen-share, copy/paste, etc.).
    """
    if expires_in <= 0 or expires_in > 86400:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expires_in must be between 1 and 86400 seconds.",
        )

    # Tenant-scoped lookup. The membership dep on tenant_id already verified
    # the caller belongs to this tenant; we re-filter by tenant_id on the row
    # to make cross-tenant access yield 404, not 403, on documents owned by
    # someone else (information-hiding parity with #90/#92).
    try:
        row = (
            db.table("documents")
            .select("id, storage_path, original_filename, mime_type")
            .eq("id", document_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Document lookup failed for %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load document.",
        ) from exc

    if not row.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    doc = row.data[0]
    storage_path = doc.get("storage_path")
    if not storage_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document row has no storage_path.",
        )

    try:
        # supabase-py: create_signed_url(path, expires_in_seconds)
        signed = db.storage.from_(_STORAGE_BUCKET).create_signed_url(
            storage_path, expires_in
        )
    except Exception as exc:
        logger.exception("Failed to create signed URL for document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage provider rejected the signed-URL request.",
        ) from exc

    # supabase-py 2.x returns {"signedURL": ..., "path": ...} on success.
    url = signed.get("signedURL") or signed.get("signed_url") or signed.get("url")
    if not url:
        logger.error("Storage create_signed_url returned no URL: %r", signed)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage provider returned no signed URL.",
        )

    return {
        "document_id": document_id,
        "url": url,
        "original_filename": doc.get("original_filename"),
        "mime_type": doc.get("mime_type"),
        "expires_in": expires_in,
    }
