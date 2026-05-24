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
    # 6. Defer the Procrastinate extraction task.
    # Degrade gracefully if the queue connector is unavailable (unit-test /
    # dev environments may not have DATABASE_URL configured for the queue).
    # ------------------------------------------------------------------
    try:
        from app.workers.document_extraction import extract_document_worker

        await extract_document_worker.defer_async(
            document_id=document_id,
            tenant_id=tenant_id,
        )
    except Exception as exc:
        # Extraction is async and non-blocking — log the failure but don't
        # roll back the upload. The document is safe in storage; a manual
        # re-queue or cron sweep can pick it up later.
        logger.warning(
            "Failed to defer extract_document_worker for %s: %s",
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
