import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ReportsService, statementPeriodRangeError } from './reports.service';

describe('ReportsService statement periods', () => {
  let service: ReportsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ReportsService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    service = TestBed.inject(ReportsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('maps Q2 2026 to the inclusive accounting-period range for every ranged statement', () => {
    service.getIncomeStatement('2026-04', '2026-06').subscribe();
    service.getCashFlow('2026-04', '2026-06').subscribe();
    service.getStatutoryPack('2026-04', '2026-06').subscribe();

    for (const report of ['income-statement', 'cash-flow', 'statutory-pack']) {
      const req = http.expectOne(
        `/api/v1/reports/${report}?period_start=2026-04&period_end=2026-06`,
      );
      expect(req.request.method).toBe('GET');
      req.flush({});
    }
  });

  it('rejects a statement range whose end period is before its start period', () => {
    expect(statementPeriodRangeError('2026-06', '2026-04')).toBe(
      'End period must be the same as or after the start period.',
    );
  });

  it('preserves monthly statement requests when only one period is supplied', () => {
    service.getIncomeStatement('2026-06').subscribe();

    const req = http.expectOne(
      '/api/v1/reports/income-statement?period_start=2026-06&period_end=2026-06',
    );
    expect(req.request.method).toBe('GET');
    req.flush({});
  });

  it('loads the viewer-safe tenant accounting context from its dedicated endpoint', () => {
    let result: { tenant_id: string; base_currency: string } | undefined;

    service.getAccountingContext().subscribe(value => { result = value; });

    const req = http.expectOne('/api/v1/tenants/accounting-context');
    expect(req.request.method).toBe('GET');
    req.flush({ tenant_id: 'tenant-1', base_currency: 'SGD' });
    expect(result).toEqual({ tenant_id: 'tenant-1', base_currency: 'SGD' });
  });
});
