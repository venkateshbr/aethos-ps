-- =============================================================================
-- Migration 0032: Engagement Financial Summary — supporting indexes
-- =============================================================================
-- Adds indexes to accelerate the GET /api/v1/engagements/{id}/summary endpoint.
--
-- The summary aggregates:
--   * invoices      — billed_to_date (sum of totals for non-voided invoices)
--   * time_entries  — WIP hours and WIP value (unbilled billable hours)
--
-- No schema changes to the engagements table itself.
-- The service_line / practice_area column is a separate, properly-designed
-- implementation (Products & Services catalogue — tracked separately).
-- =============================================================================

BEGIN;

-- Speeds up the invoice aggregate: total billed per engagement, excluding voided.
-- Partial index — only non-deleted, non-voided invoices participate in billing math.
CREATE INDEX IF NOT EXISTS idx_invoices_engagement_summary
    ON invoices(tenant_id, engagement_id)
    WHERE deleted_at IS NULL AND status <> 'voided';

-- Speeds up counting invoices and finding last_invoice_date per engagement.
-- Reuses the same partial predicate as above.
-- (idx_invoices_engagement_summary covers the same predicate; the index name
--  clearly signals its summary use-case so query plans are self-documenting.)

-- Speeds up the WIP time-entry aggregate:
-- unbilled, billable hours on projects that belong to an engagement.
-- projects.engagement_id is already indexed (idx_projects_tenant_engagement),
-- and time_entries.project_id is a FK, but there is no composite index for
-- the billing-status filter on time_entries across project_id + billing_status.
CREATE INDEX IF NOT EXISTS idx_te_project_billing_summary
    ON time_entries(tenant_id, project_id, billing_status)
    WHERE deleted_at IS NULL AND billable = TRUE;

COMMIT;
