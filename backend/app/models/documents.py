"""Pydantic request/response schemas for the documents API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response returned after a successful document upload or lookup."""

    id: str = Field(..., description="UUID of the documents row")
    tenant_id: str = Field(..., description="Owning tenant UUID")
    original_filename: str | None = Field(
        default=None,
        description="Original filename as uploaded",
    )
    document_type: str = Field(
        default="vendor_invoice",
        description="Classified type: engagement_letter | expense | vendor_invoice",
    )
    storage_path: str = Field(..., description="Path within the Supabase Storage bucket")
    mime_type: str = Field(..., description="MIME type of the uploaded file")
    file_size_bytes: int = Field(..., ge=0, description="Raw file size in bytes")
    sha256: str = Field(..., description="Hex-encoded SHA-256 digest of the file content")
    status: str = Field(
        ...,
        description="Extraction status: uploaded | extracting | extracted | failed",
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class DocumentSummary(BaseModel):
    """One row in the tenant's document inventory (GET /documents)."""

    id: str = Field(..., description="UUID of the documents row")
    filename: str = Field(..., description="Original filename as uploaded")
    mime_type: str = Field(..., description="MIME type of the uploaded file")
    document_type: str = Field(
        default="vendor_invoice",
        description="Classified type: engagement_letter | expense | vendor_invoice",
    )
    status: str = Field(
        ...,
        description="Extraction status: uploaded | extracting | extracted | failed",
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
