/**
 * Portal auth — token + tenant storage, HTTP interceptor, and route guard.
 * Trimmed copy of the main ERP's auth plumbing (issue #134, P4). The portal
 * shares the same Supabase project, so the same JWT + X-Tenant-ID contract
 * applies. localStorage keys are portal-specific to avoid clobbering a main-app
 * session in the same browser.
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

const TOKEN_KEY = 'aethos_ts_token';
const TENANT_KEY = 'aethos_ts_tenant_id';
const MUST_CHANGE_PASSWORD_KEY = 'aethos_ts_must_change_password';

// Module-level cache for cheap per-request header attachment.
let _token: string | null = null;
let _tenantId: string | null = null;

function readStoredValue(key: string): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(key);
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _t = signal<string | null>(localStorage.getItem(TOKEN_KEY));
  private _tid = signal<string | null>(localStorage.getItem(TENANT_KEY));
  private _mustChangePassword = signal(
    localStorage.getItem(MUST_CHANGE_PASSWORD_KEY) === 'true',
  );
  readonly isAuthenticated = computed(() => this._t() !== null);
  readonly mustChangePassword = computed(() => this._mustChangePassword());

  constructor() {
    _token = this._t();
    _tenantId = this._tid();
  }

  setSession(token: string, tenantId: string, mustChangePassword = false): void {
    this._t.set(token); this._tid.set(tenantId);
    this._mustChangePassword.set(mustChangePassword);
    _token = token; _tenantId = tenantId;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TENANT_KEY, tenantId);
    localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, String(mustChangePassword));
  }

  refreshToken(token: string): void {
    this._t.set(token);
    _token = token;
    localStorage.setItem(TOKEN_KEY, token);
  }

  markPasswordChanged(): void {
    this._mustChangePassword.set(false);
    localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, 'false');
  }

  markPasswordChangeRequired(): void {
    this._mustChangePassword.set(true);
    localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, 'true');
  }

  clear(): void {
    this._t.set(null); this._tid.set(null);
    _token = null; _tenantId = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TENANT_KEY);
    localStorage.removeItem(MUST_CHANGE_PASSWORD_KEY);
  }
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const auth = inject(AuthService);
  const token = _token ?? readStoredValue(TOKEN_KEY);
  const tenantId = _tenantId ?? readStoredValue(TENANT_KEY);
  if (token && !_token) _token = token;
  if (tenantId && !_tenantId) _tenantId = tenantId;

  let headers = req.headers;
  if (token) headers = headers.set('Authorization', `Bearer ${token}`);
  if (tenantId && !req.headers.has('X-Tenant-ID')) headers = headers.set('X-Tenant-ID', tenantId);
  const forwarded = headers === req.headers ? req : req.clone({ headers });
  return next(forwarded).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401) {
        auth.clear();
        if (router.url !== '/login') void router.navigate(['/login']);
      }
      if (
        err instanceof HttpErrorResponse
        && err.status === 403
        && err.error?.detail === 'PASSWORD_CHANGE_REQUIRED'
      ) {
        auth.markPasswordChangeRequired();
        if (router.url !== '/change-password') void router.navigate(['/change-password']);
      }
      return throwError(() => err);
    }),
  );
};

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.isAuthenticated() ? true : router.createUrlTree(['/login']);
};

export const passwordReadyGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) return router.createUrlTree(['/login']);
  return auth.mustChangePassword()
    ? router.createUrlTree(['/change-password'])
    : true;
};
