-- =============================================================================
-- Migration 0104: Rebrand the AI agent display name from "Atlas" to "Nous"
-- =============================================================================
-- The AI agent is now presented to users as "Aethos Nous". This migration
-- updates only user-visible text stored in the database: the AI privilege
-- labels/descriptions shown in Settings -> Security Roles. Privilege *codes*
-- (atlas.chat, atlas.tools.*) are stable technical identifiers referenced by
-- application policy and are intentionally left unchanged. No behavior changes.
-- Idempotent: re-running only rewrites the same target strings.
-- =============================================================================

BEGIN;

UPDATE security_privileges
SET label = REPLACE(label, 'Atlas', 'Nous'),
    description = REPLACE(description, 'Atlas', 'Nous')
WHERE code IN (
    'atlas.chat',
    'atlas.tools.read',
    'atlas.tools.execute_draft',
    'atlas.tools.execute_money_in',
    'atlas.tools.execute_money_out'
)
AND (label LIKE '%Atlas%' OR description LIKE '%Atlas%');

COMMIT;
