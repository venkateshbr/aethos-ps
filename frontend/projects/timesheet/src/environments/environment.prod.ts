/**
 * Timesheet Portal — production (Docker + nginx + Cloudflare tunnel).
 * apiUrl empty → nginx proxies /api/* to the backend on the internal network.
 */
export const environment = {
  production: true,
  apiUrl: '',
  supabaseUrl: 'https://glcljucaayeesvrsjths.supabase.co',
  supabaseAnonKey:
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY2xqdWNhYXllZXN2cnNqdGhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxOTU4ODIsImV4cCI6MjA5NDc3MTg4Mn0.KPGSpR8OmQ9BRKEx4PQ-qcDoSsdgAH_bkOrM_RfX4Is',
};
