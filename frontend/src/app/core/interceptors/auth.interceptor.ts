import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Auth interceptor — attaches the Authorization header for authenticated API calls.
 *
 * Public routes (e.g. /p/:token → /api/v1/public/invoices/:token) must NOT have
 * an Authorization header. Callers can opt out by adding the `skip-auth` header to
 * the request; this interceptor strips that sentinel header before the request is sent.
 *
 * Token storage: held in module-level memory only, never in localStorage or
 * sessionStorage, so it cannot be exfiltrated by XSS attacks.
 */

// Module-level memory store — not accessible from JS outside this module.
let _accessToken: string | null = null;

/** Called by AuthService after a successful login. */
export function setAccessToken(token: string): void {
  _accessToken = token;
}

/** Called by AuthService on logout. */
export function clearAccessToken(): void {
  _accessToken = null;
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // If the caller included the skip-auth sentinel, strip it and forward with no auth header.
  if (req.headers.has('skip-auth')) {
    return next(req.clone({ headers: req.headers.delete('skip-auth') }));
  }

  // No token yet (unauthenticated state) — send the request as-is.
  if (!_accessToken) {
    return next(req);
  }

  // Attach the bearer token for all other requests.
  const authReq = req.clone({
    headers: req.headers.set('Authorization', `Bearer ${_accessToken}`),
  });
  return next(authReq);
};
