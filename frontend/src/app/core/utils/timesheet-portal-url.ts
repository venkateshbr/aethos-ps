import { environment } from '../../../environments/environment';

/** Return the configured Timesheet Portal login URL without host-specific guard logic. */
export function timesheetPortalLoginUrl(): string {
  const portalOrigin = environment.timesheetPortalUrl.trim().replace(/\/+$/, '');
  return `${portalOrigin}/login`;
}

/** Accept the stored legacy role and the catalog code during role migrations. */
export function isTimesheetEmployeeRole(role: string | null): boolean {
  return role === 'employee' || role === 'timesheet_employee';
}
