-- Distributed app-level rate limiting for high-risk public endpoints.
-- Stores only hashed subjects; no raw IPs, JWTs, public invoice tokens, API
-- keys, document text, or request payloads are persisted.

CREATE TABLE IF NOT EXISTS public.rate_limit_events (
    id BIGSERIAL PRIMARY KEY,
    rule_name TEXT NOT NULL,
    subject_hash TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_events_window
    ON public.rate_limit_events (rule_name, subject_hash, occurred_at DESC);

ALTER TABLE public.rate_limit_events ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.check_rate_limit(
    p_rule_name TEXT,
    p_subject_hash TEXT,
    p_max_requests INTEGER,
    p_window_seconds INTEGER
)
RETURNS TABLE (
    allowed BOOLEAN,
    request_count INTEGER,
    retry_after_seconds INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_now TIMESTAMPTZ := now();
    v_window_start TIMESTAMPTZ := v_now - make_interval(secs => p_window_seconds);
    v_oldest TIMESTAMPTZ;
    v_count INTEGER;
BEGIN
    IF p_max_requests <= 0 OR p_window_seconds <= 0 THEN
        RETURN QUERY SELECT false, 0, 1;
        RETURN;
    END IF;

    -- Serialise by rule+subject so concurrent instances cannot both pass the
    -- same final request in a window.
    PERFORM pg_advisory_xact_lock(hashtext(p_rule_name || ':' || p_subject_hash));

    DELETE FROM public.rate_limit_events
    WHERE occurred_at < v_now - interval '1 day';

    DELETE FROM public.rate_limit_events
    WHERE rule_name = p_rule_name
      AND subject_hash = p_subject_hash
      AND occurred_at <= v_window_start;

    SELECT count(*)::INTEGER, min(occurred_at)
      INTO v_count, v_oldest
      FROM public.rate_limit_events
     WHERE rule_name = p_rule_name
       AND subject_hash = p_subject_hash
       AND occurred_at > v_window_start;

    IF v_count >= p_max_requests THEN
        RETURN QUERY SELECT
            false,
            v_count,
            GREATEST(1, CEIL(EXTRACT(EPOCH FROM (v_oldest + make_interval(secs => p_window_seconds) - v_now)))::INTEGER);
        RETURN;
    END IF;

    INSERT INTO public.rate_limit_events (rule_name, subject_hash, occurred_at)
    VALUES (p_rule_name, p_subject_hash, v_now);

    RETURN QUERY SELECT true, v_count + 1, 0;
END;
$$;

REVOKE ALL ON public.rate_limit_events FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.check_rate_limit(TEXT, TEXT, INTEGER, INTEGER) TO service_role;
