import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';
import { SupabaseService } from '../../core/services/supabase.service';
import { ThemeService } from '../../core/services/theme.service';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let auth: jasmine.SpyObj<AuthService & { setRole: (role: string) => void }>;
  let query: {
    selectedColumns: string | null;
    select: jasmine.Spy;
    eq: jasmine.Spy;
    is: jasmine.Spy;
    limit: jasmine.Spy;
  };

  beforeEach(async () => {
    auth = jasmine.createSpyObj<AuthService & { setRole: (role: string) => void }>(
      'AuthService',
      ['setToken', 'setTenantId', 'setRole', 'clearToken'],
    );

    query = {
      selectedColumns: null,
      select: jasmine.createSpy('select').and.callFake((columns: string) => {
        query.selectedColumns = columns;
        return query;
      }),
      eq: jasmine.createSpy('eq').and.returnValue(undefined),
      is: jasmine.createSpy('is').and.returnValue(undefined),
      limit: jasmine.createSpy('limit').and.resolveTo({
        data: [{ tenant_id: 'tenant-1', role: 'owner' }],
        error: null,
      }),
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
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  it('stores tenant role from membership lookup after sign-in', async () => {
    const component = fixture.componentInstance as unknown as {
      form: { setValue(value: { email: string; password: string }): void };
      submit(): Promise<void>;
    };

    component.form.setValue({ email: 'owner@example.com', password: 'correct-password' });
    await component.submit();

    expect(query.selectedColumns).toBe('tenant_id, role');
    expect(auth.setToken).toHaveBeenCalledWith('access-token-1');
    expect(auth.setTenantId).toHaveBeenCalledWith('tenant-1');
    expect(auth.setRole).toHaveBeenCalledWith('owner');
  });
});
