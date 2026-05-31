/**
 * Production environment config — Cloudflare tunnel pilot.
 *
 * apiUrl points at the backend tunnel hostname. Supabase and Stripe keys
 * are publishable-safe (RLS + server-side auth enforce security).
 */
export const environment = {
  production: true,
  apiUrl: 'https://aethos-api.ishirock.com',
  supabaseUrl: 'https://glcljucaayeesvrsjths.supabase.co',
  supabaseAnonKey:
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY2xqdWNhYXllZXN2cnNqdGhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxOTU4ODIsImV4cCI6MjA5NDc3MTg4Mn0.KPGSpR8OmQ9BRKEx4PQ-qcDoSsdgAH_bkOrM_RfX4Is',
  stripePublishableKey:
    'pk_test_51RUPgbGb8SeBo1cMoehCFEwE2a5KJWfxoMNkE30mNptvvL8DPkfcvEfdhtjaq2lgZ5NHab4FhNnoytBGC72Esfix00CS15yc7t',
};
