-- Canonical expired-trial access state and audited operator overrides (#481).

BEGIN;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS stripe_subscription_reconciled_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS billing_access_override_until TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS billing_access_override_reason TEXT,
    ADD COLUMN IF NOT EXISTS billing_access_override_by TEXT,
    ADD COLUMN IF NOT EXISTS billing_access_override_granted_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_tenants_billing_override_metadata'
          AND conrelid = 'public.tenants'::regclass
    ) THEN
        ALTER TABLE public.tenants
            ADD CONSTRAINT ck_tenants_billing_override_metadata CHECK (
                billing_access_override_until IS NULL OR (
                    length(btrim(billing_access_override_reason)) >= 8
                    AND length(btrim(billing_access_override_by)) >= 3
                    AND billing_access_override_granted_at IS NOT NULL
                )
            );
    END IF;
END;
$$;

CREATE TABLE IF NOT EXISTS public.billing_access_override_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('granted', 'revoked')),
    effective_until TIMESTAMPTZ,
    reason TEXT NOT NULL CHECK (length(btrim(reason)) >= 8),
    actor TEXT NOT NULL CHECK (length(btrim(actor)) >= 3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.billing_access_override_events ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_billing_access_override_events_tenant_created
    ON public.billing_access_override_events (tenant_id, created_at DESC);

CREATE OR REPLACE VIEW public.tenant_billing_access
WITH (security_invoker = true)
AS
SELECT
    t.id AS tenant_id,
    t.stripe_subscription_status AS provider_status,
    t.trial_ends_at,
    t.stripe_subscription_reconciled_at,
    t.billing_access_override_until AS override_until,
    CASE
        WHEN t.billing_access_override_until > now() THEN 'override_active'
        WHEN t.stripe_subscription_status = 'trialing'
             AND t.trial_ends_at IS NOT NULL
             AND now() > t.trial_ends_at + interval '24 hours' THEN 'trial_expired'
        WHEN t.stripe_subscription_status = 'trialing'
             AND t.trial_ends_at IS NOT NULL
             AND now() > t.trial_ends_at THEN 'grace_period'
        WHEN t.stripe_subscription_status IN ('active', 'trialing')
            THEN t.stripe_subscription_status
        WHEN t.stripe_subscription_status IS NULL THEN 'unknown'
        ELSE t.stripe_subscription_status
    END AS effective_status,
    CASE
        WHEN t.billing_access_override_until > now() THEN 'full'
        WHEN t.stripe_subscription_status = 'active' THEN 'full'
        WHEN t.stripe_subscription_status = 'trialing'
             AND (t.trial_ends_at IS NULL OR now() <= t.trial_ends_at + interval '24 hours')
            THEN 'full'
        ELSE 'read_only'
    END AS access_mode
FROM public.tenants t;

CREATE OR REPLACE FUNCTION public.grant_billing_access_override(
    p_tenant_id UUID,
    p_tenant_name TEXT,
    p_until TIMESTAMPTZ,
    p_reason TEXT,
    p_actor TEXT
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_name TEXT;
    v_event_id UUID;
BEGIN
    SELECT name INTO v_name FROM public.tenants WHERE id = p_tenant_id FOR UPDATE;
    IF v_name IS NULL OR v_name <> p_tenant_name THEN
        RAISE EXCEPTION 'tenant id/name guard failed';
    END IF;
    IF p_until <= now() OR p_until > now() + interval '180 days' THEN
        RAISE EXCEPTION 'override must end within 180 days';
    END IF;
    IF length(btrim(p_reason)) < 8 OR length(btrim(p_actor)) < 3 THEN
        RAISE EXCEPTION 'reason or actor is too short';
    END IF;

    UPDATE public.tenants
    SET billing_access_override_until = p_until,
        billing_access_override_reason = btrim(p_reason),
        billing_access_override_by = btrim(p_actor),
        billing_access_override_granted_at = now(),
        updated_at = now()
    WHERE id = p_tenant_id;

    INSERT INTO public.billing_access_override_events (
        tenant_id, event_type, effective_until, reason, actor
    ) VALUES (
        p_tenant_id, 'granted', p_until, btrim(p_reason), btrim(p_actor)
    ) RETURNING id INTO v_event_id;
    RETURN v_event_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.revoke_billing_access_override(
    p_tenant_id UUID,
    p_tenant_name TEXT,
    p_reason TEXT,
    p_actor TEXT
) RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_name TEXT;
    v_previous_until TIMESTAMPTZ;
    v_event_id UUID;
BEGIN
    SELECT name, billing_access_override_until
    INTO v_name, v_previous_until
    FROM public.tenants WHERE id = p_tenant_id FOR UPDATE;
    IF v_name IS NULL OR v_name <> p_tenant_name THEN
        RAISE EXCEPTION 'tenant id/name guard failed';
    END IF;
    IF length(btrim(p_reason)) < 8 OR length(btrim(p_actor)) < 3 THEN
        RAISE EXCEPTION 'reason or actor is too short';
    END IF;

    UPDATE public.tenants
    SET billing_access_override_until = NULL,
        billing_access_override_reason = NULL,
        billing_access_override_by = NULL,
        billing_access_override_granted_at = NULL,
        updated_at = now()
    WHERE id = p_tenant_id;

    INSERT INTO public.billing_access_override_events (
        tenant_id, event_type, effective_until, reason, actor
    ) VALUES (
        p_tenant_id, 'revoked', v_previous_until, btrim(p_reason), btrim(p_actor)
    ) RETURNING id INTO v_event_id;
    RETURN v_event_id;
END;
$$;

REVOKE ALL ON FUNCTION public.grant_billing_access_override(UUID, TEXT, TIMESTAMPTZ, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.revoke_billing_access_override(UUID, TEXT, TEXT, TEXT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.grant_billing_access_override(UUID, TEXT, TIMESTAMPTZ, TEXT, TEXT)
    TO service_role;
GRANT EXECUTE ON FUNCTION public.revoke_billing_access_override(UUID, TEXT, TEXT, TEXT)
    TO service_role;

COMMENT ON VIEW public.tenant_billing_access IS
    'Canonical effective SaaS billing state. Stripe status is retained as provider_status.';
COMMENT ON TABLE public.billing_access_override_events IS
    'Immutable operator audit trail for time-bounded demo/partner access overrides.';

COMMIT;
