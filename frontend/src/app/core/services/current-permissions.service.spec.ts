import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { CurrentPermissionsService } from './current-permissions.service';

function jwtFor(subject: string, rotation: string): string {
  const encode = (value: object): string => btoa(JSON.stringify(value))
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
  return `${encode({ alg: 'none' })}.${encode({ sub: subject, rotation })}.signature`;
}

describe('CurrentPermissionsService', () => {
  it('fetches effective permissions only once for the current tenant session', () => {
    const token = signal<string | null>('session-token');
    const tenantId = signal<string | null>('tenant-1');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            token: token.asReadonly(),
            tenantId: tenantId.asReadonly(),
          },
        },
      ],
    });
    const service = TestBed.inject(CurrentPermissionsService);
    const http = TestBed.inject(HttpTestingController);

    service.ensureLoaded();
    service.ensureLoaded();

    const request = http.expectOne('/api/v1/security/me/permissions');
    expect(request.request.method).toBe('GET');
    request.flush({
      tenant_id: 'tenant-1',
      user_id: 'user-1',
      legacy_role: 'manager',
      role_codes: ['ar_manager'],
      role_labels: ['AR Manager'],
      privilege_codes: ['invoices.read', 'invoices.mark_paid'],
      must_change_password: false,
    });

    service.ensureLoaded();
    http.expectNone('/api/v1/security/me/permissions');
    expect(service.hasPrivilege('invoices.mark_paid')).toBeTrue();
    expect(service.hasPrivilege('invoices.post')).toBeFalse();
    expect(service.userId()).toBe('user-1');
    http.verify();
  });

  it('keeps loaded permissions when Supabase rotates the token for the same user', () => {
    const token = signal<string | null>(jwtFor('user-1', 'initial'));
    const tenantId = signal<string | null>('tenant-1');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            token: token.asReadonly(),
            tenantId: tenantId.asReadonly(),
          },
        },
      ],
    });
    const service = TestBed.inject(CurrentPermissionsService);
    const http = TestBed.inject(HttpTestingController);

    service.ensureLoaded();
    http.expectOne('/api/v1/security/me/permissions').flush({
      tenant_id: 'tenant-1',
      user_id: 'user-1',
      legacy_role: 'manager',
      role_codes: ['ar_manager'],
      role_labels: ['AR Manager'],
      privilege_codes: ['invoices.mark_paid'],
      must_change_password: false,
    });

    token.set(jwtFor('user-1', 'refreshed'));

    expect(service.hasPrivilege('invoices.mark_paid')).toBeTrue();
    service.ensureLoaded();
    http.expectNone('/api/v1/security/me/permissions');
    http.verify();
  });

  it('resets and refetches for a different user in the same tenant', () => {
    const token = signal<string | null>(jwtFor('user-1', 'initial'));
    const tenantId = signal<string | null>('tenant-1');
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: AuthService,
          useValue: {
            token: token.asReadonly(),
            tenantId: tenantId.asReadonly(),
          },
        },
      ],
    });
    const service = TestBed.inject(CurrentPermissionsService);
    const http = TestBed.inject(HttpTestingController);

    service.ensureLoaded();
    http.expectOne('/api/v1/security/me/permissions').flush({
      tenant_id: 'tenant-1',
      user_id: 'user-1',
      legacy_role: 'manager',
      role_codes: ['ar_manager'],
      role_labels: ['AR Manager'],
      privilege_codes: ['invoices.mark_paid'],
      must_change_password: false,
    });

    token.set(jwtFor('user-2', 'new-login'));

    expect(service.hasPrivilege('invoices.mark_paid')).toBeFalse();
    expect(service.userId()).toBeNull();
    service.ensureLoaded();
    expect(service.userId()).toBeNull();
    http.expectOne('/api/v1/security/me/permissions').flush({
      tenant_id: 'tenant-1',
      user_id: 'user-2',
      legacy_role: 'manager',
      role_codes: ['billing_specialist'],
      role_labels: ['Billing Specialist'],
      privilege_codes: ['invoices.draft'],
      must_change_password: false,
    });
    expect(service.hasPrivilege('invoices.mark_paid')).toBeFalse();
    expect(service.hasPrivilege('invoices.draft')).toBeTrue();
    expect(service.userId()).toBe('user-2');
    http.verify();
  });
});
