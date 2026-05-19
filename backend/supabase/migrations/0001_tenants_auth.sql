-- =============================================================================
-- Migration 0001: Tenants, Auth, Employees, Clients
-- =============================================================================
-- Creates the core tenancy + people tables.  All tables:
--   * use TIMESTAMPTZ (UTC)
--   * have tenant_id (except tenants itself)
--   * soft-delete via deleted_at
--   * Row Level Security enabled + tenant isolation policy
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM ('owner', 'admin', 'manager', 'member', 'viewer');
CREATE TYPE client_kind AS ENUM ('customer', 'vendor', 'both');
CREATE TYPE employment_type AS ENUM ('full_time', 'part_time', 'contractor', 'consultant');
CREATE TYPE stripe_connect_status AS ENUM ('not_connected', 'pending', 'active', 'restricted', 'deauthorized');

-- ---------------------------------------------------------------------------
-- tenants
-- ---------------------------------------------------------------------------
CREATE TABLE tenants (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                        TEXT NOT NULL,
    slug                        TEXT NOT NULL UNIQUE,
    country                     CHAR(2) NOT NULL,
    base_currency               CHAR(3) NOT NULL DEFAULT 'USD',
    timezone                    TEXT NOT NULL DEFAULT 'UTC',
    locale                      TEXT NOT NULL DEFAULT 'en-US',
    -- SaaS billing
    stripe_customer_id          TEXT,
    stripe_subscription_id      TEXT,
    stripe_subscription_status  TEXT,
    -- Stripe Connect (per-tenant payout account)
    stripe_connect_account_id   TEXT,
    stripe_connect_status       stripe_connect_status NOT NULL DEFAULT 'not_connected',
    stripe_connect_charges_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_connect_payouts_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    billing_portal_url          TEXT,
    -- Subscription metadata
    plan_tier                   TEXT NOT NULL DEFAULT 'trial',
    trial_ends_at               TIMESTAMPTZ,
    brand_name                  TEXT,
    brand_logo_url              TEXT,
    status                      TEXT NOT NULL DEFAULT 'active',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- tenant_users
-- ---------------------------------------------------------------------------
CREATE TABLE tenant_users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- References auth.users (Supabase Auth) — no FK constraint across schemas
    user_id     UUID NOT NULL,
    role        user_role NOT NULL DEFAULT 'member',
    invited_at  TIMESTAMPTZ,
    joined_at   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ,
    UNIQUE (tenant_id, user_id)
);

ALTER TABLE tenant_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON tenant_users
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- ---------------------------------------------------------------------------
-- employees
-- ---------------------------------------------------------------------------
CREATE TABLE employees (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    -- Optional link to a Supabase Auth user
    user_id                 UUID,
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    email                   TEXT NOT NULL,
    title                   TEXT,
    department              TEXT,
    employment_type         employment_type NOT NULL DEFAULT 'full_time',
    -- Billing / cost rates
    default_bill_rate       NUMERIC(15,2),
    default_bill_rate_currency  CHAR(3),
    cost_rate               NUMERIC(15,2),
    available_hours_per_week  NUMERIC(6,2),
    manager_id              UUID REFERENCES employees(id),
    skills                  JSONB DEFAULT '[]'::JSONB,
    -- For autonomy promoter link back to tenant_users
    tenant_user_id          UUID REFERENCES tenant_users(id),
    status                  TEXT NOT NULL DEFAULT 'active',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON employees
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- ---------------------------------------------------------------------------
-- clients  (customers AND vendors share this table, kind discriminator)
-- ---------------------------------------------------------------------------
CREATE TABLE clients (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,
    legal_name              TEXT,
    kind                    client_kind NOT NULL DEFAULT 'customer',
    currency                CHAR(3),
    billing_email           TEXT,
    billing_address         JSONB DEFAULT '{}'::JSONB,
    tax_id                  TEXT,
    payment_terms_days      INTEGER NOT NULL DEFAULT 30,
    primary_contact         JSONB DEFAULT '{}'::JSONB,
    contacts                JSONB DEFAULT '[]'::JSONB,
    -- Stripe: customer-side Connect (for payment links routed to tenant's Connect account)
    stripe_customer_id      TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ
);

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_isolation" ON clients
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

-- ---------------------------------------------------------------------------
-- updated_at auto-refresh trigger (shared helper)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_users
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON employees
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX idx_tenant_users_tenant_id  ON tenant_users(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tenant_users_user_id    ON tenant_users(user_id)   WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_tenant_id     ON employees(tenant_id)    WHERE deleted_at IS NULL;
CREATE INDEX idx_employees_user_id       ON employees(user_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_clients_tenant_id       ON clients(tenant_id)      WHERE deleted_at IS NULL;
CREATE INDEX idx_clients_kind            ON clients(tenant_id, kind) WHERE deleted_at IS NULL;

COMMIT;
