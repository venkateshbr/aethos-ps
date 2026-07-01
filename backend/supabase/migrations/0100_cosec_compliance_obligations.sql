-- Migration 0100: COSEC compliance obligation calendar
--
-- Company-secretarial teams need an entity-level filing calendar, separate
-- from generic project work. This table stores obligation dates, evidence,
-- reminder/approval state, and billing impact for Atlas read packs and future
-- workflow automation.

BEGIN;

CREATE TABLE IF NOT EXISTS cosec_compliance_obligations (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id            UUID REFERENCES clients(id) ON DELETE SET NULL,
    engagement_id        UUID REFERENCES engagements(id) ON DELETE SET NULL,
    project_id           UUID REFERENCES projects(id) ON DELETE SET NULL,
    entity_name          TEXT NOT NULL,
    obligation_type      TEXT NOT NULL,
    filing_reference     TEXT,
    due_date             DATE NOT NULL,
    status               TEXT NOT NULL DEFAULT 'open',
    reminder_status      TEXT NOT NULL DEFAULT 'not_drafted',
    approval_status      TEXT NOT NULL DEFAULT 'not_required',
    evidence_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    missing_evidence     TEXT[] NOT NULL DEFAULT '{}',
    billing_impact       TEXT NOT NULL DEFAULT '',
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at           TIMESTAMPTZ,
    CONSTRAINT ck_cosec_obligations_status
        CHECK (status IN ('open', 'in_progress', 'filed', 'waived', 'blocked')),
    CONSTRAINT ck_cosec_obligations_reminder_status
        CHECK (reminder_status IN ('not_drafted', 'drafted', 'sent', 'blocked')),
    CONSTRAINT ck_cosec_obligations_approval_status
        CHECK (approval_status IN ('not_required', 'requires_inbox_approval', 'approved', 'rejected'))
);

ALTER TABLE cosec_compliance_obligations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "tenant_isolation" ON cosec_compliance_obligations;
CREATE POLICY "tenant_isolation" ON cosec_compliance_obligations
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON cosec_compliance_obligations;
CREATE POLICY "authenticated_member_read" ON cosec_compliance_obligations
    FOR SELECT TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON cosec_compliance_obligations
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_cosec_obligations_tenant_due
    ON cosec_compliance_obligations (tenant_id, due_date)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cosec_obligations_tenant_client
    ON cosec_compliance_obligations (tenant_id, client_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cosec_obligations_tenant_project
    ON cosec_compliance_obligations (tenant_id, project_id)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE cosec_compliance_obligations IS
    'Entity-level company-secretarial obligation calendar used for filing reminders, evidence, approvals, and billing impact.';

COMMIT;
