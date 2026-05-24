/**
 * Production environment config.
 *
 * Real values are injected at deploy-time (Vercel env vars) — these placeholders
 * exist so the build does not fail. Replace before going live.
 */
export const environment = {
  production: true,
  apiUrl: 'https://api.aethos.app',
  supabaseUrl: '',
  supabaseAnonKey: '',
  stripePublishableKey: '',
};
