import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';

import { AuthService } from './auth.service';

export interface CurrentPermissionsResponse {
  tenant_id: string;
  user_id: string;
  legacy_role: string;
  role_codes: string[];
  role_labels: string[];
  privilege_codes: string[];
  must_change_password: boolean;
}

/** Tenant/session-scoped effective privileges used only for UI affordances. */
@Injectable({ providedIn: 'root' })
export class CurrentPermissionsService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly privilegeSet = signal<ReadonlySet<string>>(new Set<string>());
  private readonly loadedUserId = signal<string | null>(null);
  private requestedSessionKey: string | null = null;

  readonly loading = signal(false);
  readonly loaded = signal(false);
  readonly error = signal<string | null>(null);
  readonly userId = computed(() => {
    const loadedUserId = this.loadedUserId();
    return this.currentSessionKey() === this.requestedSessionKey ? loadedUserId : null;
  });

  /** Load once for the current authenticated user + tenant; concurrent callers share it. */
  ensureLoaded(): void {
    const sessionKey = this.currentSessionKey();
    if (!sessionKey) {
      this.reset();
      return;
    }
    if (this.requestedSessionKey === sessionKey) return;

    this.requestedSessionKey = sessionKey;
    this.privilegeSet.set(new Set<string>());
    this.loadedUserId.set(null);
    this.loading.set(true);
    this.loaded.set(false);
    this.error.set(null);

    const expectedTenantId = this.auth.tenantId();
    this.http.get<CurrentPermissionsResponse>('/api/v1/security/me/permissions').subscribe({
      next: (response) => {
        if (sessionKey !== this.currentSessionKey()) return;
        if (response.tenant_id !== expectedTenantId) {
          this.failClosed('Permission response did not match the active tenant.');
          return;
        }
        this.privilegeSet.set(new Set(response.privilege_codes));
        this.loadedUserId.set(response.user_id);
        this.loading.set(false);
        this.loaded.set(true);
      },
      error: () => {
        if (sessionKey !== this.currentSessionKey()) return;
        this.failClosed('Could not load current permissions.');
      },
    });
  }

  hasPrivilege(privilegeCode: string): boolean {
    const sessionKey = this.currentSessionKey();
    return !!sessionKey
      && sessionKey === this.requestedSessionKey
      && this.loaded()
      && this.privilegeSet().has(privilegeCode);
  }

  private currentSessionKey(): string | null {
    const token = this.auth.token();
    const tenantId = this.auth.tenantId();
    return token && tenantId
      ? JSON.stringify([tenantId, this.tokenIdentity(token)])
      : null;
  }

  /**
   * Access-token rotation must not invalidate permissions for the same user.
   * The JWT payload is decoded only to partition this in-memory cache; backend
   * authorization remains authoritative and still verifies the signed token.
   */
  private tokenIdentity(token: string): string {
    const payloadSegment = token.split('.')[1];
    if (payloadSegment && typeof atob === 'function') {
      try {
        const base64 = payloadSegment.replace(/-/g, '+').replace(/_/g, '/');
        const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
        const payload = JSON.parse(atob(padded)) as { sub?: unknown };
        if (typeof payload.sub === 'string' && payload.sub.length > 0) {
          return `subject:${payload.sub}`;
        }
      } catch {
        // Opaque/non-JWT test tokens use a non-reversible in-memory fingerprint.
      }
    }

    let hash = 2166136261;
    for (let index = 0; index < token.length; index += 1) {
      hash = Math.imul(hash ^ token.charCodeAt(index), 16777619);
    }
    return `opaque:${token.length}:${(hash >>> 0).toString(36)}`;
  }

  private failClosed(message: string): void {
    this.privilegeSet.set(new Set<string>());
    this.loadedUserId.set(null);
    this.loading.set(false);
    this.loaded.set(false);
    this.error.set(message);
  }

  private reset(): void {
    this.requestedSessionKey = null;
    this.privilegeSet.set(new Set<string>());
    this.loadedUserId.set(null);
    this.loading.set(false);
    this.loaded.set(false);
    this.error.set(null);
  }
}
