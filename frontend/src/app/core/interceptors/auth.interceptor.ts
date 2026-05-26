import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

/**
 * Auth interceptor — attaches the Authorization header for authenticated API calls.
 *
 * Public routes (e.g. /p/:token → /api/v1/public/invoices/:token) must NOT have
 * an Authorization header. Callers can opt out by adding the `skip-auth` header to
 * the request; this interceptor strips that sentinel header before the request is sent.
 *
 * Token storage:
 *   - Module-level memory (`_accessToken`) is the runtime source for header
 *     attachment, so per-request reads stay cheap.
 *   - `AuthService` mirrors the token into localStorage so a hard refresh
 *     keeps the user signed in during the pilot (XSS trade-off documented in
 *     `auth.service.ts`).
 *
 * 401 handling — issue #111:
 *   When the API returns 401 we clear all stored token state and redirect to
 *   the landing page. This protects against the case where the token expires
 *   mid-session: without this handler the user would see a half-broken UI
 *   that keeps spinning instead of being prompted to re-authenticate.
 */

// Module-level memory store — not accessible from JS outside this module.
let _accessToken: string | null = null;
let _tenantId: string | null = null;

/** Called by AuthService after a successful login. */
export function setAccessToken(token: string): void {
  _accessToken = token;
}

/** Called by AuthService on logout. */
export function clearAccessToken(): void {
  _accessToken = null;
}

/** Called by AuthService when the tenant context is established (post-signup,
 *  post-login, or restored from localStorage on app boot). */
export function setTenantId(tenantId: string): void {
  _tenantId = tenantId;
}

export function clearTenantId(): void {
  _tenantId = null;
}

const STORAGE_KEY = 'aethos_token';
const TENANT_STORAGE_KEY = 'aethos_tenant_id';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  // If the caller included the skip-auth sentinel, strip it and forward with no auth header.
  if (req.headers.has('skip-auth')) {
    return next(req.clone({ headers: req.headers.delete('skip-auth') }));
  }

  // Attach both Authorization and X-Tenant-ID when we have them. The backend's
  // membership dependency (`get_tenant_id` per #90) requires X-Tenant-ID on
  // every authenticated route — without it the API replies 403 "Tenant
  // context missing".
  let headers = req.headers;
  if (_accessToken) {
    headers = headers.set('Authorization', `Bearer ${_accessToken}`);
  }
  if (_tenantId && !req.headers.has('X-Tenant-ID')) {
    headers = headers.set('X-Tenant-ID', _tenantId);
  }
  const forwarded = headers === req.headers ? req : req.clone({ headers });

  return next(forwarded).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401) {
        // Session expired or token invalid — flush all token state and bounce.
        // We intentionally clear localStorage here (rather than depending on
        // AuthService) so the interceptor is self-contained and there is no
        // circular DI risk.
        _accessToken = null;
        _tenantId = null;
        if (typeof localStorage !== 'undefined') {
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem(TENANT_STORAGE_KEY);
        }
        // Avoid a navigation storm if multiple in-flight calls 401 at once —
        // only navigate when we're not already on the landing route.
        if (!router.url.startsWith('/?') && router.url !== '/') {
          void router.navigate(['/'], {
            queryParams: { sessionExpired: '1' },
          });
        }
      }
      return throwError(() => err);
    }),
  );
};
