-- =============================================================================
-- Migration 0101: Atlas semantic intent router settings
--
-- Adds tenant-level controls for the Atlas response pipeline:
--   semantic_intent -> atlas_runtime by default.
-- The semantic stage may answer high-confidence finance intents through
-- deterministic Aethos tools/read-packs before falling back to Hermes/basic AI.
-- =============================================================================

BEGIN;

ALTER TABLE tenant_ai_settings
    ADD COLUMN IF NOT EXISTS semantic_router_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS semantic_router_min_confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.720,
    ADD COLUMN IF NOT EXISTS atlas_response_order TEXT[] NOT NULL DEFAULT ARRAY['semantic_intent', 'atlas_runtime']::TEXT[];

ALTER TABLE tenant_ai_settings
    DROP CONSTRAINT IF EXISTS ck_tenant_ai_settings_semantic_router_confidence;
ALTER TABLE tenant_ai_settings
    ADD CONSTRAINT ck_tenant_ai_settings_semantic_router_confidence CHECK (
        semantic_router_min_confidence >= 0.500
        AND semantic_router_min_confidence <= 0.980
    );

ALTER TABLE tenant_ai_settings
    DROP CONSTRAINT IF EXISTS ck_tenant_ai_settings_response_order;
ALTER TABLE tenant_ai_settings
    ADD CONSTRAINT ck_tenant_ai_settings_response_order CHECK (
        array_length(atlas_response_order, 1) BETWEEN 1 AND 2
        AND atlas_response_order <@ ARRAY['semantic_intent', 'atlas_runtime']::TEXT[]
        AND 'atlas_runtime' = ANY(atlas_response_order)
    );

COMMENT ON COLUMN tenant_ai_settings.semantic_router_enabled IS
    'When true, Atlas may route high-confidence operational intents through the semantic intent router before model inference.';
COMMENT ON COLUMN tenant_ai_settings.semantic_router_min_confidence IS
    'Minimum classifier confidence required before the semantic intent router can answer a turn.';
COMMENT ON COLUMN tenant_ai_settings.atlas_response_order IS
    'Ordered Atlas response stages. Default semantic_intent then atlas_runtime.';

COMMIT;
