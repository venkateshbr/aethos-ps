import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';

import { AuthService } from '../services/auth.service';
import { TimesheetPortalNavigationService } from '../services/timesheet-portal-navigation.service';
import { timesheetPortalLoginUrl } from '../utils/timesheet-portal-url';
import { authChildGuard, authGuard } from './auth.guard';

describe('authGuard Timesheet Employee boundary', () => {
  it('redirects an authenticated employee away from the main app to the Timesheet portal', () => {
    const redirectToLogin = jasmine.createSpy('redirectToLogin');
    const auth = {
      isAuthenticated: signal(true),
      mustChangePassword: signal(false),
      role: signal<string | null>('employee'),
    };

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        {
          provide: Router,
          useValue: { createUrlTree: jasmine.createSpy('createUrlTree') },
        },
        {
          provide: TimesheetPortalNavigationService,
          useValue: { redirectToLogin },
        },
      ],
    });

    const result = TestBed.runInInjectionContext(() =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/app/invoices' } as RouterStateSnapshot,
      ),
    );

    expect(result).toBeFalse();
    expect(redirectToLogin).toHaveBeenCalledTimes(1);
    expect(timesheetPortalLoginUrl()).toBe('http://localhost:4200/login');
  });

  it('applies the same employee boundary during child-route activation', () => {
    const redirectToLogin = jasmine.createSpy('redirectToLogin');
    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAuthenticated: signal(true),
            mustChangePassword: signal(false),
            role: signal<string | null>('employee'),
          },
        },
        {
          provide: TimesheetPortalNavigationService,
          useValue: { redirectToLogin },
        },
      ],
    });

    const result = TestBed.runInInjectionContext(() =>
      authChildGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/app/reports' } as RouterStateSnapshot,
      ),
    );

    expect(result).toBeFalse();
    expect(redirectToLogin).toHaveBeenCalledTimes(1);
  });

  it('continues to admit authenticated ERP roles', () => {
    const redirectToLogin = jasmine.createSpy('redirectToLogin');
    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            isAuthenticated: signal(true),
            mustChangePassword: signal(false),
            role: signal<string | null>('owner'),
          },
        },
        {
          provide: Router,
          useValue: { createUrlTree: jasmine.createSpy('createUrlTree') },
        },
        {
          provide: TimesheetPortalNavigationService,
          useValue: { redirectToLogin },
        },
      ],
    });

    const result = TestBed.runInInjectionContext(() =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/app/invoices' } as RouterStateSnapshot,
      ),
    );

    expect(result).toBeTrue();
    expect(redirectToLogin).not.toHaveBeenCalled();
  });
});
