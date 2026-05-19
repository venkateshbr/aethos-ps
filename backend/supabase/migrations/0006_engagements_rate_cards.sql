-- =============================================================================
-- Migration 0006: Engagements, Rate Cards, Billing Terms, Invoice Sequences
-- =============================================================================
-- Creates the commercial backbone of the PS ERP:
--   * billing_arrangement enum  — 6 billing models
--   * engagement_status enum
--   * rate_cards / rate_card_lines / rate_card_client_overrides
--   * engagements — contract with a client, tied to a billing arrangement
--   * engagement_billing_terms — billing-model-specific parameters
--   * invoice_number_sequences — per-tenant atomic sequence (UPDATE…RETURNING)
--
-- Money: NUMERIC(15,2) everywhere. All timestamps TIMESTAMPTZ.
-- Tenant isolation: RLS on every tenant-scoped table.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE billing_arrangement AS ENUM (
    'time_and_materials',
    'fixed_fee',
    'retainer',
    'retainer_draw',
    'milestone',
    'capped_tm'
);

CREATE TYPE engagement_status AS ENUM (
    'draft',
    'active',
    'on_hold',
    'completed',
    'cancelled'
);

-- ---------------------------------------------------------------------------
-- rate_cards
-- A named set of role → hourly rate entries for a tenant.
-- ---------------------------------------------------------------------------
CREATE TABLE rate_cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    currency        CHAR(3) NOT NULL DEFAULT 'USD',
    effective_date  DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

ALTER TABLE rate_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON rate_cards
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON rate_cards
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_rate_cards_tenant_id ON rate_cards(tenant_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- rate_card_lines
-- One row per role within a rate card.
-- ---------------------------------------------------------------------------
CREATE TABLE rate_card_lines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id    UUID NOT NULL REFERENCES rate_cards(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    rate            NUMERIC(15,2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rate_card_id, role),
    CONSTRAINT ck_rate_card_lines_rate_positive CHECK (rate >= 0)
);

ALTER TABLE rate_card_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON rate_card_lines
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_rate_card_lines_rate_card_id ON rate_card_lines(rate_card_id);
CREATE INDEX idx_rate_card_lines_tenant_id    ON rate_card_lines(tenant_id);

-- ---------------------------------------------------------------------------
-- rate_card_client_overrides
-- Per-client rate adjustments on top of a rate card.
-- ---------------------------------------------------------------------------
CREATE TABLE rate_card_client_overrides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rate_card_id    UUID NOT NULL REFERENCES rate_cards(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    rate            NUMERIC(15,2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_rcco_rate_positive CHECK (rate >= 0)
);

ALTER TABLE rate_card_client_overrides ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON rate_card_client_overrides
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE INDEX idx_rcco_rate_card_id ON rate_card_client_overrides(rate_card_id);
CREATE INDEX idx_rcco_tenant_id    ON rate_card_client_overrides(tenant_id);
CREATE INDEX idx_rcco_client_id    ON rate_card_client_overrides(tenant_id, client_id);

-- ---------------------------------------------------------------------------
-- engagements
-- Commercial container: one engagement per client contract.
-- ---------------------------------------------------------------------------
CREATE TABLE engagements (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    name                TEXT NOT NULL,
    billing_arrangement billing_arrangement NOT NULL,
    currency            CHAR(3) NOT NULL DEFAULT 'USD',
    total_value         NUMERIC(15,2),
    status              engagement_status NOT NULL DEFAULT 'draft',
    start_date          DATE,
    end_date            DATE,
    -- Optional: rate card applied to this engagement
    rate_card_id        UUID REFERENCES rate_cards(id) ON DELETE SET NULL,
    description         TEXT,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT ck_engagements_total_value CHECK (total_value IS NULL OR total_value >= 0),
    CONSTRAINT ck_engagements_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE engagements ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON engagements
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON engagements
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_engagements_tenant_status    ON engagements(tenant_id, status)    WHERE deleted_at IS NULL;
CREATE INDEX idx_engagements_tenant_client    ON engagements(tenant_id, client_id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- engagement_billing_terms
-- Billing-model-specific parameters stored separately (1:1 with engagement).
-- ---------------------------------------------------------------------------
CREATE TABLE engagement_billing_terms (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id               UUID NOT NULL UNIQUE REFERENCES engagements(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- fixed_fee / capped_tm
    fixed_fee_amount            NUMERIC(15,2),
    -- milestone totals (individual milestones tracked in milestones table in v1.1)
    milestone_total             NUMERIC(15,2),
    -- retainer / retainer_draw
    retainer_monthly_amount     NUMERIC(15,2),
    retainer_floor              NUMERIC(15,2),
    retainer_rollover           BOOLEAN NOT NULL DEFAULT FALSE,
    -- capped_tm
    cap_amount                  NUMERIC(15,2),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ebt_fixed_fee_pos    CHECK (fixed_fee_amount    IS NULL OR fixed_fee_amount    >= 0),
    CONSTRAINT ck_ebt_milestone_pos    CHECK (milestone_total      IS NULL OR milestone_total      >= 0),
    CONSTRAINT ck_ebt_retainer_pos     CHECK (retainer_monthly_amount IS NULL OR retainer_monthly_amount >= 0),
    CONSTRAINT ck_ebt_floor_pos        CHECK (retainer_floor       IS NULL OR retainer_floor       >= 0),
    CONSTRAINT ck_ebt_cap_pos          CHECK (cap_amount           IS NULL OR cap_amount           >= 0)
);

ALTER TABLE engagement_billing_terms ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON engagement_billing_terms
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON engagement_billing_terms
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_ebt_tenant_id ON engagement_billing_terms(tenant_id);

-- ---------------------------------------------------------------------------
-- invoice_number_sequences
-- Per-tenant counter. Service layer issues:
--   INSERT … ON CONFLICT DO NOTHING  (ensure row exists)
--   UPDATE … SET last_number = last_number + 1 … RETURNING last_number
-- Formats: 'INV-' || LPAD(last_number::text, 4, '0')
-- ---------------------------------------------------------------------------
CREATE TABLE invoice_number_sequences (
    tenant_id   UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    last_number INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT ck_inv_seq_non_negative CHECK (last_number >= 0)
);

-- RLS: each tenant can only see/update their own sequence row.
ALTER TABLE invoice_number_sequences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON invoice_number_sequences
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

COMMIT;
