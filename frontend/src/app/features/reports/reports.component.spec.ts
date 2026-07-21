import { ComponentFixture, DeferBlockState, TestBed } from '@angular/core/testing';
import { EMPTY, of } from 'rxjs';

import { ReportsService } from '../../core/services/reports.service';
import { ReportsComponent } from './reports.component';

describe('ReportsComponent statement periods', () => {
  let fixture: ComponentFixture<ReportsComponent>;
  let service: jasmine.SpyObj<ReportsService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<ReportsService>('ReportsService', [
      'getAccountingContext',
      'getArAging',
      'getApAging',
      'getProjectPnl',
      'getUtilization',
      'getWip',
      'getRevenueByEngagement',
      'getBalanceSheet',
      'getRetainedEarningsRollForward',
      'getIncomeStatement',
      'getCashFlow',
      'getStatutoryPack',
      'getTrialBalance',
    ]);
    service.getAccountingContext.and.returnValue(of({
      tenant_id: 'tenant-1',
      base_currency: 'SGD',
    }));
    service.getArAging.and.returnValue(EMPTY);
    service.getApAging.and.returnValue(EMPTY);
    service.getProjectPnl.and.returnValue(EMPTY);
    service.getUtilization.and.returnValue(EMPTY);
    service.getWip.and.returnValue(EMPTY);
    service.getRevenueByEngagement.and.returnValue(EMPTY);
    service.getBalanceSheet.and.returnValue(EMPTY);
    service.getRetainedEarningsRollForward.and.returnValue(EMPTY);
    service.getIncomeStatement.and.returnValue(EMPTY);
    service.getCashFlow.and.returnValue(EMPTY);
    service.getStatutoryPack.and.returnValue(EMPTY);
    service.getTrialBalance.and.returnValue(EMPTY);

    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [{ provide: ReportsService, useValue: service }],
    }).compileComponents();

    fixture = TestBed.createComponent(ReportsComponent);
  });

  it('uses a Q2 range for ranged statements and the quarter end for as-of statements', () => {
    fixture.componentInstance.statementPeriodStart = '2026-04';
    fixture.componentInstance.statementPeriodEnd = '2026-06';

    fixture.componentInstance.loadFinancialStatements();

    expect(service.getIncomeStatement).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getCashFlow).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getStatutoryPack).toHaveBeenCalledOnceWith('2026-04', '2026-06');
    expect(service.getBalanceSheet).toHaveBeenCalledOnceWith('2026-06');
    expect(service.getRetainedEarningsRollForward).toHaveBeenCalledOnceWith('2026-06');
  });

  it('blocks a reversed range before any financial statement request', () => {
    fixture.componentInstance.statementPeriodStart = '2026-06';
    fixture.componentInstance.statementPeriodEnd = '2026-04';

    fixture.componentInstance.loadFinancialStatements();

    expect(fixture.componentInstance.statementPeriodValidationError()).toBe(
      'End period must be the same as or after the start period.',
    );
    expect(service.getIncomeStatement).not.toHaveBeenCalled();
    expect(service.getCashFlow).not.toHaveBeenCalled();
    expect(service.getStatutoryPack).not.toHaveBeenCalled();
    expect(service.getBalanceSheet).not.toHaveBeenCalled();
    expect(service.getRetainedEarningsRollForward).not.toHaveBeenCalled();
  });

  it('loads the tenant accounting context once and exposes its verified base currency', () => {
    fixture.detectChanges();

    expect(service.getAccountingContext).toHaveBeenCalledTimes(1);
    expect(fixture.componentInstance.baseCurrency()).toBe('SGD');
    expect(fixture.componentInstance.reportCurrency()).toBe('SGD');
    expect(fixture.nativeElement.querySelector('[data-testid="reporting-currency"]')?.textContent)
      .toContain('SGD base currency');
  });

  it('preserves an explicit transaction currency and uses tenant base only as fallback', () => {
    fixture.componentInstance.loadAccountingContext();

    expect(fixture.componentInstance.displayCurrency('GBP')).toBe('GBP');
    expect(fixture.componentInstance.displayCurrency(null)).toBe('SGD');
  });

  it('renders AR aging totals in tenant base currency with stable browser-test selectors', async () => {
    service.getArAging.and.returnValue(of({
      '0_30': '27250.00',
      '31_60': '0.00',
      '61_90': '0.00',
      over_90: '0.00',
      unallocated: '0.00',
      total: '27250.00',
    }));
    fixture.detectChanges();

    const [arAgingBlock] = await fixture.getDeferBlocks();
    await arAgingBlock.render(DeferBlockState.Complete);
    fixture.detectChanges();

    const cards = fixture.nativeElement.querySelector('[data-testid="ar-aging-cards"]');
    const total = fixture.nativeElement.querySelector('[data-testid="ar-aging-total"]');
    const unallocated = fixture.nativeElement.querySelector(
      '[data-testid="ar-aging-unallocated"]',
    );
    expect(cards?.textContent).toContain('Total open AR · SGD base currency');
    expect(total?.textContent).toContain('SGD');
    expect(total?.textContent).toContain('27,250.00');
    expect(unallocated?.textContent).toContain('SGD');
  });
});
