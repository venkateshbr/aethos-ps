import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuthService } from '../../core/services/auth.service';
import { FinanceOpsScheduleComponent } from './finance-ops-schedule.component';

const schedule = {
  tenant_id: 'tenant-1',
  is_enabled: true,
  cadence: 'daily',
  run_hour_utc: 7,
  run_weekday_utc: 0,
  timezone: 'UTC',
  period_mode: 'current_month',
  lookback_limit: 10,
  stale_after_hours: 24,
  high_risk_stale_after_hours: 4,
  escalation_enabled: true,
  is_seeded_default: true,
  created_at: null,
  updated_at: null,
} as const;

describe('FinanceOpsScheduleComponent', () => {
  let fixture: ComponentFixture<FinanceOpsScheduleComponent>;
  let http: HttpTestingController;

  async function setup(roleValue: 'admin' | 'manager' = 'admin'): Promise<void> {
    const role = signal<string | null>(roleValue);

    await TestBed.configureTestingModule({
      imports: [FinanceOpsScheduleComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: { role: role.asReadonly() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FinanceOpsScheduleComponent);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => {
    http.verify();
  });

  it('loads and renders the seeded default schedule', async () => {
    await setup('admin');

    const req = http.expectOne('/api/v1/agents/finance-ops/schedule');
    expect(req.request.method).toBe('GET');
    req.flush(schedule);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Default schedule');
    expect(text).toContain('Enabled');
    expect(fixture.componentInstance.form.getRawValue().run_hour_utc).toBe(7);
  });

  it('saves admin schedule edits through the existing API contract', async () => {
    await setup('admin');
    http.expectOne('/api/v1/agents/finance-ops/schedule').flush(schedule);

    fixture.componentInstance.form.patchValue({
      cadence: 'weekly',
      run_hour_utc: 8,
      run_weekday_utc: 2,
      timezone: 'UTC',
      period_mode: 'previous_month',
      lookback_limit: 12,
      stale_after_hours: 48,
      high_risk_stale_after_hours: 6,
      escalation_enabled: true,
    });
    fixture.componentInstance.save();

    const req = http.expectOne('/api/v1/agents/finance-ops/schedule');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({
      is_enabled: true,
      cadence: 'weekly',
      run_hour_utc: 8,
      run_weekday_utc: 2,
      timezone: 'UTC',
      period_mode: 'previous_month',
      lookback_limit: 12,
      stale_after_hours: 48,
      high_risk_stale_after_hours: 6,
      escalation_enabled: true,
    });
    req.flush({ ...schedule, cadence: 'weekly', is_seeded_default: false });

    expect(fixture.componentInstance.saved()).toBeTrue();
  });

  it('keeps manager users read-only', async () => {
    await setup('manager');
    http.expectOne('/api/v1/agents/finance-ops/schedule').flush(schedule);
    fixture.detectChanges();

    expect(fixture.componentInstance.form.disabled).toBeTrue();
    fixture.componentInstance.save();

    http.expectNone((req) => req.method === 'PUT');
  });
});
