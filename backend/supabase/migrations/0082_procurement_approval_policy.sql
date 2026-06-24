-- =============================================================================
-- Migration 0082: Procurement Approval Policy Snapshot
-- =============================================================================
-- Stores the deterministic approval route used when purchase requests/orders
-- are created. This keeps approval decisions auditable without requiring a
-- full org-chart workflow engine for launch.
-- =============================================================================

BEGIN;

ALTER TABLE procurement_documents
    ADD COLUMN IF NOT EXISTS cost_center_code TEXT,
    ADD COLUMN IF NOT EXISTS approval_required_role TEXT NOT NULL DEFAULT 'manager',
    ADD COLUMN IF NOT EXISTS approval_policy_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS approval_route JSONB NOT NULL DEFAULT '[]'::JSONB;

ALTER TABLE procurement_documents
    DROP CONSTRAINT IF EXISTS ck_procurement_documents_approval_required_role;
ALTER TABLE procurement_documents
    ADD CONSTRAINT ck_procurement_documents_approval_required_role
    CHECK (approval_required_role IN ('manager', 'admin', 'owner'));

CREATE INDEX IF NOT EXISTS idx_procurement_documents_cost_center
    ON procurement_documents (tenant_id, cost_center_code)
    WHERE deleted_at IS NULL AND cost_center_code IS NOT NULL;

COMMIT;
