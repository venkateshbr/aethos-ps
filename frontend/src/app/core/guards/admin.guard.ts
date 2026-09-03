import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Legacy tenant roles that carry tenant-administration authority.
 *
 * The security catalogue (migration 0096) projects every one of its 22 system
 * roles onto this legacy set; `owner` and `admin` are the two projections that
 * administer the tenant (Tenant Owner, Tenant Admin, CFO, Finance Controller,
 * GL Accountant, Close Manager, AI Operations Admin). Everything else — manager,
 * approver, member, auditor, viewer, employee — is operational or read-only.
 */
const ADMIN_ROLES: ReadonlySet<string> = new Set(['owner', 'admin']);

export function isTenantAdminRole(role: string | null | undefined): boolean {
  return ADMIN_ROLES.has((role ?? '').trim().toLowerCase());
}

/**
 * adminGuard — restricts a route to tenant owners and admins.
 *
 * Applied to `/app/guides` so the guide library (which now includes the Nous
 * runtime and learning-operations manual, covering secret rotation and open
 * security gaps) is not readable by ordinary staff or by anonymous visitors.
 *
 * Layering: `authGuard` on the `/app` parent has already established that a
 * session exists, so an unauthenticated visitor never reaches this guard. A
 * signed-in user without the role is sent to the dashboard rather than to the
 * landing page — they are authenticated, just not permitted here.
 *
 * This is a UI affordance only. Guide HTML is served as a static asset today,
 * so treat this as "not advertised to non-admins" rather than a hard access
 * control until the guide payloads move behind an authenticated endpoint.
 */
export const adminGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (isTenantAdminRole(auth.role())) return true;

  return router.createUrlTree(['/app/dashboard'], {
    queryParams: { denied: 'guides' },
  });
};
