-- =============================================================================
-- Migration 0094: Tenant AI inference settings
--
-- Tenant-scoped configuration for Aethos Atlas runtime and OpenRouter model
-- routing. The default chain is:
--   google/gemma-4-31b-it:free -> openrouter/free -> anthropic/claude-haiku-4.5
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS tenant_ai_settings (
    tenant_id           UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    atlas_runtime       TEXT NOT NULL DEFAULT 'hermes_agent',
    provider            TEXT NOT NULL DEFAULT 'openrouter',
    primary_model       TEXT NOT NULL DEFAULT 'google/gemma-4-31b-it:free',
    use_free_router     BOOLEAN NOT NULL DEFAULT TRUE,
    fallback_model      TEXT NOT NULL DEFAULT 'anthropic/claude-haiku-4.5',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_tenant_ai_settings_runtime CHECK (
        atlas_runtime IN ('aethos_basic', 'hermes_agent')
    ),
    CONSTRAINT ck_tenant_ai_settings_provider CHECK (
        provider = 'openrouter'
    ),
    CONSTRAINT ck_tenant_ai_settings_primary_model CHECK (
        primary_model IN (
            'google/gemma-4-31b-it:free',
            'openrouter/free',
            'anthropic/claude-haiku-4.5'
        )
    ),
    CONSTRAINT ck_tenant_ai_settings_fallback_model CHECK (
        fallback_model IN (
            'anthropic/claude-haiku-4.5',
            'openrouter/free',
            'google/gemma-4-31b-it:free'
        )
    )
);

ALTER TABLE tenant_ai_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "tenant_isolation" ON tenant_ai_settings;
CREATE POLICY "tenant_isolation" ON tenant_ai_settings
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

DROP POLICY IF EXISTS "authenticated_member_read" ON tenant_ai_settings;
CREATE POLICY "authenticated_member_read" ON tenant_ai_settings
    FOR SELECT
    TO authenticated
    USING (
        public.is_tenant_member(auth.uid(), tenant_id)
    );

CREATE TRIGGER set_updated_at BEFORE UPDATE ON tenant_ai_settings
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

COMMENT ON TABLE tenant_ai_settings IS
    'Tenant-level Aethos Atlas runtime and OpenRouter model routing settings.';
COMMENT ON COLUMN tenant_ai_settings.primary_model IS
    'Preferred OpenRouter model ID for tenant AI inference.';
COMMENT ON COLUMN tenant_ai_settings.use_free_router IS
    'When true, insert openrouter/free between primary and paid fallback.';
COMMENT ON COLUMN tenant_ai_settings.fallback_model IS
    'Paid or stable fallback model used when free models are unavailable.';

COMMIT;
