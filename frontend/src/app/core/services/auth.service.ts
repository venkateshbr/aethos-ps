import { Injectable, signal, computed } from '@angular/core';
import { setAccessToken, clearAccessToken } from '../interceptors/auth.interceptor';

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

@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Reactive token signal — components & guards read from here. */
  private _token = signal<string | null>(this.readFromStorage());

  /** Public read-only signal of the current access token (null when signed out). */
  readonly token = this._token.asReadonly();

  /** True when a token is present. Derived signal — use in templates & guards. */
  readonly isAuthenticated = computed(() => this._token() !== null);

  constructor() {
    // Sync the interceptor's in-memory cache with whatever we restored from
    // storage so the very first HTTP call carries the bearer header.
    const t = this._token();
    if (t) {
      setAccessToken(t);
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
   * the session is no longer valid. Clears all three storage locations.
   */
  clearToken(): void {
    this._token.set(null);
    clearAccessToken();
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  /** Synchronous getter for places that can't subscribe to the signal. */
  getToken(): string | null {
    return this._token();
  }

  private readFromStorage(): string | null {
    if (typeof localStorage === 'undefined') return null;
    return localStorage.getItem(STORAGE_KEY);
  }
}
