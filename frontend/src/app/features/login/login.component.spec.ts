import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';
import { ThemeService } from '../../core/services/theme.service';
import { TimesheetPortalNavigationService } from '../../core/services/timesheet-portal-navigation.service';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let auth: jasmine.SpyObj<AuthService & { setRole: (role: string) => void }>;
  let navigate: jasmine.Spy;
  let portalAssign: jasmine.Spy;
  let membership: {
    tenant_id: string;
    role: string;
    must_change_password: boolean;
  };
  let query: {
    selectedColumns: string | null;
    select: jasmine.Spy;
    eq: jasmine.Spy;
    is: jasmine.Spy;
    limit: jasmine.Spy;
  };

  beforeEach(async () => {
    portalAssign = jasmine.createSpy('assign');
    auth = jasmine.createSpyObj<AuthService & { setRole: (role: string) => void }>(
      'AuthService',
      [
        'setToken',
        'setTenantId',
        'setRole',
        'setMustChangePassword',
        'getMustChangePassword',
        'clearToken',
      ],
    );
    membership = {
      tenant_id: 'tenant-1',
      role: 'owner',
      must_change_password: false,
    };
    auth.getMustChangePassword.and.callFake(
      () => Boolean(auth.setMustChangePassword.calls.mostRecent()?.args[0]),
    );

    query = {
      selectedColumns: null,
      select: jasmine.createSpy('select').and.callFake((columns: string) => {
        query.selectedColumns = columns;
        return query;
      }),
      eq: jasmine.createSpy('eq').and.returnValue(undefined),
      is: jasmine.createSpy('is').and.returnValue(undefined),
      limit: jasmine.createSpy('limit').and.callFake(async () => ({
        data: [membership],
        error: null,
      })),
    };
    query.eq.and.returnValue(query);
    query.is.and.returnValue(query);

    const supabase = {
      client: {
        auth: {
          signInWithPassword: jasmine.createSpy('signInWithPassword').and.resolveTo({
            data: {
              session: {
                access_token: 'access-token-1',
                user: { id: 'user-1' },
              },
            },
            error: null,
          }),
        },
        from: jasmine.createSpy('from').and.returnValue(query),
      },
    };

    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: auth },
        { provide: SupabaseService, useValue: supabase },
        {
          provide: ThemeService,
          useValue: {
            meta: () => ({ lockupSrc: '/assets/test-lockup.svg', label: 'test' }),
          },
        },
        {
          provide: TimesheetPortalNavigationService,
          useValue: { redirectToLogin: portalAssign },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  it('stores tenant role from membership lookup after sign-in', async () => {
    const component = fixture.componentInstance as unknown as {
      form: { setValue(value: { email: string; password: string }): void };
      submit(): Promise<void>;
    };

    component.form.setValue({ email: 'owner@example.com', password: 'correct-password' });
    await component.submit();

    expect(query.selectedColumns).toBe('tenant_id, role, must_change_password');
    expect(auth.setToken).toHaveBeenCalledWith('access-token-1');
    expect(auth.setTenantId).toHaveBeenCalledWith('tenant-1');
    expect(auth.setRole).toHaveBeenCalledWith('owner');
    expect(auth.setMustChangePassword).toHaveBeenCalledOnceWith(false);
    expect(navigate).toHaveBeenCalledOnceWith(['/app/copilot']);
  });

  it('routes an admin-created user to profile when an initial password change is required', async () => {
    membership = {
      ...membership,
      must_change_password: true,
    };
    const component = fixture.componentInstance as unknown as {
      form: { setValue(value: { email: string; password: string }): void };
      submit(): Promise<void>;
    };

    component.form.setValue({ email: 'finance@example.com', password: 'temporary-password' });
    await component.submit();

    expect(auth.setMustChangePassword).toHaveBeenCalledOnceWith(true);
    expect(navigate).toHaveBeenCalledOnceWith(['/app/profile']);
  });

  it('redirects a Timesheet Employee login to the separate portal instead of the ERP', async () => {
    membership = {
      ...membership,
      role: 'employee',
      must_change_password: true,
    };
    const component = fixture.componentInstance as unknown as {
      form: { setValue(value: { email: string; password: string }): void };
      submit(): Promise<void>;
    };

    component.form.setValue({
      email: 'employee@example.com',
      password: 'temporary-password',
    });
    await component.submit();

    expect(auth.setRole).toHaveBeenCalledOnceWith('employee');
    expect(portalAssign).toHaveBeenCalledTimes(1);
    expect(navigate).not.toHaveBeenCalled();
  });
});
