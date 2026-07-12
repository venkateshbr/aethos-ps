/**
 * Production environment config — Cloudflare tunnel pilot.
 *
 * apiUrl points at the backend tunnel hostname. Supabase and Stripe keys
 * are publishable-safe (RLS + server-side auth enforce security).
 */
export const environment = {
  production: true,
  // Empty = relative URLs. Nginx in the Docker container proxies /api/* to
  // the backend service on the internal Docker network (api:8080). No CORS
  // needed; single origin for all requests.
  apiUrl: '',
  timesheetPortalUrl: 'https://timesheet.aethos.ishirock.tech',
  supabaseUrl: 'https://glcljucaayeesvrsjths.supabase.co',
  supabaseAnonKey:
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY2xqdWNhYXllZXN2cnNqdGhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxOTU4ODIsImV4cCI6MjA5NDc3MTg4Mn0.KPGSpR8OmQ9BRKEx4PQ-qcDoSsdgAH_bkOrM_RfX4Is',
  stripePublishableKey:
    'pk_test_51RUPgbGb8SeBo1cMoehCFEwE2a5KJWfxoMNkE30mNptvvL8DPkfcvEfdhtjaq2lgZ5NHab4FhNnoytBGC72Esfix00CS15yc7t',
};
