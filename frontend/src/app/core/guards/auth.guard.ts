import { inject } from '@angular/core';
import {
  CanActivateFn,
  CanActivateChildFn,
  Router,
  createUrlTreeFromSnapshot,
} from '@angular/router';
import { AuthService } from '../services/auth.service';
import { TimesheetPortalNavigationService } from '../services/timesheet-portal-navigation.service';
import { isTimesheetEmployeeRole } from '../utils/timesheet-portal-url';

/**
 * authGuard — blocks `/app/*` routes when no access token is present.
 *
 * Resolution:
 *   - Authenticated ERP role → returns `true` and navigation proceeds.
 *   - Timesheet Employee → leaves this origin for the dedicated portal.
 *   - Unauthenticated → returns a UrlTree pointing at `/` (landing). The
 *     `returnUrl` query param is set so a future sign-in flow can route the
 *     user back to where they were going (no consumer yet — landing ignores
 *     it for now; ticketed as a follow-up).
 *
 * Issue #111 — Founder reported any visitor could browse `/app/inbox`,
 * `/app/copilot`, etc. without authenticating. This guard plugs that hole.
 */
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) {
    if (isTimesheetEmployeeRole(auth.role())) {
      inject(TimesheetPortalNavigationService).redirectToLogin();
      return false;
    }
    if (auth.mustChangePassword() && state.url !== '/app/profile') {
      return router.createUrlTree(['/app/profile']);
    }
    return true;
  }

  // Build a UrlTree to `/` with the attempted URL preserved for post-signin redirect.
  return router.createUrlTree(['/'], {
    queryParams: { returnUrl: state.url },
  });
};

/**
 * authChildGuard — same logic as `authGuard`, applied per child activation so
 * a 401-triggered token clear mid-session boots the user out on next navigation
 * rather than letting them see stale shell chrome.
 */
export const authChildGuard: CanActivateChildFn = (childRoute, state) => {
  const auth = inject(AuthService);

  if (auth.isAuthenticated()) {
    if (isTimesheetEmployeeRole(auth.role())) {
      inject(TimesheetPortalNavigationService).redirectToLogin();
      return false;
    }
    if (auth.mustChangePassword() && state.url !== '/app/profile') {
      return createUrlTreeFromSnapshot(childRoute, ['/app/profile']);
    }
    return true;
  }

  return createUrlTreeFromSnapshot(childRoute, ['/'], { returnUrl: state.url });
};
