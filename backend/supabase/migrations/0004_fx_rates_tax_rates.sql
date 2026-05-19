-- =============================================================================
-- Migration 0004: FX Rates and Tax Rates
-- =============================================================================
-- fx_rates   — global table (no tenant_id); unique per currency pair + date.
-- tax_rates  — nullable tenant_id: NULL = system-seeded rate visible to all;
--              non-NULL = tenant override / custom rate.
-- Seed data lives in seed.sql (run separately).
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- fx_rates  (global — no RLS needed; no PII)
-- ---------------------------------------------------------------------------
CREATE TABLE fx_rates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency   CHAR(3) NOT NULL,
    to_currency     CHAR(3) NOT NULL,
    -- 6dp for FX precision (e.g. USDINR 83.123456)
    rate            NUMERIC(15,6) NOT NULL,
    source          TEXT NOT NULL DEFAULT 'manual',
    rate_date       DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (from_currency, to_currency, rate_date),
    CONSTRAINT ck_fx_rates_positive CHECK (rate > 0),
    CONSTRAINT ck_fx_rates_different_currencies CHECK (from_currency <> to_currency)
);

CREATE INDEX idx_fx_rates_pair_date ON fx_rates(from_currency, to_currency, rate_date DESC);
CREATE INDEX idx_fx_rates_date      ON fx_rates(rate_date DESC);

-- Add FK from journal_lines.fx_rate_id now that fx_rates exists
ALTER TABLE journal_lines
    ADD CONSTRAINT fk_journal_lines_fx_rate
    FOREIGN KEY (fx_rate_id) REFERENCES fx_rates(id);

-- ---------------------------------------------------------------------------
-- tax_rates
-- ---------------------------------------------------------------------------
CREATE TABLE tax_rates (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = system-seeded (visible to all tenants as a starting point)
    tenant_id               UUID REFERENCES tenants(id) ON DELETE CASCADE,
    country                 CHAR(2),
    -- Short code, e.g. "VAT-20", "GST-9", "GST-IN-18"
    code                    TEXT NOT NULL,
    name                    TEXT NOT NULL,
    -- Stored as fraction: 0.2000 = 20%, 0.0900 = 9%
    rate                    NUMERIC(5,4) NOT NULL,
    is_default              BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_seeded               BOOLEAN NOT NULL DEFAULT FALSE,
    -- Optional: which GL account this tax posts to (e.g. 2300 Sales Tax Payable)
    accounting_account_id   UUID REFERENCES accounts(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,
    CONSTRAINT ck_tax_rates_positive CHECK (rate >= 0),
    CONSTRAINT ck_tax_rates_max CHECK (rate <= 1)
);

-- RLS: system rows (tenant_id IS NULL) are readable by everyone;
--      tenant rows only by their tenant.
ALTER TABLE tax_rates ENABLE ROW LEVEL SECURITY;

-- Allow reading system-seeded rates (tenant_id IS NULL) for all authenticated users
CREATE POLICY "system_rates_readable" ON tax_rates
    FOR SELECT
    USING (tenant_id IS NULL);

-- Tenant-scoped rates visible only to that tenant
CREATE POLICY "tenant_rates_isolation" ON tax_rates
    FOR ALL
    USING (
        tenant_id IS NOT NULL
        AND tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tax_rates
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX idx_tax_rates_tenant_id ON tax_rates(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_rates_country   ON tax_rates(country, is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_tax_rates_system    ON tax_rates(country) WHERE tenant_id IS NULL AND deleted_at IS NULL;

COMMIT;
