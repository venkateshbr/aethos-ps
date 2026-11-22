-- Dedicated Telegram adapter state. No grants or policies for end-user roles.
BEGIN;

CREATE TABLE public.telegram_erp_links (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    membership_id uuid NOT NULL REFERENCES public.tenant_users(id) ON DELETE CASCADE,
    sender_id bigint NOT NULL CHECK (sender_id BETWEEN 1 AND 4503599627370495),
    challenge_hash text UNIQUE,
    linked_at timestamptz,
    expires_at timestamptz NOT NULL,
    UNIQUE (tenant_id, user_id),
    CHECK ((linked_at IS NULL) = (challenge_hash IS NOT NULL))
);
-- Unproved claims never reserve somebody else's Telegram identity.
CREATE UNIQUE INDEX telegram_erp_one_link_per_sender
    ON public.telegram_erp_links(sender_id) WHERE linked_at IS NOT NULL;

CREATE TABLE public.telegram_erp_deliveries (
    -- One dedicated bot per database; Telegram update IDs are bot-wide.
    update_id bigint PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id uuid NOT NULL,
    link_id uuid NOT NULL, -- keep audit history after unlink
    command text NOT NULL CHECK (command IN ('ar', 'draft', 'confirm', 'unlink')),
    outcome text NOT NULL DEFAULT 'claimed',
    created_at timestamptz NOT NULL DEFAULT now(),
    confirmation_hash text UNIQUE,
    confirmation_expires_at timestamptz,
    arguments jsonb,
    suggestion_id uuid
);
CREATE INDEX telegram_erp_deliveries_tenant_created
    ON public.telegram_erp_deliveries(tenant_id, created_at);

ALTER TABLE public.telegram_erp_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.telegram_erp_deliveries ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.telegram_erp_links, public.telegram_erp_deliveries
    FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.telegram_erp_links, public.telegram_erp_deliveries
    TO service_role;

COMMIT;
