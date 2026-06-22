-- =============================================================================
-- Migration 0038: Client Groups
-- =============================================================================
-- Adds tenant-scoped client grouping for family offices, portfolios,
-- corporate groups, billing groups, and relationship rollups.
--
-- Clients remain the legal/billable counterparties. Groups are reporting and
-- relationship containers with explicit memberships.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS client_groups (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    group_type          TEXT NOT NULL DEFAULT 'other'
                        CHECK (group_type IN (
                            'family_office',
                            'portfolio',
                            'corporate_group',
                            'billing_group',
                            'client_relationship',
                            'other'
                        )),
    primary_client_id   UUID REFERENCES clients(id) ON DELETE SET NULL,
    billing_client_id   UUID REFERENCES clients(id) ON DELETE SET NULL,
    currency            CHAR(3),
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'archived')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

ALTER TABLE client_groups ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON client_groups;
CREATE POLICY tenant_isolation ON client_groups
    USING (tenant_id = (current_setting('app.current_tenant_id', TRUE))::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON client_groups
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE TABLE IF NOT EXISTS client_group_members (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    group_id            UUID NOT NULL REFERENCES client_groups(id) ON DELETE CASCADE,
    client_id           UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    relationship_role   TEXT NOT NULL DEFAULT 'other'
                        CHECK (relationship_role IN (
                            'parent',
                            'subsidiary',
                            'trust',
                            'spv',
                            'individual',
                            'portfolio_company',
                            'billing_entity',
                            'other'
                        )),
    is_primary          BOOLEAN NOT NULL DEFAULT FALSE,
    start_date          DATE,
    end_date            DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT ck_client_group_members_dates
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

ALTER TABLE client_group_members ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON client_group_members;
CREATE POLICY tenant_isolation ON client_group_members
    USING (tenant_id = (current_setting('app.current_tenant_id', TRUE))::UUID);

CREATE TRIGGER set_updated_at BEFORE UPDATE ON client_group_members
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

CREATE INDEX IF NOT EXISTS idx_client_groups_tenant_active
    ON client_groups(tenant_id, name)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_client_groups_primary_client
    ON client_groups(tenant_id, primary_client_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_client_groups_billing_client
    ON client_groups(tenant_id, billing_client_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_client_group_members_group
    ON client_group_members(tenant_id, group_id)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_client_group_members_client
    ON client_group_members(tenant_id, client_id)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_client_group_members_active_client
    ON client_group_members(tenant_id, group_id, client_id)
    WHERE deleted_at IS NULL;

COMMENT ON TABLE client_groups IS
    'Relationship/reporting containers for client rollups; clients remain legal counterparties.';
COMMENT ON TABLE client_group_members IS
    'Tenant-scoped memberships that connect clients to client groups with relationship roles.';

COMMIT;
