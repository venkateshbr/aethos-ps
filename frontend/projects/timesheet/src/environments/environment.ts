/**
 * Timesheet Portal — local-dev environment.
 * Shares the same Supabase project and backend API as the main ERP.
 */
export const environment = {
  production: false,
  apiUrl: '',  // relative — Angular dev proxy forwards /api → :8011
  supabaseUrl: 'https://glcljucaayeesvrsjths.supabase.co',
  supabaseAnonKey:
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdsY2xqdWNhYXllZXN2cnNqdGhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkxOTU4ODIsImV4cCI6MjA5NDc3MTg4Mn0.KPGSpR8OmQ9BRKEx4PQ-qcDoSsdgAH_bkOrM_RfX4Is',
};
