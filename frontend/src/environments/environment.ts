/**
 * Local-dev environment config.
 *
 * Keep these aligned with `backend/.env`:
 *   - supabaseUrl / supabaseAnonKey  → SUPABASE_URL / SUPABASE_ANON_KEY
 *   - stripePublishableKey            → STRIPE_PUBLISHABLE_KEY
 *
 * The anon key is *publishable* (RLS enforces tenant scoping) — safe to ship
 * to the browser. The Stripe publishable key is also browser-safe by design.
 *
 * Signup uses Supabase Auth directly from the FE (see SignupService) because
 * the backend's POST /auth/signup does NOT return an access token — only a
 * tenant_id and SetupIntent client_secret. After backend signup completes we
 * call `supabase.auth.signInWithPassword()` to mint a JWT for the subsequent
 * authenticated calls to /billing/prices and /billing/start-trial.
 */
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8011',
  supabaseUrl: 'https://glcljucaayeesvrsjths.supabase.co',
  supabaseAnonKey:
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY2xqdWNhYXllZXN2cnNqdGhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxOTU4ODIsImV4cCI6MjA5NDc3MTg4Mn0.KPGSpR8OmQ9BRKEx4PQ-qcDoSsdgAH_bkOrM_RfX4Is',
  stripePublishableKey:
    'pk_test_51RUPgbGb8SeBo1cMoehCFEwE2a5KJWfxoMNkE30mNptvvL8DPkfcvEfdhtjaq2lgZ5NHab4FhNnoytBGC72Esfix00CS15yc7t',
};
