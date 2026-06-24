import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthService } from '../../core/services/auth.service';
import { ApprovalPolicyComponent } from './approval-policy.component';

const policy = {
  tenant_id: 'tenant-1',
  policy_source: 'system_default',
  money_out_default_role: 'admin',
  money_out_owner_threshold: '50000',
  money_out_owner_role: 'owner',
  accounting_role: 'admin',
  money_in_role: 'manager',
  draft_role: 'manager',
  external_send_role: 'manager',
  high_risk_role: 'admin',
  created_at: null,
  updated_at: null,
} as const;

describe('ApprovalPolicyComponent', () => {
  let fixture: ComponentFixture<ApprovalPolicyComponent>;
  let http: HttpTestingController;

  async function setup(roleValue: 'admin' | 'manager' = 'admin'): Promise<void> {
    const role = signal<string | null>(roleValue);

    await TestBed.configureTestingModule({
      imports: [ApprovalPolicyComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { role: role.asReadonly() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ApprovalPolicyComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
  });

  it('loads the effective default approval policy', async () => {
    await setup('admin');

    const req = http.expectOne('/api/v1/approval-policy/effective');
    expect(req.request.method).toBe('GET');
    req.flush(policy);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('System default');
    expect(fixture.componentInstance.form.getRawValue().money_out_default_role).toBe('admin');
  });

  it('saves admin policy edits through the API contract', async () => {
    await setup('admin');
    http.expectOne('/api/v1/approval-policy/effective').flush(policy);

    fixture.componentInstance.form.patchValue({
      money_out_default_role: 'owner',
      money_out_owner_threshold: 25000,
      accounting_role: 'owner',
      external_send_role: 'admin',
      high_risk_role: 'owner',
    });
    fixture.componentInstance.save();

    const req = http.expectOne('/api/v1/approval-policy/default');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({
      money_out_default_role: 'owner',
      money_out_owner_threshold: '25000',
      money_out_owner_role: 'owner',
      accounting_role: 'owner',
      money_in_role: 'manager',
      draft_role: 'manager',
      external_send_role: 'admin',
      high_risk_role: 'owner',
    });
    req.flush({ ...policy, policy_source: 'tenant_default', money_out_default_role: 'owner' });

    expect(fixture.componentInstance.saved()).toBeTrue();
  });

  it('keeps manager users read-only', async () => {
    await setup('manager');
    http.expectOne('/api/v1/approval-policy/effective').flush(policy);
    fixture.detectChanges();

    expect(fixture.componentInstance.form.disabled).toBeTrue();
    fixture.componentInstance.save();

    http.expectNone((req) => req.method === 'PUT');
  });
});
