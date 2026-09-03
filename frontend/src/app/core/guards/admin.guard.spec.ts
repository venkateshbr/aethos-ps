import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';

import { adminGuard, isTenantAdminRole } from './admin.guard';
import { AuthService } from '../services/auth.service';

describe('adminGuard', () => {
  function runGuard(role: string | null): boolean | UrlTree {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { role: () => role } },
      ],
    });
    return TestBed.runInInjectionContext(
      () => adminGuard({} as never, {} as never),
    ) as boolean | UrlTree;
  }

  it('admits owner and admin roles', () => {
    expect(runGuard('owner')).toBeTrue();
    expect(runGuard('admin')).toBeTrue();
    expect(runGuard('Admin')).toBeTrue();
  });

  it('redirects every non-administrative role to the dashboard', () => {
    for (const role of ['manager', 'approver', 'member', 'auditor', 'viewer', 'employee', '', null]) {
      const result = runGuard(role);
      expect(result instanceof UrlTree)
        .withContext(`role=${role} must not reach the guides`)
        .toBeTrue();
      expect((result as UrlTree).toString()).toContain('/app/dashboard');
    }
  });

  it('classifies roles independently of the guard', () => {
    expect(isTenantAdminRole('owner')).toBeTrue();
    expect(isTenantAdminRole('manager')).toBeFalse();
    expect(isTenantAdminRole(undefined)).toBeFalse();
  });
});
