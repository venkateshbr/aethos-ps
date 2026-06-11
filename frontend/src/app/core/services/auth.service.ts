import { Injectable, inject, signal, computed } from '@angular/core';
import { setAccessToken, clearAccessToken, setTenantId, clearTenantId } from '../interceptors/auth.interceptor';
import { SupabaseService } from './supabase.service';

/**
 * AuthService — single source of truth for the access token lifecycle.
 *
 * Token storage strategy (pilot phase):
 *   - Mirror into localStorage under `aethos_token` so a hard refresh keeps the
 *     user signed in (needed by Founder + design partners during validation).
 *   - Also push into the auth interceptor's in-memory cache so HTTP requests
 *     attach the bearer header without re-reading storage on every call.
 *
 * Security note: localStorage is reachable from any same-origin script, so a
 * stored-XSS bug would leak the token. We accept this trade-off for the pilot
 * to get refresh-survival; the post-pilot hardening plan (see Prahari's backlog)
 * is to switch to an HttpOnly refresh cookie + short-lived in-memory access
 * token. Tracked separately — do not regress that work without coordinating.
 */

const STORAGE_KEY = 'aethos_token';
const TENANT_STORAGE_KEY = 'aethos_tenant_id';

@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Reactive token signal — components & guards read from here. */
  private _token = signal<string | null>(this.readFromStorage());

  /** Reactive tenant_id signal — components read the current tenant. */
  private _tenantId = signal<string | null>(this.readTenantFromStorage());

  /** Public read-only signal of the current access token (null when signed out). */
  readonly token = this._token.asReadonly();
  readonly tenantId = this._tenantId.asReadonly();

  /** True when a token is present. Derived signal — use in templates & guards. */
  readonly isAuthenticated = computed(() => this._token() !== null);

  private readonly supa = inject(SupabaseService);

  constructor() {
    // Sync the interceptor's in-memory cache with whatever we restored from
    // storage so the very first HTTP call carries both bearer + tenant headers.
    const t = this._token();
    const tid = this._tenantId();
    if (t) setAccessToken(t);
    if (tid) setTenantId(tid);

    // Keep aethos_token in sync when Supabase silently refreshes the JWT.
    // This prevents the interceptor carrying a stale token after a background
    // token rotation — especially visible in long-running E2E test sessions.
    this.supa.client.auth.onAuthStateChange((_event, session) => {
      const freshToken = session?.access_token;
      if (freshToken && this._token() !== null) {
        // Only update if we are currently signed in (don't re-set after logout)
        this._token.set(freshToken);
        setAccessToken(freshToken);
        if (typeof localStorage !== 'undefined') {
          localStorage.setItem(STORAGE_KEY, freshToken);
        }
      }
    });

    // Self-heal sessions created before the X-Tenant-ID rollout (#90): a token
    // restored from storage with no tenant_id means every API call 403s with
    // "Tenant context missing". Re-resolve the membership the same way login
    // does instead of leaving the user in a half-broken session.
    if (t && !tid) {
      void this.resolveTenantFromMembership();
    }
  }

  /**
   * Look up the signed-in user's tenant membership and store it. Used to
   * backfill tenant_id for sessions that predate the tenant-header rollout.
   * If the lookup fails (expired Supabase session, no membership), clear the
   * session entirely — a token without a tenant cannot make any API call.
   */
  private async resolveTenantFromMembership(): Promise<void> {
    try {
      const { data: userData } = await this.supa.client.auth.getUser();
      const userId = userData?.user?.id;
      if (!userId) {
        this.clearToken();
        return;
      }
      const { data: memberships, error } = await this.supa.client
        .from('tenant_users')
        .select('tenant_id')
        .eq('user_id', userId)
        .is('deleted_at', null)
        .limit(1);
      if (error || !memberships?.length) {
        this.clearToken();
        return;
      }
      this.setTenantId(memberships[0].tenant_id as string);
    } catch {
      this.clearToken();
    }
  }

  /**
   * Set the access token. Called after a successful signup / login response.
   * Mirrors into localStorage and the interceptor's in-memory cache.
   */
  setToken(token: string): void {
    this._token.set(token);
    setAccessToken(token);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, token);
    }
  }

  /**
   * Clear the access token. Called on logout or when a 401 response indicates
   * the session is no longer valid. Clears all three storage locations + tenant.
   */
  clearToken(): void {
    this._token.set(null);
    this._tenantId.set(null);
    clearAccessToken();
    clearTenantId();
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(TENANT_STORAGE_KEY);
    }
  }

  /** Synchronous getter for places that can't subscribe to the signal. */
  getToken(): string | null {
    return this._token();
  }

  /**
   * Set the tenant_id for the current session. Called by signup (after page 1
   * returns tenant_id) and by login (after a tenant_users lookup). The
   * interceptor attaches this as X-Tenant-ID on every authenticated request.
   */
  setTenantId(tenantId: string): void {
    this._tenantId.set(tenantId);
    setTenantId(tenantId);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(TENANT_STORAGE_KEY, tenantId);
    }
  }

  getTenantId(): string | null {
    return this._tenantId();
  }

  private readFromStorage(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEY);
  }

  private readTenantFromStorage(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(TENANT_STORAGE_KEY);
  }
}
