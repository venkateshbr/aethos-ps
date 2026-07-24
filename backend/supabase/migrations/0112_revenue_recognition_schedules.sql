-- =============================================================================
-- Migration 0112: Durable revenue-recognition schedules (#408).
--
-- Stores a per-source deferred-revenue release schedule so the
-- revenue_recognition_agent can release *historical* deferred balances on a
-- durable straight-line plan (not just the current period's net credits). The
-- agent reads active schedules at close and DRAFTS the period's release journal
-- (DR deferred / CR revenue) via HITL; recognized_to_date advances only when the
-- suggestion is approved and posted. See ADR 0004.
-- =============================================================================

BEGIN;

CREATE TABLE revenue_recognition_schedules (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    source_type        TEXT NOT NULL,          -- 'invoice' | 'engagement' | 'manual'
    source_id          UUID,                   -- optional link to the originating row
    method             TEXT NOT NULL DEFAULT 'straight_line',
    currency           TEXT NOT NULL,
    base_currency      TEXT NOT NULL,
    start_period       TEXT NOT NULL,          -- 'YYYY-MM'
    end_period         TEXT NOT NULL,          -- 'YYYY-MM'
    periods            INTEGER NOT NULL,       -- number of monthly periods
    total_amount       NUMERIC(15,2) NOT NULL,
    base_total_amount  NUMERIC(15,2) NOT NULL,
    recognized_to_date NUMERIC(15,2) NOT NULL DEFAULT 0,
    deferred_account_code TEXT NOT NULL DEFAULT '2200',
    revenue_account_code  TEXT NOT NULL DEFAULT '4000',
    status             TEXT NOT NULL DEFAULT 'active',  -- active | completed | cancelled
    description        TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_revrec_method CHECK (method IN ('straight_line')),
    CONSTRAINT ck_revrec_status CHECK (status IN ('active', 'completed', 'cancelled')),
    CONSTRAINT ck_revrec_periods CHECK (periods >= 1),
    CONSTRAINT ck_revrec_period_fmt CHECK (
        start_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
        AND end_period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
    ),
    CONSTRAINT ck_revrec_total_nonneg CHECK (total_amount >= 0),
    CONSTRAINT ck_revrec_recognized_bounds CHECK (
        recognized_to_date >= 0 AND recognized_to_date <= total_amount
    )
);

ALTER TABLE revenue_recognition_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON revenue_recognition_schedules
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY "authenticated_member_read" ON revenue_recognition_schedules
    FOR SELECT TO authenticated
    USING (public.is_tenant_member(auth.uid(), tenant_id));

CREATE TRIGGER set_updated_at BEFORE UPDATE ON revenue_recognition_schedules
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_revrec_schedules_active
    ON revenue_recognition_schedules (tenant_id, status, start_period);

COMMENT ON TABLE revenue_recognition_schedules IS
    'Durable straight-line deferred-revenue release schedules read by the '
    'revenue_recognition_agent to draft period releases (#408).';

COMMIT;
